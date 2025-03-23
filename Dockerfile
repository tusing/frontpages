FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py config.yaml frontpages.py ./

# Expose the port the app runs on
EXPOSE 5001

# Run the application
CMD ["python", "frontpages.py"] 