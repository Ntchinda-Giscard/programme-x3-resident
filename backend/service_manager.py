import logging
import subprocess
import win32serviceutil
import win32service
import pywintypes
import win32net
import win32netcon
import os
import sys
import shutil


SERVICE_NAME = "WAZAPOS_TEST"
SERVICE_DISPLAY_NAME = "WAZAPOS_TEST"
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

def get_permanent_service_dir():
    """Get or create a permanent directory for service files"""
    app_data = os.getenv('LOCALAPPDATA')
    
    # Handle case where LOCALAPPDATA is not set
    if not app_data:
        # Fallback to APPDATA or a default location
        app_data = os.getenv('APPDATA')
        if not app_data:
            # Last resort: use user's home directory
            app_data = os.path.expanduser('~')
    
    service_dir = os.path.join(app_data, 'WAZAPOS', 'service')
    os.makedirs(service_dir, exist_ok=True)
    return service_dir

def get_service_script_path():
    """Get the absolute path to the service script"""
    
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        logger.info("Running as compiled executable")
        
        # Use permanent location for service files
        permanent_dir = get_permanent_service_dir()
        service_script = os.path.join(permanent_dir, 'service.py')
        
        logger.info(f"Permanent service directory: {permanent_dir}")
        
        # If service script doesn't exist in permanent location, copy it from bundle
        if not os.path.exists(service_script):
            logger.info("Service script not found in permanent location, attempting to copy from bundle")
            
            # Get _MEIPASS directory safely
            meipass = getattr(sys, '_MEIPASS', None)
            if meipass:
                possible_sources = [
                    os.path.join(meipass, 'src', 'windowsService', 'service.py'),
                    os.path.join(meipass, 'windowsService', 'service.py'),
                    os.path.join(meipass, 'service.py'),
                ]
                
                for source in possible_sources:
                    logger.info(f"Checking for service script at: {source}")
                    if os.path.exists(source):
                        logger.info(f"Found service script at: {source}")
                        shutil.copy2(source, service_script)
                        
                        # Also copy scheduler.py if it exists
                        scheduler_source = os.path.join(os.path.dirname(source), 'scheduler.py')
                        if os.path.exists(scheduler_source):
                            shutil.copy2(scheduler_source, os.path.join(permanent_dir, 'scheduler.py'))
                            logger.info("Copied scheduler.py as well")
                        
                        break
                else:
                    # List what's actually in _MEIPASS for debugging
                    logger.info(f"Contents of _MEIPASS: {os.listdir(meipass)}")
                    raise FileNotFoundError(f"Service script not found in bundle. Checked: {possible_sources}")
    else:
        # Running in development mode
        logger.info("Running in development mode")
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        service_script = os.path.join(backend_dir, 'src', 'windowsService', 'service.py')
    
    logger.info(f"Final service script path: {service_script}")
    logger.info(f"Service script exists: {os.path.exists(service_script)}")
    
    if not os.path.exists(service_script):
        raise FileNotFoundError(f"Service script not found at: {service_script}")
    
    return service_script

def create_service_user_if_needed(username, password):
    """Create a local Windows user if it doesn't exist."""
    try:
        win32net.NetUserGetInfo(None, username, 1) # type: ignore
        logger.info(f"User {username} already exists.")
        return
    except pywintypes.error as e:
        if e.winerror != 2221:
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
    logger.info(f"User {username} created and added to Administrators group.")

def get_python_executable():
    """Get Python executable path"""
    if getattr(sys, 'frozen', False):
        # When frozen, look for bundled Python
        exe_dir = os.path.dirname(sys.executable)
        
        # Check for bundled Python in several locations
        possible_paths = [
            os.path.join(exe_dir, 'python', 'python.exe'),
            os.path.join(exe_dir, 'resources', 'python', 'python.exe'),
            os.path.join(os.path.dirname(exe_dir), 'python', 'python.exe'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found bundled Python at: {path}")
                return path
        
        # Fallback: try to find system Python
        import shutil
        system_python = shutil.which('python') or shutil.which('python3')
        if system_python:
            logger.info(f"Using system Python at: {system_python}")
            return system_python
        
        raise FileNotFoundError("No Python interpreter found. Please ensure Python is installed or bundle it with your app.")
    else:
        # Development mode - use current interpreter
        return sys.executable


def install_service():
    """Install the Windows service"""
    try:
        status = get_service_status()
        logger.info(f'=====Current service status: {status}')
        if status['installed']:
            logger.info("Service already installed, returning early")
            return "Service is already installed"
    except Exception as e:
        logger.error(f'Error checking service status: {e}')
        raise e
    
    service_script = get_service_script_path()
    python_exe = get_python_executable()
    
    logger.info(f"Using Python: {python_exe}")
    logger.info(f"Service script: {service_script}")
    
    cmd = [
        python_exe,
        service_script,
        # '--username', f'.\\{SERVICE_USER}',
        # '--password', SERVICE_PASSWORD,
        '--startup=auto',
        'install'
    ]
    
    logger.info(f"Running install command: {' '.join(cmd)}")
    logger.info(f"Working directory: {os.path.dirname(service_script)}")
    
    try:
        # Execute the installation command with timeout
        logger.info("About to execute subprocess.run...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(service_script),
            timeout=30  # Add 30 second timeout
        )
        
        logger.info(f"Subprocess completed")
        logger.info(f"Return code: {result.returncode}")
        logger.info(f"STDOUT: {result.stdout}")
        logger.info(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            success_msg = "Service installed successfully"
            logger.info(f"Returning success: {success_msg}")
            return success_msg
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"Installation failed with error: {error_msg}")
            raise Exception(f"Installation failed: {error_msg}")
    
    except subprocess.TimeoutExpired as e:
        logger.error(f"Installation command timed out after 30 seconds")
        raise Exception(f"Installation timed out: {str(e)}")
    except subprocess.SubprocessError as e:
        logger.error(f"Subprocess error: {e}")
        raise Exception(f"Failed to execute install command: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during installation: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to install service: {str(e)}")
    
    
def uninstall_service():
    """Uninstall the Windows service"""
    try:
        # Stop service first if running
        status = get_service_status()
        logger.info(f'=====Current service status: {status}')
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
        logger.info(f'=====Current service status: {status}')
        
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
        logger.info(f'=====Current service status: {status}')
        
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
        logger.info(f'=====Current service status: {status}')
        
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
        service_satus = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        logger.info(f"=== Service status {service_satus}")
        status_code = service_satus[1]
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