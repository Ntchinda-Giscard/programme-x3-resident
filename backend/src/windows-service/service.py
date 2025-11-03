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
        format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
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

# Add the service directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
    logger.info(f"Added to sys.path: {script_dir}")

# Also add the permanent service directory
permanent_dir = os.path.join(
    os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
    'WAZAPOS',
    'service'
)
if permanent_dir not in sys.path:
    sys.path.insert(0, permanent_dir)
    logger.info(f"Added to sys.path: {permanent_dir}")


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
        """
        CRITICAL: This method must report SERVICE_RUNNING status IMMEDIATELY
        to avoid the 1053 timeout error. All heavy initialization must happen
        AFTER reporting the running status.
        """
        try:
            # STEP 1: Report running status FIRST, before doing ANY work
            # This is the most critical fix for error 1053
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            
            # STEP 2: Now we can do logging and other work safely
            logger.info("Service reported as RUNNING to Windows")
            logger.info("SvcDoRun called - service is starting")
            
            # STEP 3: Log to Windows Event Log (this can be slow, so do it AFTER reporting status)
            try:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, '')
                )
            except Exception as e:
                logger.warning(f"Could not log to Windows Event Log: {e}")
            
            # STEP 4: Now run the main loop (this is blocking, but Windows is happy now)
            logger.info("Calling main()...")
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
        """
        Main service loop - this runs AFTER we've reported SERVICE_RUNNING status.
        We can take our time here because Windows already knows we're running.
        """
        try:
            logger.info("Entering main() method")
            
            # Import scheduler here (lazy import) to avoid delays at module load time
            scheduler = None
            scheduler_error = None
            
            try:
                logger.info("Attempting to import scheduler module...")
                from scheduler import TaskScheduler
                logger.info("✓ Successfully imported TaskScheduler")
                
                # Initialize and start the scheduler
                logger.info("Initializing TaskScheduler...")
                scheduler = TaskScheduler()
                logger.info("✓ TaskScheduler instance created")
                
                logger.info("Starting scheduler...")
                scheduler.start()
                logger.info("✓ TaskScheduler started successfully")
                
                try:
                    servicemanager.LogInfoMsg("TaskScheduler started successfully")
                except:
                    pass
                
            except ImportError as e:
                scheduler_error = f"Import error: {str(e)}"
                logger.error(f"✗ Failed to import scheduler: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                try:
                    servicemanager.LogWarningMsg(
                        f"TaskScheduler not available: {scheduler_error}. "
                        "Service running in limited mode."
                    )
                except:
                    pass
                    
            except Exception as e:
                scheduler_error = f"Unexpected error: {str(e)}"
                logger.error(f"✗ Failed to start scheduler: {e}")
                logger.error(traceback.format_exc())
                
                try:
                    servicemanager.LogErrorMsg(f"Failed to start scheduler: {e}")
                except:
                    pass
            
            # Store scheduler reference for cleanup
            self.scheduler = scheduler
            
            # Keep the service running - this is the main loop
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