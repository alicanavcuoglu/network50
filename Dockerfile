FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for SQLite database
RUN mkdir -p instance && chown -R www-data:www-data instance

# Run as non-root user
USER www-data

# Expose port
EXPOSE 5000

# Modified command to use Flask-SocketIO's worker
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]