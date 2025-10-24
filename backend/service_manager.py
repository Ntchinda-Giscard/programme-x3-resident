# backend/service_manager.py
import logging
import subprocess
import win32serviceutil
import win32service
import pywintypes
import win32net
import win32netcon
import os
import sys


SERVICE_USER = "DIGITAL MARKET"
SERVICE_PASSWORD = "1478500"  # You can generate or encrypt this if needed

SERVICE_NAME = "WAZAPOS"
SERVICE_DISPLAY_NAME = "WAZAPOS App Background Service"
SERVICE_DESCRIPTION = "Runs scheduled tasks for WAZAPOS App"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

logger = logging.getLogger(__name__)

def create_service_user_if_needed(username, password):
    """Create a local Windows user if it doesn't exist."""
    try:
        win32net.NetUserGetInfo(None, username, 1) # type: ignore
        logger.info(f"User {username} already exists.")
        return
    except pywintypes.error as e:
        if e.winerror != 2221:  # 2221 = user does not exist
            raise

    print(f"Creating user {username}...")
    user_info = {
        "name": username,
        "password": password,
        "priv": win32netcon.USER_PRIV_USER,
        "home_dir": None,
        "comment": "Service account for Python app",
        "flags": win32netcon.UF_SCRIPT | win32netcon.UF_DONT_EXPIRE_PASSWD,
    }

    win32net.NetUserAdd(None, 1, user_info) # type: ignore
    subprocess.run(["net", "localgroup", "Administrators", username, "/add"], shell=True)
    logger.info(f" User {username} created and added to Administrators group.")


def get_service_script_path():
    """Get the absolute path to the service script"""
    # Get the backend directory (where this file is located)
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Build path to service.py
    service_script = os.path.join(backend_dir, 'src', 'windows-service', 'service.py')
    
    logger.info(f"Backend directory: {backend_dir}")
    logger.info(f"Service script path: {service_script}")
    logger.info(f"Service script exists: {os.path.exists(service_script)}")
    
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
    logger.info(f"Using Python: {python_exe}")
    # create_service_user_if_needed(SERVICE_USER, SERVICE_PASSWORD)
    
    cmd = [
        python_exe,
        service_script,
        '--username', f'.\\{SERVICE_USER}',
        '--password', SERVICE_PASSWORD,
        '--startup=auto',
        'install'
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    logger.info(f"Working directory: {os.path.dirname(service_script)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(service_script)
    )
    
    logger.info(f"Return code: {result.returncode}")
    logger.info(f"STDOUT: {result.stdout}")
    logger.info(f"STDERR: {result.stderr}")
    
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
            logger.info("Stopping service before uninstall...")
            stop_service()
    except Exception as e:
        logger.info(f"Warning: Could not stop service: {e}")
    
    try:
        service_script = get_service_script_path()
        
        cmd = [sys.executable, service_script, 'remove']
        
        logger.info(f"Running uninstall command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(service_script)
        )
        
        logger.info(f"Return code: {result.returncode}")
        logger.info(f"STDOUT: {result.stdout}")
        logger.info(f"STDERR: {result.stderr}")
        
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
        
        logger.info(f"Starting service: {SERVICE_NAME}")
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
        
        logger.info(f"Stopping service: {SERVICE_NAME}")
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