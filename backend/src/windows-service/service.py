# backend/src/windows-service/service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import time
import os
import traceback
from scheduler import TaskScheduler

# Set up file logging BEFORE anything else
def setup_logging():
    """Setup logging to file so we can debug service issues"""
    log_dir = os.path.join(
        os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
        'WAZAPOS',
        'service'
    )
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'service_debug.log')
    
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()
logger.info("=" * 80)
logger.info("SERVICE STARTING - Log initialized")
logger.info("=" * 80)

# Try to import scheduler with detailed error logging
SCHEDULER_AVAILABLE = False
SCHEDULER_ERROR = None

try:
    logger.info("Attempting to import scheduler module...")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Script directory: {os.path.dirname(__file__)}")
    logger.info(f"sys.path: {sys.path}")
    
    # Import the TaskScheduler class from scheduler module
    from scheduler import TaskScheduler
    
    SCHEDULER_AVAILABLE = True
    logger.info("✓ Successfully imported TaskScheduler")
    logger.info(f"TaskScheduler type: {type(TaskScheduler)}")
    
except ImportError as e:
    SCHEDULER_ERROR = f"Import error: {str(e)}"
    logger.error(f"✗ Failed to import scheduler (ImportError): {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Also log to Windows Event Log (if available)
    try:
        servicemanager.LogErrorMsg(f"Failed to import scheduler: {e}")
    except:
        pass
        
except Exception as e:
    SCHEDULER_ERROR = f"Unexpected error: {str(e)}"
    logger.error(f"✗ Failed to import scheduler (Exception): {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    try:
        servicemanager.LogErrorMsg(f"Failed to import scheduler: {e}")
    except:
        pass


class YourAppService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WAZAPOS"
    _svc_display_name_ = "WAZAPOS App Background Service"
    _svc_description_ = "Runs scheduled tasks for WAZAPOS App"

    def __init__(self, args):
        try:
            logger.info("Initializing service...")
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            socket.setdefaulttimeout(60)
            self.is_alive = True
            self.scheduler = None
            logger.info("✓ Service initialized successfully")
        except Exception as e:
            logger.error(f"✗ Error in __init__: {e}")
            logger.error(traceback.format_exc())
            raise

    def SvcStop(self):
        try:
            logger.info("Stop signal received")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)
            self.is_alive = False
            
            if self.scheduler:
                logger.info("Stopping scheduler...")
                try:
                    self.scheduler.stop()
                    logger.info("✓ Scheduler stopped")
                except Exception as e:
                    logger.error(f"Error stopping scheduler: {e}")
            
            logger.info("✓ Service stop completed")
        except Exception as e:
            logger.error(f"✗ Error in SvcStop: {e}")
            logger.error(traceback.format_exc())

    def SvcDoRun(self):
        try:
            logger.info("SvcDoRun called - service is starting")
            
            # Report that we're starting
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            
            # Log to Windows Event Log
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            logger.info("Calling main()...")
            
            # Report that we've started successfully BEFORE running main
            # This prevents the 1053 timeout error
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            
            # Now run the main loop
            self.main()
            
            logger.info("Main() completed, service ending")
            
        except Exception as e:
            logger.error(f"✗ FATAL ERROR in SvcDoRun: {e}")
            logger.error(traceback.format_exc())
            
            try:
                servicemanager.LogErrorMsg(f"Service failed: {e}")
            except:
                pass
            
            # Report service stopped due to error
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def main(self):
        try:
            logger.info("Entering main() method")
            
            if not SCHEDULER_AVAILABLE:
                logger.warning("Scheduler not available - running in limited mode")
                logger.warning(f"Scheduler error was: {SCHEDULER_ERROR}")
                
                try:
                    servicemanager.LogWarningMsg(
                        f"TaskScheduler not available: {SCHEDULER_ERROR}. "
                        "Service running in limited mode."
                    )
                except:
                    pass
                
                # Keep service alive but don't do anything
                logger.info("Entering wait loop (limited mode)...")
                while self.is_alive:
                    rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                    if rc == win32event.WAIT_OBJECT_0:
                        logger.info("Stop event received in limited mode")
                        break
                return
            
            # Initialize and start the scheduler
            logger.info("Initializing TaskScheduler...")
            try:
                if SCHEDULER_AVAILABLE and 'TaskScheduler' in globals():
                    self.scheduler = TaskScheduler()
                    logger.info("✓ TaskScheduler instance created")
                else:
                    raise ImportError("TaskScheduler is not available")
                
                logger.info("Starting scheduler...")
                self.scheduler.start()
                logger.info("✓ TaskScheduler started successfully")
                
                try:
                    servicemanager.LogInfoMsg("TaskScheduler started successfully")
                except:
                    pass
                
            except Exception as e:
                logger.error(f"✗ Failed to start scheduler: {e}")
                logger.error(traceback.format_exc())
                try:
                    servicemanager.LogErrorMsg(f"Failed to start scheduler: {e}")
                except:
                    pass
                # Continue anyway, just without scheduler
            
            # Keep the service running
            logger.info("Entering main service loop...")
            while self.is_alive:
                # Wait for stop signal (check every 5 seconds)
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    logger.info("Stop event received")
                    break
            
            logger.info("Exiting main service loop")
            
        except Exception as e:
            logger.error(f"✗ FATAL ERROR in main(): {e}")
            logger.error(traceback.format_exc())
            try:
                servicemanager.LogErrorMsg(f"Fatal error in main: {e}")
            except:
                pass
            raise


if __name__ == '__main__':
    try:
        logger.info("Service script executed")
        logger.info(f"Arguments: {sys.argv}")
        
        if len(sys.argv) == 1:
            logger.info("Running as service...")
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(YourAppService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            logger.info("Running command line handler...")
            win32serviceutil.HandleCommandLine(YourAppService)
            
    except Exception as e:
        logger.error(f"✗ FATAL ERROR in __main__: {e}")
        logger.error(traceback.format_exc())
        raise