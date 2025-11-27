import os
import requests
import threading
import time
import logging

logger = logging.getLogger(__name__)

class SSLClient:
    def __init__(self, service_url: str, save_path: str):
        """
        :param service_url: The base URL of the SSL Service (e.g., http://34.73.29.221)
        :param save_path: Local directory to save certificates.
        """
        self.service_url = service_url.rstrip("/")
        self.save_path = save_path
        self.running = False
        self.thread = None
        
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def validate_and_fetch(self):
        """
        Triggers validation on the server and fetches certificates if valid.
        """
        try:
            # 1. Trigger validation
            logger.info("Triggering validation on remote service...")
            resp = requests.post(f"{self.service_url}/validate")
            resp.raise_for_status()
            
            # 2. Fetch certificates
            logger.info("Fetching certificates...")
            resp = requests.get(f"{self.service_url}/certificates")
            resp.raise_for_status()
            
            data = resp.json()
            fullchain = data.get("fullchain")
            privkey = data.get("privkey")
            
            if fullchain and privkey:
                self._save_certs(fullchain, privkey)
                logger.info("Certificates saved successfully.")
            else:
                logger.error("Invalid certificate data received.")
                
        except Exception as e:
            logger.error(f"Error in validate_and_fetch: {e}")

    def _save_certs(self, fullchain, privkey):
        fullchain_path = os.path.join(self.save_path, "fullchain.pem")
        privkey_path = os.path.join(self.save_path, "privkey.pem")
        
        with open(fullchain_path, "w") as f:
            f.write(fullchain)
            
        with open(privkey_path, "w") as f:
            f.write(privkey)

    def start_auto_renew(self, interval_seconds=86400):
        """
        Starts a background thread to run validate_and_fetch periodically.
        """
        if self.running:
            logger.warning("Auto renew already running.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop, args=(interval_seconds,), daemon=True)
        self.thread.start()
        logger.info("Auto renew started.")

    def stop_auto_renew(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _loop(self, interval):
        while self.running:
            self.validate_and_fetch()
            # Sleep in chunks to allow faster stopping
            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)

