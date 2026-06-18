# Use official light-weight Python base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (libgomp1 is required by FAISS because it leverages OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code files
COPY . .

# Expose FastAPI server port
EXPOSE 8000

# Start server listening on all interfaces inside container
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
