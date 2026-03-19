FROM python:3.10-slim

# 1. Install LibreOffice, Fonts, and JRE
# We combine these to keep the image layers clean
RUN apt-get update && apt-get install -y \
    libreoffice-writer \
    fonts-liberation \
    default-jre-headless \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 2. Set the working directory
WORKDIR /app

# 3. Copy only requirements first (Optimization Trick)
# This allows Docker to cache your dependencies separately from your code
COPY requirements.txt .

# 4. Install python dependencies
# --no-cache-dir keeps the image size small
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code
COPY . .

# 6. Start the app
CMD ["python", "main.py"]
