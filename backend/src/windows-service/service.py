# backend/src/windows-service/service.py
import sys
import os

# CRITICAL: Set unbuffered output immediately
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Emergency logging with explicit flushing
def emergency_write(msg):
    """Write to file immediately with forced flush"""
    try:
        log_dir = os.path.join(
            os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
            'WAZAPOS',
            'service'
        )
        os.makedirs(log_dir, exist_ok=True)
        
        emergency_log = os.path.join(log_dir, 'EMERGENCY.log')
        
        with open(emergency_log, 'a') as f:
            from datetime import datetime
            f.write(f"{datetime.now()} - {msg}\n")
            f.flush()
            os.fsync(f.fileno())  # Force OS to write to disk
    except Exception as e:
        # Last resort - write to temp
        try:
            import tempfile
            with open(os.path.join(tempfile.gettempdir(), 'wazapos_emergency.log'), 'a') as f:
                f.write(f"{msg}\n")
                f.flush()
        except:
            pass

emergency_write("=" * 80)
emergency_write(f"SERVICE PROCESS STARTED")
emergency_write(f"Python executable: {sys.executable}")
emergency_write(f"Python version: {sys.version}")
emergency_write(f"Working directory: {os.getcwd()}")
emergency_write(f"Script: {__file__}")
emergency_write(f"sys.path: {sys.path[:3]}")
emergency_write("=" * 80)

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import traceback
import threading
import logging

emergency_write("Imports successful")

def setup_logging():
    """Setup logging with forced flushing"""
    log_dir = os.path.join(
        os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
        'WAZAPOS',
        'service'
    )
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'service_debug.log')
    
    # Create a custom handler that forces flushing
    class FlushingFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()  # Force flush after every log
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s - %(funcName)s - %(lineno)d',
        handlers=[
            FlushingFileHandler(log_file, mode='a'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing config
    )
    
    logger = logging.getLogger(__name__)
    
    # Test that logging works
    logger.info("=" * 80)
    logger.info("LOGGING INITIALIZED")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)
    
    # Force all handlers to flush
    for handler in logger.handlers:
        handler.flush()
    
    return logger

emergency_write("Setting up logging...")
logger = setup_logging()
emergency_write("Logging setup complete")


class YourAppService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WAZAPOS"
    _svc_display_name_ = "WAZAPOS App Background Service"
    _svc_description_ = "Runs scheduled tasks for WAZAPOS App"

    def __init__(self, args):
        emergency_write("__init__ called")
        logger.info("Initializing YourAppService")
        
        try:
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            socket.setdefaulttimeout(60)
            self.is_alive = True
            self.scheduler = None
            self.scheduler_thread = None
            
            logger.info("Service initialized successfully")
            emergency_write("Service initialized")
            
        except Exception as e:
            error_msg = f"Error in __init__: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            emergency_write(f"ERROR: {error_msg}")
            raise

    def SvcStop(self):
        emergency_write("SvcStop called")
        logger.info("Stop signal received")
        
        try:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)
            self.is_alive = False
            
            if self.scheduler:
                logger.info("Stopping scheduler...")
                self.scheduler.stop()
                logger.info("Scheduler stopped")
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                logger.info("Waiting for scheduler thread...")
                self.scheduler_thread.join(timeout=5)
                logger.info("Scheduler thread finished")
            
            logger.info("Service stop completed")
            emergency_write("Service stopped successfully")
            
        except Exception as e:
            error_msg = f"Error in SvcStop: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            emergency_write(f"ERROR: {error_msg}")

    def SvcDoRun(self):
        emergency_write("SvcDoRun called")
        logger.info("SvcDoRun - service starting")
        
        try:
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            emergency_write("Reported START_PENDING")
            
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            logger.info("Service reported as RUNNING")
            emergency_write("Service RUNNING")
            
            # Start scheduler
            self._start_scheduler_background()
            
            # Main loop
            self._main_loop()
            
            logger.info("Service ending normally")
            emergency_write("Service ending")
            
        except Exception as e:
            error_msg = f"FATAL ERROR in SvcDoRun: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            emergency_write(f"FATAL: {error_msg}")
            
            try:
                servicemanager.LogErrorMsg(f"Service failed: {e}")
            except:
                pass
            
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def _start_scheduler_background(self):
        """Start scheduler in background thread"""
        try:
            logger.info("Starting scheduler thread...")
            emergency_write("Starting scheduler thread")
            
            self.scheduler_thread = threading.Thread(
                target=self._initialize_scheduler_thread,
                daemon=False,
                name="SchedulerThread"
            )
            self.scheduler_thread.start()
            
            logger.info("Scheduler thread spawned")
            emergency_write("Scheduler thread spawned")
            
        except Exception as e:
            error_msg = f"Failed to spawn scheduler: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            emergency_write(f"ERROR: {error_msg}")

    def _initialize_scheduler_thread(self):
        """Initialize scheduler on separate thread"""
        emergency_write("Scheduler thread started")
        logger.info("Scheduler thread: initializing...")
        
        try:
            # Import scheduler module
            logger.info("Scheduler thread: importing TaskScheduler...")
            
            try:
                from scheduler import TaskScheduler
                logger.info("TaskScheduler imported successfully")
                emergency_write("TaskScheduler imported")
                
            except ImportError as e:
                error_msg = f"Failed to import scheduler: {e}\n{traceback.format_exc()}"
                logger.error(error_msg)
                emergency_write(f"IMPORT ERROR: {error_msg}")
                return
            
            # Create and start scheduler
            try:
                logger.info("Creating TaskScheduler instance...")
                self.scheduler = TaskScheduler()
                logger.info("TaskScheduler created")
                emergency_write("TaskScheduler created")
                
                logger.info("Starting TaskScheduler...")
                self.scheduler.start()
                logger.info("TaskScheduler started successfully")
                emergency_write("TaskScheduler started successfully")
                
                servicemanager.LogInfoMsg("TaskScheduler is running")
                
            except Exception as e:
                error_msg = f"Failed to start scheduler: {e}\n{traceback.format_exc()}"
                logger.error(error_msg)
                emergency_write(f"START ERROR: {error_msg}")
                
        except Exception as e:
            error_msg = f"FATAL in scheduler thread: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            emergency_write(f"FATAL: {error_msg}")

    def _main_loop(self):
        """Main service loop"""
        emergency_write("Entering main loop")
        logger.info("Entering main service loop")
        
        try:
            iteration = 0
            while self.is_alive:
                iteration += 1
                
                # Log heartbeat every 60 iterations (~5 minutes)
                if iteration % 60 == 0:
                    logger.info(f"Service heartbeat - iteration {iteration}")
                    emergency_write(f"Heartbeat {iteration}")
                
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    logger.info("Stop event received")
                    emergency_write("Stop event received")
                    break
            
            logger.info("Exiting main loop")
            emergency_write("Main loop exited")
            
        except Exception as e:
            error_msg = f"ERROR in main loop: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            emergency_write(f"LOOP ERROR: {error_msg}")
            raise


if __name__ == '__main__':
    emergency_write("__main__ executing")
    logger.info(f"Script started with args: {sys.argv}")
    
    try:
        if len(sys.argv) == 1:
            emergency_write("Running as service")
            logger.info("Running as Windows service")
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(YourAppService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            emergency_write(f"Command line: {sys.argv}")
            logger.info("Running command line handler")
            win32serviceutil.HandleCommandLine(YourAppService)
            
    except Exception as e:
        error_msg = f"FATAL in __main__: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        emergency_write(f"FATAL MAIN: {error_msg}")
        raise