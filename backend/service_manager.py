# python-backend/service_manager.py
import subprocess
import win32serviceutil
import os

SERVICE_NAME = "YourAppService"
SERVICE_DISPLAY_NAME = "Your App Background Service"
SERVICE_DESCRIPTION = "Runs scheduled tasks for Your App"

def install_service():
    """Install the Windows service"""
    service_script = os.path.join(os.path.dirname(__file__), 'src', 'windows-service', 'service.py')
    
    cmd = [
        'python',
        service_script,
        '--startup=auto',
        'install'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return "Service installed successfully"
    else:
        raise Exception(f"Installation failed: {result.stderr}")

def uninstall_service():
    """Uninstall the Windows service"""
    try:
        win32serviceutil.StopService(SERVICE_NAME)
    except:
        pass  # Service might not be running
    
    service_script = os.path.join(os.path.dirname(__file__), 'src', 'windows-service', 'service.py')
    
    cmd = ['python', service_script, 'remove']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return "Service uninstalled successfully"
    else:
        raise Exception(f"Uninstallation failed: {result.stderr}")

def start_service():
    """Start the Windows service"""
    win32serviceutil.StartService(SERVICE_NAME)
    return "Service started successfully"

def stop_service():
    """Stop the Windows service"""
    win32serviceutil.StopService(SERVICE_NAME)
    return "Service stopped successfully"

def get_service_status():
    """Get the current status of the service"""
    try:
        status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)[1]
        status_map = {
            1: "stopped",
            2: "start_pending",
            3: "stop_pending",
            4: "running",
            5: "continue_pending",
            6: "pause_pending",
            7: "paused"
        }
        return {
            "installed": True,
            "status": status_map.get(status, "unknown")
        }
    except Exception as e:
        return {
            "installed": False,
            "status": "not_installed"
        }