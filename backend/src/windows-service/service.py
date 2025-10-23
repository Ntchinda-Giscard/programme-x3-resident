# backend/src/windows-service/service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import time
from scheduler import TaskScheduler

class YourAppService(win32serviceutil.ServiceFramework):
    _svc_name_ = "YourAppService"
    _svc_display_name_ = "Your App Background Service"
    _svc_description_ = "Runs scheduled tasks for Your App"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True
        self.scheduler = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False
        if self.scheduler:
            self.scheduler.stop()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # Initialize and start the scheduler
        self.scheduler = TaskScheduler()
        self.scheduler.start()
        
        # Keep the service running
        while self.is_alive:
            # Wait for stop signal (check every second)
            rc = win32event.WaitForSingleObject(self.hWaitStop, 1000)
            if rc == win32event.WAIT_OBJECT_0:
                break

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(YourAppService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(YourAppService)