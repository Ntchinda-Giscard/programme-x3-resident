# import sys
# import os

# # CRITICAL: Set unbuffered output immediately
# sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
# sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# # Emergency logging with explicit flushing
# def emergency_write(msg):
#     """Write to file immediately with forced flush"""
#     try:
#         log_dir = os.path.join(
#             os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
#             'WAZAPOS',
#             'service'
#         )
#         os.makedirs(log_dir, exist_ok=True)
        
#         emergency_log = os.path.join(log_dir, 'EMERGENCY.log')
        
#         with open(emergency_log, 'a') as f:
#             from datetime import datetime
#             f.write(f"{datetime.now()} - {msg}\n")
#             f.flush()
#             os.fsync(f.fileno())  # Force OS to write to disk
#     except Exception as e:
#         # Last resort - write to temp
#         try:
#             import tempfile
#             with open(os.path.join(tempfile.gettempdir(), 'wazapos_emergency.log'), 'a') as f:
#                 f.write(f"{msg}\n")
#                 f.flush()
#         except:
#             pass

# emergency_write("=" * 80)
# emergency_write(f"SERVICE PROCESS STARTED")
# emergency_write(f"Python executable: {sys.executable}")
# emergency_write(f"Python version: {sys.version}")
# emergency_write(f"Working directory: {os.getcwd()}")
# emergency_write(f"Script: {__file__}")
# emergency_write(f"sys.path: {sys.path[:3]}")
# emergency_write("=" * 80)

# import win32serviceutil
# import win32service
# import win32event
# import servicemanager
# import socket
# import time
# import traceback
# import threading
# import logging

# emergency_write("Imports successful")

# def setup_logging():
#     """Setup logging with forced flushing"""
#     log_dir = os.path.join(
#         os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
#         'WAZAPOS',
#         'service'
#     )
#     os.makedirs(log_dir, exist_ok=True)
    
#     class FlushingFileHandler(logging.FileHandler):
#         def emit(self, record):
#             super().emit(record)
#             self.flush()  # Force flush after every log
    
#     # Setup SERVICE logger
#     service_logger = logging.getLogger('service')
#     service_logger.setLevel(logging.DEBUG)
#     service_logger.propagate = False  # Don't propagate to root logger
    
#     service_logger.handlers.clear()
    
#     service_log_file = os.path.join(log_dir, 'service_debug.log')
#     service_handler = FlushingFileHandler(service_log_file, mode='a')
#     service_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - %(funcName)s - %(lineno)d'))
#     service_logger.addHandler(service_handler)
#     service_logger.addHandler(logging.StreamHandler(sys.stdout))
    
#     # Setup SCHEDULER logger with its own file
#     scheduler_logger = logging.getLogger('scheduler')
#     scheduler_logger.setLevel(logging.DEBUG)
#     scheduler_logger.propagate = False  # Don't propagate to root logger
    
#     scheduler_logger.handlers.clear()
    
#     scheduler_log_file = os.path.join(log_dir, 'scheduler.log')
#     scheduler_handler = FlushingFileHandler(scheduler_log_file, mode='a')
#     scheduler_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s'))
#     scheduler_logger.addHandler(scheduler_handler)
#     scheduler_logger.addHandler(logging.StreamHandler(sys.stdout))
    
#     service_logger.info("=" * 80)
#     service_logger.info("LOGGING INITIALIZED")
#     service_logger.info(f"Service log file: {service_log_file}")
#     service_logger.info(f"Service logger handlers: {len(service_logger.handlers)}")
#     service_logger.info(f"Scheduler log file: {scheduler_log_file}")
#     service_logger.info(f"Scheduler logger handlers: {len(scheduler_logger.handlers)}")
#     service_logger.info("=" * 80)
    
#     for handler in service_logger.handlers:
#         handler.flush()
#     for handler in scheduler_logger.handlers:
#         handler.flush()
    
#     return service_logger, scheduler_logger

# emergency_write("Setting up logging...")
# logger, scheduler_logger = setup_logging()
# emergency_write("Logging setup complete")

# # windowsService/scheduler.py
# import schedule
# from datetime import datetime

# log_dir = os.path.join(
#     os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
#     'WAZAPOS',
#     'service'
# )
# os.makedirs(log_dir, exist_ok=True)

