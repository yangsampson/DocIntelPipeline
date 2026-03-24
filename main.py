import os
import shutil
import tempfile
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

# 1. Setup Absolute Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

UPLOAD_DIR = os.path.join(BASE_DIR, os.getenv("UPLOAD_DIR", "storage/uploads"))
OUTPUT_DIR = os.path.join(BASE_DIR, os.getenv("OUTPUT_DIR", "storage/output"))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Logic imports
from services.converter import convert_to_png
from services.processor import extract_elements

app = FastAPI()

class DeleteRequest(BaseModel):
    folders: List[str]

# --- PAGE ROUTES ---

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))

@app.get("/record")
async def serve_record():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "record.html"))

# --- UPLOAD ---

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    safe_filename = file.filename.replace(" ", "_")
    # Strip extension for the ID (e.g., 'test.pdf' -> 'test')
    clean_id = os.path.splitext(safe_filename)[0]
    input_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        png_path = convert_to_png(input_path, safe_filename)
        if not png_path or not os.path.exists(png_path):
            raise HTTPException(status_code=500, detail="Conversion failed.")
            
        result_data = extract_elements(png_path)
        # Return the clean ID to be saved in LocalStorage
        result_data["folder_id"] = clean_id
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- DOWNLOADS ---

@app.get("/download/{filename}")
async def download_output_folder(filename: str, background_tasks: BackgroundTasks):
    folder_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found.")
    
    zip_base_path = os.path.join(OUTPUT_DIR, f"{filename}_temp")
    shutil.make_archive(zip_base_path, 'zip', folder_path)
    final_zip_path = f"{zip_base_path}.zip"
    
    background_tasks.add_task(os.remove, final_zip_path)
    return FileResponse(path=final_zip_path, filename=f"{filename}.zip", media_type="application/zip")

@app.get("/download/header/{base_name}")
async def download_header(base_name: str):
    # Ensure we use base_name to find the file
    clean_id = os.path.splitext(base_name)[0]
    file_path = os.path.join(OUTPUT_DIR, clean_id, f"{clean_id}_header.png")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
    
    # application/octet-stream forces a download instead of a preview
    return FileResponse(path=file_path, filename=f"{clean_id}_header.png", media_type="application/octet-stream")

@app.get("/download/signature/{base_name}")
async def download_signature(base_name: str):
    clean_id = os.path.splitext(base_name)[0]
    file_path = os.path.join(OUTPUT_DIR, clean_id, f"{clean_id}_signature.png")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
        
    return FileResponse(path=file_path, filename=f"{clean_id}_signature.png", media_type="application/octet-stream")

# --- BULK RECORD MANAGEMENT ---

@app.post("/api/download-selected")
async def download_selected(data: DeleteRequest, background_tasks: BackgroundTasks):
    if not data.folders:
        raise HTTPException(status_code=400, detail="No folders selected")

    # Create a temp workspace
    tmp_parent = tempfile.mkdtemp()
    internal_folder_name = "Processed Records"
    export_path = os.path.join(tmp_parent, internal_folder_name)
    os.makedirs(export_path)

    try:
        for folder_name in data.folders:
            # Prevent directory traversal
            safe_name = os.path.basename(folder_name)
            src = os.path.join(OUTPUT_DIR, safe_name)
            if os.path.exists(src):
                # Copy selected folders into the "Processed Records" directory
                shutil.copytree(src, os.path.join(export_path, safe_name))

        # Zip it up: Archive everything in tmp_parent/Processed Records
        zip_base = os.path.join(tmp_parent, "ProcessedRecords")
        shutil.make_archive(zip_base, 'zip', tmp_parent, internal_folder_name)
        final_zip = f"{zip_base}.zip"

        background_tasks.add_task(shutil.rmtree, tmp_parent)
        return FileResponse(path=final_zip, filename="ProcessedRecords.zip", media_type="application/zip")
    except Exception as e:
        if os.path.exists(tmp_parent):
            shutil.rmtree(tmp_parent)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/records")
async def get_records_data():
    if not os.path.exists(OUTPUT_DIR): return {"records": []}
    # Return all folder names so frontend can filter
    all_folders = [f for f in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, f))]
    all_folders.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    return {"records": all_folders}

@app.post("/api/delete")
async def delete_records(data: DeleteRequest):
    deleted = []
    for folder_name in data.folders:
        safe_name = os.path.basename(folder_name)
        target = os.path.join(OUTPUT_DIR, safe_name)
        if os.path.exists(target):
            shutil.rmtree(target)
            deleted.append(safe_name)
    return {"status": "success", "deleted": deleted}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
