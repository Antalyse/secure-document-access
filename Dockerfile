# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed (e.g. for sqlite3 headers, though often included)
# RUN apt-get update && apt-get install -y sqlite3

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create a volume mount point for persistent data (counter and db)
VOLUME /app/data

# Expose the port the app runs on
EXPOSE 5000

# Run the application using Gunicorn for production readiness
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
