# backend/service_manager.py
import subprocess
import win32serviceutil
import win32service
import pywintypes
import os
import sys


SERVICE_USER = "WazaPOSUser"
SERVICE_PASSWORD = "StrongPassword123!"  # You can generate or encrypt this if needed

SERVICE_NAME = "WAZAPOS"
SERVICE_DISPLAY_NAME = "WAZAPOS App Background Service"
SERVICE_DESCRIPTION = "Runs scheduled tasks for WAZAPOS App"

def get_service_script_path():
    """Get the absolute path to the service script"""
    # Get the backend directory (where this file is located)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Build path to service.py
    service_script = os.path.join(backend_dir, 'src', 'windows-service', 'service.py')
    
    print(f"Backend directory: {backend_dir}")
    print(f"Service script path: {service_script}")
    print(f"Service script exists: {os.path.exists(service_script)}")
    
    if not os.path.exists(service_script):
        raise FileNotFoundError(f"Service script not found at: {service_script}")
    
    return service_script

def install_service():
    """Install the Windows service"""
    try:
        # Check if already installed
        status = get_service_status()
        if status['installed']:
            return "Service is already installed"
    except:
        pass
    
    service_script = get_service_script_path()
    
    # Use the current Python interpreter
    python_exe = sys.executable
    print(f"Using Python: {python_exe}")
    
    cmd = [
        python_exe,
        service_script,
        '--startup=auto',
        'install'
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {os.path.dirname(service_script)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(service_script)
    )
    
    print(f"Return code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")
    
    if result.returncode == 0:
        return "Service installed successfully and set to auto-start with Windows"
    else:
        raise Exception(f"Installation failed: {result.stderr or result.stdout}")

def uninstall_service():
    """Uninstall the Windows service"""
    try:
        # Stop service first if running
        status = get_service_status()
        if status['installed'] and status['status'] == 'running':
            print("Stopping service before uninstall...")
            stop_service()
    except Exception as e:
        print(f"Warning: Could not stop service: {e}")
    
    try:
        service_script = get_service_script_path()
        
        cmd = [sys.executable, service_script, 'remove']
        
        print(f"Running uninstall command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(service_script)
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            return "Service uninstalled successfully"
        else:
            raise Exception(f"Uninstallation failed: {result.stderr or result.stdout}")
    except Exception as e:
        raise Exception(f"Failed to uninstall service: {str(e)}")

def start_service():
    """Start the Windows service"""
    try:
        status = get_service_status()
        
        if not status['installed']:
            raise Exception("Service is not installed. Please install it first.")
        
        if status['status'] == 'running':
            return "Service is already running"
        
        if status['status'] == 'start_pending':
            return "Service is already starting"
        
        print(f"Starting service: {SERVICE_NAME}")
        win32serviceutil.StartService(SERVICE_NAME)
        
        # Wait a bit and verify it started
        import time
        time.sleep(2)
        new_status = get_service_status()
        
        if new_status['status'] == 'running':
            return "Service started successfully"
        else:
            return f"Service start initiated, current status: {new_status['status']}"
            
    except pywintypes.error as e:
        if e.winerror == 1056:  # Service is already running
            return "Service is already running"
        elif e.winerror == 1060:  # Service does not exist
            raise Exception("Service is not installed. Please install it first.")
        else:
            raise Exception(f"Failed to start service: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to start service: {str(e)}")

def stop_service():
    """Stop the Windows service"""
    try:
        status = get_service_status()
        
        if not status['installed']:
            raise Exception("Service is not installed")
        
        if status['status'] == 'stopped':
            return "Service is already stopped"
        
        if status['status'] == 'stop_pending':
            return "Service is already stopping"
        
        print(f"Stopping service: {SERVICE_NAME}")
        win32serviceutil.StopService(SERVICE_NAME)
        
        # Wait a bit and verify it stopped
        import time
        time.sleep(2)
        new_status = get_service_status()
        
        if new_status['status'] == 'stopped':
            return "Service stopped successfully"
        else:
            return f"Service stop initiated, current status: {new_status['status']}"
            
    except pywintypes.error as e:
        if e.winerror == 1062:  # Service has not been started
            return "Service is already stopped"
        elif e.winerror == 1060:  # Service does not exist
            raise Exception("Service is not installed")
        else:
            raise Exception(f"Failed to stop service: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to stop service: {str(e)}")

def restart_service():
    """Restart the Windows service"""
    try:
        status = get_service_status()
        
        if not status['installed']:
            raise Exception("Service is not installed")
        
        # Stop if running
        if status['status'] in ['running', 'start_pending']:
            print("Stopping service...")
            stop_service()
            import time
            time.sleep(3)  # Wait for clean shutdown
        
        # Start the service
        print("Starting service...")
        return start_service()
        
    except Exception as e:
        raise Exception(f"Failed to restart service: {str(e)}")

def get_service_status():
    """Get the current status of the service"""
    try:
        status_code = win32serviceutil.QueryServiceStatus(SERVICE_NAME)[1]
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
            "status": status_map.get(status_code, "unknown"),
            "status_code": status_code
        }
    except pywintypes.error as e:
        if e.winerror == 1060:  # Service does not exist
            return {
                "installed": False,
                "status": "not_installed",
                "status_code": None
            }
        else:
            raise Exception(f"Failed to query service status: {str(e)}")
    except Exception as e:
        return {
            "installed": False,
            "status": "not_installed",
            "status_code": None,
            "error": str(e)
        }

# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python service_manager.py install")
        print("  python service_manager.py uninstall")
        print("  python service_manager.py start")
        print("  python service_manager.py stop")
        print("  python service_manager.py status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "install":
            result = install_service()
            print(result)
        elif command == "uninstall":
            result = uninstall_service()
            print(result)
        elif command == "start":
            result = start_service()
            print(result)
        elif command == "stop":
            result = stop_service()
            print(result)
        elif command == "status":
            status = get_service_status()
            print(f"Service Status: {status}")
        else:
            print(f"Unknown command: {command}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()