import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import logging
from pathlib import Path
from typing import List
import time

# Setup logging
log_dir = Path(os.getenv('APPDATA') or os.path.expanduser('~')) / 'WAZAPOS' / 'service'
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'test_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MinimalTestService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WAZAPOS_TEST"
    _svc_display_name_ = "WAZAPOS Test Service"
    _svc_description_ = "Test service for WAZAPOS"

    def __init__(self, args: List[str]):
        # CRITICAL: Must call parent __init__ FIRST
        win32serviceutil.ServiceFramework.__init__(self, args)  # type: ignore
        # Create the stop event AFTER parent init
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False
        logger.info("Service initialized")

    def SvcStop(self):
        logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False

    def SvcDoRun(self):
        logger.info("Service starting...")
        try:
            # Report that service is running
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            logger.info("Service is now running")
            self.is_running = True

            # Main loop - just wait for stop event
            while self.is_running:
                # Wait for stop event (timeout 5 seconds)
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    logger.info("Stop event received")
                    break

        except Exception as e:
            logger.exception(f"Error in SvcDoRun: {e}")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            raise

        logger.info("Service stopped")
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


def handle_command_line(argv: List[str]) -> None:
    try:
        w32ts = win32serviceutil.GetServiceClassString(MinimalTestService)
        win32serviceutil.HandleCommandLine(MinimalTestService)
    except Exception as e:
        logger.exception(f"Command line error: {e}")
        print(f"Error: {e}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        print('2025-11-05 12:43:17,089 - INFO - Running in debug mode')
        try:
            log_dir = Path(os.getenv('APPDATA') or Path.home()) / 'WAZAPOS' / 'service'
            log_dir.mkdir(parents=True, exist_ok=True)
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / 'test_service_debug.log'),
                    logging.StreamHandler()
                ]
            )
            
            logging.info('Debug mode: Running service logic directly')
            logging.info('Service is running. Press Ctrl+C to stop.')
            
            # Run the service main logic directly
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info('Service stopped by user')
        except Exception as e:
            logging.error(f"Error: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
    else:
        win32serviceutil.HandleCommandLine(MinimalTestService)

