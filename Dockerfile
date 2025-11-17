FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data config output logs

# Expose Streamlit port
EXPOSE 8501

# Default command (runs dashboard)
CMD ["streamlit", "run", "dashboard.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
