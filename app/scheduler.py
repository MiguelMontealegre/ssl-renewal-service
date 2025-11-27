from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.ssl_service import SSLService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
ssl_service = SSLService()

def start_scheduler():
    # Schedule the job
    # Run once on startup? We can do that manually or let the scheduler handle it.
    # For 'every X days', we use interval.
    
    trigger = IntervalTrigger(days=settings.VALIDATION_INTERVAL_DAYS)
    
    scheduler.add_job(
        func=ssl_service.check_and_renew,
        trigger=trigger,
        id="ssl_validation_job",
        name="Check and Renew SSL Certificate",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Validation interval: {settings.VALIDATION_INTERVAL_DAYS} days.")