# # Log immediately when module is loaded
# scheduler_logger.info("=" * 60)
# scheduler_logger.info("SCHEDULER MODULE LOADED")
# scheduler_logger.info("=" * 60)

# def your_task_function():
#     """Example task function that gets executed by the scheduler"""
#     try:
#         timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         scheduler_logger.info(f"=" * 60)
#         scheduler_logger.info(f"TASK EXECUTED AT: {timestamp}")
#         scheduler_logger.info(f"=" * 60)
        
#         # Write to a separate task execution log for easy verification
#         task_log = os.path.join(log_dir, 'task_executions.log')
#         with open(task_log, 'a') as f:
#             f.write(f"{timestamp} - Task executed successfully\n")
#             f.flush()
        
#         # Example: Write to a file that your Electron app can monitor
#         notification_file = os.path.join(log_dir, 'pending_notifications.txt')
#         with open(notification_file, 'a') as f:
#             f.write(f"{timestamp}|Scheduler Task|Your scheduled task has been executed.\n")
#             f.flush()
        
#         scheduler_logger.info("Task completed successfully - notification queued")
        
#     except Exception as e:
#         scheduler_logger.error(f"Error in task execution: {e}")
#         import traceback
#         scheduler_logger.error(traceback.format_exc())

# class TaskScheduler:
#     def __init__(self):
#         self.running = False
#         self.thread = None
#         self.task_count = 0
#         scheduler_logger.info("TaskScheduler initialized")
        
#     def setup_schedules(self):
#         scheduler_logger.info("Setting up scheduled tasks...")

#         try:
#             # Run every 5 minutes only
#             schedule.every(5).minutes.do(self._wrapped_task, "Every 5 minutes")
#             scheduler_logger.info("Scheduled: Task every 5 minutes")

#             scheduler_logger.info("All schedules configured successfully")
#             scheduler_logger.info(f"Total scheduled jobs: {len(schedule.jobs)}")

#         except Exception as e:
#             scheduler_logger.error(f"Error setting up schedules: {e}")
#             raise

    
#     def _wrapped_task(self, task_name):
#         """Wrapper that adds tracking to task execution"""
#         self.task_count += 1
#         scheduler_logger.info(f"Executing task '{task_name}' (execution #{self.task_count})")
#         your_task_function()
#         scheduler_logger.info(f"Completed task '{task_name}'")
        
#     def run(self):
#         """Run the scheduler loop"""
#         try:
#             scheduler_logger.info("Scheduler loop starting...")
#             self.setup_schedules()
            
#             scheduler_logger.info("Entering scheduler loop - waiting for tasks...")
#             iteration = 0
#             while self.running:
#                 iteration += 1
                
#                 # Log every 60 iterations (roughly every minute) to show scheduler is alive
#                 if iteration % 60 == 0:
#                     scheduler_logger.info(f"Scheduler alive - {len(schedule.jobs)} jobs scheduled, {self.task_count} tasks executed so far")
#                     scheduler_logger.info(f"Next run times: {[str(job.next_run) for job in schedule.jobs[:3]]}")
                
#                 schedule.run_pending()
#                 time.sleep(1)
            
#             scheduler_logger.info("Scheduler loop ended")
#         except Exception as e:
#             scheduler_logger.error(f"Error in scheduler loop: {e}")
#             import traceback
#             scheduler_logger.error(traceback.format_exc())
#             raise
    
#     def start(self):
#         """Start the scheduler in a separate thread"""
#         scheduler_logger.info("Starting scheduler thread...")
#         self.running = True
#         self.thread = threading.Thread(target=self.run, daemon=True)
#         self.thread.start()
#         scheduler_logger.info("Scheduler thread started")
    
#     def stop(self):
#         """Stop the scheduler"""
#         scheduler_logger.info("Stopping scheduler...")
#         self.running = False
#         if self.thread:
#             self.thread.join(timeout=5)
#         scheduler_logger.info(f"Scheduler stopped - Total tasks executed: {self.task_count}")


# class YourAppService(win32serviceutil.ServiceFramework):
#     _svc_name_ = "WAZAPOS"
#     _svc_display_name_ = "WAZAPOS App Background Service"
#     _svc_description_ = "Runs scheduled tasks for WAZAPOS App"

