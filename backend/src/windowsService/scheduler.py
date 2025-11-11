# windowsService/scheduler.py
import schedule
import time
import threading
import logging
import sys
import os
from datetime import datetime

# Setup logging
log_dir = os.path.join(
    os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
    'WAZAPOS',
    'service'
)
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(log_dir, 'scheduler.log'), mode='a')
    ]
)

logger = logging.getLogger(__name__)

# Log immediately when module is loaded
logger.info("=" * 60)
logger.info("SCHEDULER MODULE LOADED")
logger.info("=" * 60)

def your_task_function():
    """Example task function that gets executed by the scheduler"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"=" * 60)
        logger.info(f"TASK EXECUTED AT: {timestamp}")
        logger.info(f"=" * 60)
        
        # Write to a separate task execution log for easy verification
        task_log = os.path.join(log_dir, 'task_executions.log')
        with open(task_log, 'a') as f:
            f.write(f"{timestamp} - Task executed successfully\n")
        
        # TODO: Add your actual task logic here
        # Since win10toast doesn't work from services, use file-based notification
        # or IPC to communicate with your Electron app
        
        # Example: Write to a file that your Electron app can monitor
        notification_file = os.path.join(log_dir, 'pending_notifications.txt')
        with open(notification_file, 'a') as f:
            f.write(f"{timestamp}|Scheduler Task|Your scheduled task has been executed.\n")
        
        logger.info("Task completed successfully - notification queued")
        
    except Exception as e:
        logger.error(f"Error in task execution: {e}")
        import traceback
        logger.error(traceback.format_exc())

class TaskScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.task_count = 0
        logger.info("TaskScheduler initialized")
        
    def setup_schedules(self):
        """Define your scheduled tasks here"""
        logger.info("Setting up scheduled tasks...")
        
        try:
            # Run every day at 10:30 AM
            schedule.every().day.at("10:30").do(self._wrapped_task, "Daily 10:30")
            logger.info("Scheduled: Daily task at 10:30 AM")
            
            # Run every hour
            schedule.every().hour.do(self._wrapped_task, "Hourly")
            logger.info("Scheduled: Hourly task")
            
            # Run every 5 minutes
            schedule.every(5).minutes.do(self._wrapped_task, "Every 5 minutes")
            logger.info("Scheduled: Task every 5 minutes")
            
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
                
                # Log every 60 iterations (roughly every minute) to show scheduler is alive
                if iteration % 60 == 0:
                    logger.info(f"Scheduler alive - {len(schedule.jobs)} jobs scheduled, {self.task_count} tasks executed so far")
                    logger.info(f"Next run times: {[str(job.next_run) for job in schedule.jobs[:3]]}")
                
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