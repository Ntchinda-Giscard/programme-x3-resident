# windows-service/scheduler.py
import schedule
import time
import threading
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

logger = logging.getLogger(__name__)

# Define your task function directly in this file
def your_task_function():
    """Example task function that gets executed by the scheduler"""
    logger.info("Task executed successfully")
    
    # TODO: Add your actual task logic here
    # For example:
    # - Database cleanup
    # - Send notifications
    # - Process queued jobs
    # - Sync data
    # etc.

class TaskScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        logger.info("TaskScheduler initialized")
        
    def setup_schedules(self):
        """Define your scheduled tasks here"""
        logger.info("Setting up scheduled tasks...")
        
        # Run every day at 10:30 AM
        schedule.every().day.at("10:30").do(your_task_function)
        logger.info("Scheduled: Daily task at 10:30 AM")
        
        # Run every hour
        schedule.every().hour.do(your_task_function)
        logger.info("Scheduled: Hourly task")
        
        # Run every 5 minutes
        schedule.every(5).minutes.do(your_task_function)
        logger.info("Scheduled: Task every 5 minutes")
        
        logger.info("All schedules configured")
        
    def run(self):
        """Run the scheduler loop"""
        logger.info("Scheduler loop starting...")
        self.setup_schedules()
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("Scheduler loop ended")
    
    def start(self):
        """Start the scheduler in a separate thread"""
        logger.info("Starting scheduler thread...")
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        logger.info("Scheduler thread started")
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping scheduler...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")