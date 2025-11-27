FROM python:3.11-slim

# Install system dependencies (if any needed for cryptography/certbot)
# certbot might need some system deps if we install via pip?
# Usually safe with modern wheels.
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    musl-dev \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for certs and static files
RUN mkdir -p /app/static/.well-known/acme-challenge
RUN mkdir -p /etc/letsencrypt

# Expose port 80
EXPOSE 80

# Command to run the application
# We use port 80 because HTTP-01 challenge comes to port 80.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]

