import subprocess
import os
import logging
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from app.config import settings

logger = logging.getLogger(__name__)

class SSLService:
    def __init__(self):
        self.domain = settings.DOMAIN
        self.email = settings.EMAIL
        self.webroot = settings.WEBROOT_DIR
        self.cert_dir = os.path.join(settings.CERT_DIR, self.domain)
        
        # Ensure webroot exists
        os.makedirs(self.webroot, exist_ok=True)

    def get_certificate_path(self):
        """Returns the path to the fullchain.pem"""
        # Certbot default structure: /etc/letsencrypt/live/domain/fullchain.pem
        return os.path.join(settings.CERT_DIR, self.domain, "fullchain.pem")

    def get_key_path(self):
        return os.path.join(settings.CERT_DIR, self.domain, "privkey.pem")

    def get_cert_expiry(self) -> datetime | None:
        cert_path = self.get_certificate_path()
        if not os.path.exists(cert_path):
            return None
        
        try:
            with open(cert_path, "rb") as f:
                cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                return cert.not_valid_after_utc
        except Exception as e:
            logger.error(f"Error reading certificate: {e}")
            return None

    def days_until_expiry(self) -> int | None:
        expiry = self.get_cert_expiry()
        if expiry is None:
            return None
        
        now = datetime.now(timezone.utc)
        delta = expiry - now
        return delta.days

    def obtain_certificate(self):
        """Runs certbot to obtain a new certificate using webroot plugin"""
        logger.info(f"Obtaining certificate for {self.domain}...")
        cmd = [
            "certbot", "certonly",
            "--webroot",
            "--webroot-path", self.webroot,
            "-d", self.domain,
            "--email", self.email,
            "--agree-tos",
            "--non-interactive",
            "--keep-until-expiring" # Don't renew if not needed by certbot's standards, but we control calls
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Certbot finished successfully.")
            logger.info(result.stdout)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Certbot failed: {e.stderr}")
            return False, e.stderr

    def check_and_renew(self):
        """
        Checks if certificate exists and is valid.
        If not exists or expiring soon (based on config), renews it.
        """
        days_left = self.days_until_expiry()
        
        if days_left is None:
            logger.info("No certificate found. Attempting to obtain one.")
            return self.obtain_certificate()
        
        logger.info(f"Certificate expires in {days_left} days.")
        
        if days_left < settings.RENEWAL_DAYS_BEFORE_EXPIRY:
            logger.info(f"Certificate is expiring soon (< {settings.RENEWAL_DAYS_BEFORE_EXPIRY} days). Renewing...")
            # Force renewal if close to expiry
            # We can use 'certbot renew' or just run obtain_certificate again with --force-renewal if needed
            # actually certbot certonly knows how to renew if lineages exist.
            # But to enforce our specific day count, we might need --force-renewal if certbot thinks it's too early
            # Certbot default is 30 days. If we set RENEWAL_DAYS to 40, we need to force.
            
            cmd = [
                "certbot", "certonly",
                "--webroot",
                "--webroot-path", self.webroot,
                "-d", self.domain,
                "--email", self.email,
                "--agree-tos",
                "--non-interactive",
                "--force-renewal"
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                logger.info("Certbot renewal finished successfully.")
                return True, result.stdout
            except subprocess.CalledProcessError as e:
                logger.error(f"Certbot renewal failed: {e.stderr}")
                return False, e.stderr
        else:
            return True, "Certificate is valid and not due for renewal."

