# windows-service/scheduler.py
import schedule
import time
import threading
import logging
import sys
import os
from datetime import datetime

# Setup logging with forced flushing
log_dir = os.path.join(
    os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
    'WAZAPOS',
    'service'
)
os.makedirs(log_dir, exist_ok=True)

# Custom handler that forces flushing
class FlushingFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        FlushingFileHandler(os.path.join(log_dir, 'scheduler.log'), mode='a')
    ],
    force=True
)

logger = logging.getLogger(__name__)
logger.info("="*60)
logger.info("SCHEDULER MODULE LOADED")
logger.info("="*60)

def your_task_function():
    """Example task function that gets executed by the scheduler"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info("=" * 60)
        logger.info(f"TASK EXECUTED AT: {timestamp}")
        logger.info("=" * 60)
        
        # Write to task executions log
        task_log = os.path.join(log_dir, 'task_executions.log')
        with open(task_log, 'a') as f:
            f.write(f"{timestamp} - Task executed successfully\n")
            f.flush()
            os.fsync(f.fileno())  # Force OS write
        
        # Write notification file for Electron app
        notification_file = os.path.join(log_dir, 'pending_notifications.txt')
        with open(notification_file, 'a') as f:
            f.write(f"{timestamp}|Scheduler Task|Your scheduled task has been executed.\n")
            f.flush()
            os.fsync(f.fileno())
        
        logger.info("Task completed - notification queued")
        
    except Exception as e:
        logger.error(f"Error in task execution: {e}")
        import traceback
        logger.error(traceback.format_exc())

class TaskScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.task_count = 0  # Add this line - it was missing!
        logger.info("TaskScheduler initialized")
        
    def setup_schedules(self):
        """Define your scheduled tasks here"""
        logger.info("Setting up scheduled tasks...")
        
        try:
            # For testing, run every 2 minutes instead of longer intervals
            schedule.every(2).minutes.do(self._wrapped_task, "Every 2 minutes")
            logger.info("Scheduled: Task every 2 minutes")
            
            # Uncomment these once testing is complete:
            # schedule.every().day.at("10:30").do(self._wrapped_task, "Daily 10:30")
            # schedule.every().hour.do(self._wrapped_task, "Hourly")
            
            logger.info("All schedules configured successfully")
            logger.info(f"Total scheduled jobs: {len(schedule.jobs)}")
            
        except Exception as e:
            logger.error(f"Error setting up schedules: {e}")
            raise
    
    def _wrapped_task(self, task_name):
        """Wrapper that adds tracking to task execution"""
        self.task_count += 1
        logger.info(f"Executing task '{task_name}' (execution #{self.task_count})")
        your_task_function()
        logger.info(f"Completed task '{task_name}'")
        
    def run(self):
        """Run the scheduler loop"""
        try:
            logger.info("Scheduler loop starting...")
            self.setup_schedules()
            
            logger.info("Entering scheduler loop - waiting for tasks...")
            iteration = 0
            
            while self.running:
                iteration += 1
                
                # Log every 30 iterations (roughly every 30 seconds) to show it's alive
                if iteration % 30 == 0:
                    logger.info(f"Scheduler alive - {len(schedule.jobs)} jobs, {self.task_count} tasks executed")
                    if schedule.jobs:
                        next_run = min(job.next_run for job in schedule.jobs)
                        logger.info(f"Next run at: {next_run}")
                
                schedule.run_pending()
                time.sleep(1)
            
            logger.info("Scheduler loop ended")
            
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
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
        logger.info(f"Scheduler stopped - Total tasks executed: {self.task_count}")