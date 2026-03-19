FROM python:3.10-slim

# Install LibreOffice AND OpenCV system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    fonts-liberation \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure folder structure is ready
RUN mkdir -p storage/uploads storage/output

EXPOSE 8000
CMD ["python", "main.py"]
