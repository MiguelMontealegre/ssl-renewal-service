import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DOMAIN: str = "testdomain.robin-ai.xyz"
    EMAIL: str = "admin@robin-ai.xyz"  # Default, should be overridden
    VALIDATION_INTERVAL_DAYS: int = 1
    RENEWAL_DAYS_BEFORE_EXPIRY: int = 95
    CERT_DIR: str = "/etc/letsencrypt/live" # Default certbot path, might need to be adjustable for non-root
    WEBROOT_DIR: str = "/app/static" # Where challenge files will be stored
    
    class Config:
        env_file = ".env"

settings = Settings()
