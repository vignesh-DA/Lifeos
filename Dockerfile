# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential for compiling C-extensions if any)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model during build so it doesn't download at runtime
RUN python -m spacy download en_core_web_sm

# Copy entire application code
COPY . .

# Expose port (Cloud Run relies on PORT environment variable, usually 8080)
ENV PORT=8080
EXPOSE 8080

# Change working directory to backend where main.py is located
WORKDIR /app/backend

# Command to run FastAPI server
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