#     def __init__(self, args):
#         emergency_write("__init__ called")
#         logger.info("Initializing YourAppService")
        
#         try:
#             win32serviceutil.ServiceFramework.__init__(self, args)
#             self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
#             socket.setdefaulttimeout(60)
#             self.is_alive = True
#             self.scheduler = None
#             self.scheduler_thread = None
            
#             logger.info("Service initialized successfully")
#             emergency_write("Service initialized")
            
#         except Exception as e:
#             error_msg = f"Error in __init__: {e}\n{traceback.format_exc()}"
#             logger.error(error_msg)
#             emergency_write(f"ERROR: {error_msg}")
#             raise

#     def SvcStop(self):
#         emergency_write("SvcStop called")
#         logger.info("Stop signal received")
        
#         try:
#             self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
#             win32event.SetEvent(self.hWaitStop)
#             self.is_alive = False
            
#             if self.scheduler:
#                 logger.info("Stopping scheduler...")
#                 self.scheduler.stop()
#                 logger.info("Scheduler stopped")
            
#             if self.scheduler_thread and self.scheduler_thread.is_alive():
#                 logger.info("Waiting for scheduler thread...")
#                 self.scheduler_thread.join(timeout=5)
#                 logger.info("Scheduler thread finished")
            
#             logger.info("Service stop completed")
#             emergency_write("Service stopped successfully")
            
#         except Exception as e:
#             error_msg = f"Error in SvcStop: {e}\n{traceback.format_exc()}"
#             logger.error(error_msg)
#             emergency_write(f"ERROR: {error_msg}")

#     def SvcDoRun(self):
#         emergency_write("SvcDoRun called")
#         logger.info("SvcDoRun - service starting")
        
#         try:
#             self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
#             emergency_write("Reported START_PENDING")
            
#             servicemanager.LogMsg(
#                 servicemanager.EVENTLOG_INFORMATION_TYPE,
#                 servicemanager.PYS_SERVICE_STARTED,
#                 (self._svc_name_, '')
#             )
            
#             self.ReportServiceStatus(win32service.SERVICE_RUNNING)
#             logger.info("Service reported as RUNNING")
#             emergency_write("Service RUNNING")
            
#             # Start scheduler
#             self._start_scheduler_background()
            
#             # Main loop
#             self._main_loop()
            
#             logger.info("Service ending normally")
#             emergency_write("Service ending")
            
#         except Exception as e:
#             error_msg = f"FATAL ERROR in SvcDoRun: {e}\n{traceback.format_exc()}"
#             logger.error(error_msg)
#             emergency_write(f"FATAL: {error_msg}")
            
#             try:
#                 servicemanager.LogErrorMsg(f"Service failed: {e}")
#             except:
#                 pass
            
#             self.ReportServiceStatus(win32service.SERVICE_STOPPED)

#     def _start_scheduler_background(self):
#         """Start scheduler in background thread"""
#         try:
#             logger.info("Starting scheduler thread...")
#             emergency_write("Starting scheduler thread")
            
#             self.scheduler_thread = threading.Thread(
#                 target=self._initialize_scheduler_thread,
#                 daemon=False,
#                 name="SchedulerThread"
#             )
#             self.scheduler_thread.start()
            
#             logger.info("Scheduler thread spawned")
#             emergency_write("Scheduler thread spawned")
            
#         except Exception as e:
#             error_msg = f"Failed to spawn scheduler: {e}\n{traceback.format_exc()}"
#             logger.error(error_msg)
#             emergency_write(f"ERROR: {error_msg}")

#     def _initialize_scheduler_thread(self):
#         """Initialize scheduler on separate thread"""
#         emergency_write("Scheduler thread started")
#         logger.info("Scheduler thread: initializing...")
        
#         try:
#             logger.info("Creating TaskScheduler instance...")
#             self.scheduler = TaskScheduler()
#             logger.info("TaskScheduler created")
#             emergency_write("TaskScheduler created")
            
#             logger.info("Starting TaskScheduler...")
#             self.scheduler.start()
#             logger.info("TaskScheduler started successfully")
#             emergency_write("TaskScheduler started successfully")
            
#             servicemanager.LogInfoMsg("TaskScheduler is running")
            
