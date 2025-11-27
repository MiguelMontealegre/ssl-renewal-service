import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from app.config import settings
from app.ssl_service import SSLService
from app.scheduler import start_scheduler
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

ssl_service = SSLService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    # Trigger an initial check on startup (optional but good for immediate validation)
    logger.info("Running initial SSL check...")
    # Run in background or await? Since it might take time (certbot), maybe background.
    # For now, let's just let the scheduler run, or do a quick check. 
    # If we block here, deployment might time out if certbot hangs.
    # We'll skip blocking check. The scheduler runs based on interval, but doesn't fire immediately unless we tell it to.
    # We can manually trigger the job or just let the API be the trigger.
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)

# Mount the webroot directory for ACME challenges
# URL path: /.well-known/acme-challenge/
# Local path: settings.WEBROOT_DIR/.well-known/acme-challenge/ 
# Wait, certbot --webroot -w /app/static puts files in /app/static/.well-known/acme-challenge
# So we need to serve /app/static/.well-known/acme-challenge at /.well-known/acme-challenge
# Or just mount /app/static at /? No.
# We want /.well-known/acme-challenge/TOKEN -> /app/static/.well-known/acme-challenge/TOKEN

# Ensure the directory structure exists for mounting
challenge_dir = os.path.join(settings.WEBROOT_DIR, ".well-known", "acme-challenge")
os.makedirs(challenge_dir, exist_ok=True)

app.mount("/.well-known/acme-challenge", StaticFiles(directory=challenge_dir), name="acme-challenge")

@app.get("/")
def read_root():
    return {"message": "SSL Validation Service is running"}

@app.post("/validate")
def trigger_validation():
    """
    Manually triggers the validation and renewal process.
    """
    success, message = ssl_service.check_and_renew()
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=500, detail=f"Validation/Renewal failed: {message}")

@app.get("/certificates")
def get_certificates():
    """
    Returns the certificate content.
    Useful for the client library to 'pull' the certificates.
    """
    cert_path = ssl_service.get_certificate_path()
    key_path = ssl_service.get_key_path()
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        raise HTTPException(status_code=404, detail="Certificates not found")
    
    try:
        with open(cert_path, "r") as f:
            fullchain = f.read()
        with open(key_path, "r") as f:
            privkey = f.read()
            
        return {
            "domain": settings.DOMAIN,
            "fullchain": fullchain,
            "privkey": privkey
        }
    except Exception as e:
        logger.error(f"Error reading certs: {e}")
        raise HTTPException(status_code=500, detail="Error reading certificates")

@app.get("/status")
def get_status():
    days = ssl_service.days_until_expiry()
    return {
        "domain": settings.DOMAIN,
        "days_until_expiry": days,
        "valid": days is not None and days > 0
    }

