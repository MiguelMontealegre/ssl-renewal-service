# SSL Renewal Service

This project provides an automated SSL certificate validation and renewal service using Certbot (HTTP-01 challenge). It exposes an API to trigger validation and retrieve certificates.

## Structure

- `app/`: Main application code (FastAPI).
- `app/ssl_service.py`: Handles Certbot interactions.
- `app/scheduler.py`: Background task scheduler.
- `client_lib/`: A Python client library to consume this service.

## Deployment

The service is containerized using Docker.

### Prerequisites

- SSH access to the target server.
- Python 3 installed locally (for the deployment script).

### Deploying

Run the `deploy.py` script to deploy to the server:

```bash
python3 deploy.py
```

Ensure you have the correct credentials in `deploy.py`.

## Configuration

Environment variables can be set in `.env` (or passed to Docker):

- `DOMAIN`: Domain to validate (default: test_domain.robin-ai.xyz)
- `EMAIL`: Email for Let's Encrypt registration.
- `VALIDATION_INTERVAL_DAYS`: Frequency of checks (default: 1).
- `RENEWAL_DAYS_BEFORE_EXPIRY`: Days before expiry to trigger renewal (default: 30).

## API Endpoints

- `GET /`: Health check.
- `POST /validate`: Trigger validation/renewal manually.
- `GET /certificates`: Download the current certificate and private key (JSON).
- `GET /status`: Check certificate status and days until expiry.

---

# SSL Client Library

A Python library to consume the SSL Service.

## Installation

```bash
cd client_lib
pip install .
```

## Usage

```python
from ssl_client import SSLClient
import time

# Initialize client
client = SSLClient(
    service_url="http://34.73.29.221", 
    save_path="/path/to/save/certs"
)

# Trigger immediate validation and fetch
client.validate_and_fetch()

# Start automatic periodic checks (background thread)
client.start_auto_renew(interval_seconds=86400) # Daily

# Keep main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    client.stop_auto_renew()
```