#             logger.info("Scheduler initialization thread now keeping scheduler alive...")
#             while self.is_alive:
#                 time.sleep(1)
            
#             logger.info("Scheduler initialization thread ending")
            
#         except Exception as e:
#             error_msg = f"FATAL in scheduler thread: {e}\n{traceback.format_exc()}"
#             logger.error(error_msg)
#             emergency_write(f"FATAL: {error_msg}")

#     def _main_loop(self):
#         """Main service loop"""
#         emergency_write("Entering main loop")
#         logger.info("Entering main service loop")
        
#         try:
#             iteration = 0
#             while self.is_alive:
#                 iteration += 1
                
#                 # Log heartbeat every 60 iterations (~5 minutes)
#                 if iteration % 60 == 0:
#                     logger.info(f"Service heartbeat - iteration {iteration}")
#                     emergency_write(f"Heartbeat {iteration}")
                
#                 rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
#                 if rc == win32event.WAIT_OBJECT_0:
#                     logger.info("Stop event received")
#                     emergency_write("Stop event received")
#                     break
            
#             logger.info("Exiting main loop")
#             emergency_write("Main loop exited")
            
#         except Exception as e:
#             error_msg = f"ERROR in main loop: {e}\n{traceback.format_exc()}"
#             logger.error(error_msg)
#             emergency_write(f"LOOP ERROR: {error_msg}")
#             raise


# if __name__ == '__main__':
#     emergency_write("__main__ executing")
#     logger.info(f"Script started with args: {sys.argv}")
    
#     try:
#         if len(sys.argv) == 1:
#             emergency_write("Running as service")
#             logger.info("Running as Windows service")
#             servicemanager.Initialize()
#             servicemanager.PrepareToHostSingle(YourAppService)
#             servicemanager.StartServiceCtrlDispatcher()
#         else:
#             emergency_write(f"Command line: {sys.argv}")
#             logger.info("Running command line handler")
#             win32serviceutil.HandleCommandLine(YourAppService)
            
#     except Exception as e:
#         error_msg = f"FATAL in __main__: {e}\n{traceback.format_exc()}"
#         logger.error(error_msg)
#         emergency_write(f"FATAL MAIN: {error_msg}")
#         raise


import win32serviceutil
import win32service
import win32event
import servicemanager
import time
from datetime import datetime
import pyodbc
import sqlite3
from decimal import Decimal
import logging
import os


# LOG_FILE = "C:\\WAZAPOS_service_log.log"

# def log_message(message):
#     """Helper: log message with timestamp to file and Event Viewer"""
#     timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
#     line = f"{timestamp} {message}\n"

#     # Append to file
#     with open(LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(line)

#     # Send to Event Viewer
#     servicemanager.LogInfoMsg(line)


class PythonService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WAZAPOS_TEST"              # Service name (unique)
    _svc_display_name_ = "WAZAPOS_TEST"    # Display name in Windows Services
    _svc_description_ = "Runs a Python script in the background as a Windows service"

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        """Called when the service is stopped."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        """Main service loop."""
        servicemanager.LogInfoMsg("MyPythonService - Starting service...")
        sqlserver_conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=192.168.2.41,1433;"
            "DATABASE=x3waza;"
            "UID=superadmin;"
            "PWD=MotDePasseFort123!;"
        )
        sqlserver_cursor = sqlserver_conn.cursor()

        db_folder = r"C:\my-folder-i-created\sagex3-db"
        db_path = os.path.join(db_folder, "sagex3_seed.db")

        # Create the folder if it doesn't exist
        os.makedirs(db_folder, exist_ok=True)

        while self.running:
            # 👉 Put your custom Python code here
            with open("C:\\service_log.txt", "a") as f:
                f.write("Service running new...\n")

            time.sleep(10)  # Wait 10 seconds before next loop

        servicemanager.LogInfoMsg("MyPythonService - Service stopped.")

    # def SvcDoRun(self):
    #     """Main entry point for service logic"""
    #     log_message("Service started successfully.")
    #     self.main_loop()
    
    # def main_loop(self):
    #     """Main loop that runs periodically"""
    #     while self.running:
    #         log_message("Heartbeat: Service is running.")
    #         time.sleep(300)  # Log every 5 minutes

        # log_message("Service stopped.")


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)
