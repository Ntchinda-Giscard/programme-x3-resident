# backend/src/windows-service/service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import time

# CRITICAL: Set up paths and logging BEFORE any other imports
# This ensures we can debug what's happening even if imports fail
log_dir = os.path.join(
    os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
    'WAZAPOS',
    'service'
)
os.makedirs(log_dir, exist_ok=True)

import logging
log_file = os.path.join(log_dir, 'service_debug.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("SERVICE PROCESS STARTING")
logger.info(f"Python: {sys.executable}")
logger.info(f"Version: {sys.version}")
logger.info(f"CWD: {os.getcwd()}")
logger.info(f"Script: {__file__}")
logger.info("=" * 80)

# Add service directories to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, log_dir)  # Also add the log directory as a fallback

logger.info(f"sys.path: {sys.path}")


class WazaposService(win32serviceutil.ServiceFramework):
    """
    Windows service for WAZAPOS background tasks.
    
    This service is designed to start quickly and avoid the 1053 timeout error
    by reporting its running status immediately, then doing all initialization
    work afterwards.
    """
    
    _svc_name_ = "WAZAPOS"
    _svc_display_name_ = "WAZAPOS App Background Service"
    _svc_description_ = "Runs scheduled tasks for WAZAPOS App"

    def __init__(self, args):
        """
        Initialize the service framework.
        This must be fast - no heavy work here.
        """
        logger.info("Service __init__ called")
        win32serviceutil.ServiceFramework.__init__(self, args)
        
        # Create an event to signal when to stop
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False
        self.scheduler = None
        
        logger.info("Service __init__ completed")

    def SvcStop(self):
        """
        Called when Windows wants to stop the service.
        """
        logger.info("=== SERVICE STOP REQUESTED ===")
        
        # Tell Windows we're stopping
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        # Signal our main loop to exit
        win32event.SetEvent(self.stop_event)
        self.is_running = False
        
        # Stop the scheduler if it exists
        if self.scheduler:
            try:
                logger.info("Stopping scheduler...")
                self.scheduler.stop()
                logger.info("Scheduler stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}", exc_info=True)
        
        logger.info("Service stop completed")

    def SvcDoRun(self):
        """
        This is the main entry point when the service starts.
        
        CRITICAL FOR ERROR 1053 FIX:
        We MUST call ReportServiceStatus(SERVICE_RUNNING) as the very first
        thing we do. Windows expects this within 30 seconds, but we do it
        immediately (within milliseconds) to avoid any timeout issues.
        """
        try:
            # === CRITICAL: Report running status IMMEDIATELY ===
            # This MUST be the first thing we do to avoid error 1053
            # Everything else happens AFTER this line
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            
            # Now that Windows knows we're running, we can take our time
            logger.info("=== SERVICE STARTED SUCCESSFULLY ===")
            logger.info("Reported SERVICE_RUNNING to Windows")
            
            # Try to log to Windows Event Log
            try:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, '')
                )
            except:
                pass  # Don't fail if event log doesn't work
            
            # Now run our actual service logic
            self.run_service()
            
        except Exception as e:
            logger.error(f"FATAL ERROR in SvcDoRun: {e}", exc_info=True)
            try:
                servicemanager.LogErrorMsg(f"Service failed: {e}")
            except:
                pass

    def run_service(self):
        """
        The actual service logic runs here.
        This is called AFTER we've told Windows we're running.
        """
        logger.info("Starting service logic...")
        self.is_running = True
        
        # Try to initialize the scheduler
        try:
            logger.info("Attempting to import and start scheduler...")
            from scheduler import TaskScheduler
            
            self.scheduler = TaskScheduler()
            self.scheduler.start()
            
            logger.info("Scheduler started successfully")
            
            try:
                servicemanager.LogInfoMsg("TaskScheduler initialized")
            except:
                pass
                
        except ImportError as e:
            logger.warning(f"Could not import scheduler: {e}")
            logger.warning("Service will run without scheduled tasks")
            
            try:
                servicemanager.LogWarningMsg(
                    f"Scheduler not available: {e}. Service running without tasks."
                )
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}", exc_info=True)
            logger.warning("Service will continue without scheduler")
        
        # Main service loop - just wait for stop signal
        logger.info("Entering main service loop (waiting for stop signal)...")
        
        while self.is_running:
            # Wait for stop event (check every 5 seconds)
            result = win32event.WaitForSingleObject(self.stop_event, 5000)
            
            if result == win32event.WAIT_OBJECT_0:
                # Stop event was signaled
                logger.info("Stop signal received")
                break
        
        logger.info("Service loop exited")


# When running as a script (for install/remove commands)
if __name__ == '__main__':
    logger.info(f"Script called with args: {sys.argv}")
    
    if len(sys.argv) == 1:
        # No arguments - running as a service
        logger.info("Starting as Windows service...")
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(WazaposService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception as e:
            logger.error(f"Service dispatcher error: {e}", exc_info=True)
    else:
        # Command line arguments - install/remove/start/stop
        logger.info("Running command line handler...")
        try:
            win32serviceutil.HandleCommandLine(WazaposService)
        except Exception as e:
            logger.error(f"Command line error: {e}", exc_info=True)
            raise