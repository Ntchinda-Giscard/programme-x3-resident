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
import threading
import logging

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


class YourAppService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WAZAPOS"
    _svc_display_name_ = "WAZAPOS App Background Service"
    _svc_description_ = "Runs scheduled tasks for WAZAPOS App"

    def __init__(self, args):
        self.is_running = True

        try:
            logger.info("Initializing service...")
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            socket.setdefaulttimeout(60)
            self.is_alive = True
            self.scheduler = None
            self.scheduler_thread = None
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
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                logger.info("Waiting for scheduler thread to finish...")
                self.scheduler_thread.join(timeout=5)
                logger.info("✓ Scheduler thread finished")
            
            logger.info("✓ Service stop completed")
        except Exception as e:
            logger.error(f"✗ Error in SvcStop: {e}")
            logger.error(traceback.format_exc())

    def SvcDoRun(self):
        try:
            logger.info("SvcDoRun called - service is starting")
            
            # This prevents Windows from timing out (1053 error)
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # This must happen before any blocking operations
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            logger.info("✓ Service reported as RUNNING to Windows")
            
            # Now safely start the scheduler in background
            self._start_scheduler_background()
            
            # Keep service alive and responsive to Windows
            self._main_loop()
            
            logger.info("Main loop completed, service ending")
            
        except Exception as e:
            logger.error(f"✗ FATAL ERROR in SvcDoRun: {e}")
            logger.error(traceback.format_exc())
            
            try:
                servicemanager.LogErrorMsg(f"Service failed: {e}")
            except:
                pass
            
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def _start_scheduler_background(self):
        """Run scheduler in a separate thread - non-blocking"""
        try:
            logger.info("Starting scheduler initialization thread...")
            
            self.scheduler_thread = threading.Thread(
                target=self._initialize_scheduler_thread,
                daemon=False,
                name="SchedulerThread"
            )
            self.scheduler_thread.start()
            logger.info("✓ Scheduler thread spawned")
            
        except Exception as e:
            logger.error(f"✗ Failed to spawn scheduler thread: {e}")
            logger.error(traceback.format_exc())
            try:
                servicemanager.LogErrorMsg(f"Failed to start scheduler: {e}")
            except:
                pass

    def _initialize_scheduler_thread(self):
        """Initialize scheduler on separate thread - allows main thread to respond to Windows"""
        try:
            logger.info("Scheduler thread: Starting initialization...")
            
            # This prevents import delays from blocking service startup
            try:
                from scheduler import TaskScheduler
                logger.info("✓ Scheduler thread: Successfully imported TaskScheduler")
            except ImportError as e:
                logger.error(f"✗ Scheduler thread: Failed to import scheduler: {e}")
                logger.error(traceback.format_exc())
                try:
                    servicemanager.LogErrorMsg(f"Failed to import scheduler: {e}")
                except:
                    pass
                return
            except Exception as e:
                logger.error(f"✗ Scheduler thread: Unexpected error importing scheduler: {e}")
                logger.error(traceback.format_exc())
                try:
                    servicemanager.LogErrorMsg(f"Unexpected error importing scheduler: {e}")
                except:
                    pass
                return
            
            # Now instantiate and start the scheduler
            try:
                self.scheduler = TaskScheduler()
                logger.info("✓ Scheduler thread: TaskScheduler instance created")
                
                self.scheduler.start()
                logger.info("✓ Scheduler thread: TaskScheduler started successfully")
                
                try:
                    servicemanager.LogInfoMsg("TaskScheduler started successfully")
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"✗ Scheduler thread: Failed to instantiate/start scheduler: {e}")
                logger.error(traceback.format_exc())
                try:
                    servicemanager.LogErrorMsg(f"Failed to start scheduler: {e}")
                except:
                    pass
                
        except Exception as e:
            logger.error(f"✗ FATAL ERROR in scheduler thread: {e}")
            logger.error(traceback.format_exc())

    def _main_loop(self):
        """Main service loop - keeps service responsive to Windows"""
        try:
            logger.info("Entering main service loop...")
            
            while self.is_alive:
                # WaitForSingleObject with timeout keeps service responsive
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    logger.info("Stop event received")
                    break
            
            logger.info("Exiting main service loop")
            
        except Exception as e:
            logger.error(f"✗ FATAL ERROR in main loop: {e}")
            logger.error(traceback.format_exc())
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
        raise e
