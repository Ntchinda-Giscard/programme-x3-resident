# windows-service/scheduler.py
import schedule
import time
import threading
from tasks import your_task_function

class TaskScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        
    def setup_schedules(self):
        """Define your scheduled tasks here"""
        # Run every day at 10:30 AM
        schedule.every().day.at("10:30").do(your_task_function)
        
        # Run every hour
        schedule.every().hour.do(your_task_function)
        
        # Run every 5 minutes
        schedule.every(5).minutes.do(your_task_function)
        
        # Custom schedules as needed
        
    def run(self):
        """Run the scheduler loop"""
        self.setup_schedules()
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def start(self):
        """Start the scheduler in a separate thread"""
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)