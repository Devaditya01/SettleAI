FROM python:3.11-slim

WORKDIR /app

# Install system build tools needed for some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy app source
COPY . .

# Render injects $PORT at runtime
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
