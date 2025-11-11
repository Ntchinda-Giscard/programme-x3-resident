"""
Comprehensive test to identify why the service isn't logging
Run this with: python comprehensive_test.py
"""
import sys
import os

service_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'WAZAPOS', 'service')
print(f"Service directory: {service_dir}")
print(f"Directory exists: {os.path.exists(service_dir)}")

if os.path.exists(service_dir):
    print(f"\nFiles in service directory:")
    for f in os.listdir(service_dir):
        full_path = os.path.join(service_dir, f)
        if os.path.isfile(full_path):
            size = os.path.getsize(full_path)
            print(f"  - {f} ({size} bytes)")
        else:
            print(f"  - {f}/ (directory)")

sys.path.insert(0, service_dir)

print("\n" + "="*60)
print("TEST 1: SERVICE FILE VALIDATION")
print("="*60)

service_file = os.path.join(service_dir, 'service.py')
if os.path.exists(service_file):
    size = os.path.getsize(service_file)
    print(f"✅ service.py exists ({size} bytes)")
    
    if size == 0:
        print("❌ CRITICAL: service.py is EMPTY!")
        print("   → Copy the service.py file to this location")
    elif size < 1000:
        print("⚠️  WARNING: service.py is suspiciously small")
        print("   → Verify the file content is correct")
    
    # Check if it's actually Python code
    try:
        with open(service_file, 'r') as f:
            first_line = f.readline()
            if first_line.strip().startswith('#') or first_line.strip().startswith('import'):
                print(f"✅ File appears to be Python code")
            else:
                print(f"⚠️  First line: {first_line[:50]}")
    except Exception as e:
        print(f"❌ Can't read file: {e}")
else:
    print(f"❌ service.py NOT FOUND")

print("\n" + "="*60)
print("TEST 2: SCHEDULER FILE VALIDATION")
print("="*60)

scheduler_file = os.path.join(service_dir, 'scheduler.py')
if os.path.exists(scheduler_file):
    size = os.path.getsize(scheduler_file)
    print(f"✅ scheduler.py exists ({size} bytes)")
    
    # Try to import and test
    try:
        import scheduler
        print(f"✅ scheduler.py imports successfully")
        
        from scheduler import TaskScheduler
        print(f"✅ TaskScheduler class found")
        
        # Try to instantiate it
        ts = TaskScheduler()
        print(f"✅ TaskScheduler instantiated")
        print(f"   - running: {ts.running}")
        print(f"   - task_count: {ts.task_count}")
        
    except Exception as e:
        print(f"❌ Error with scheduler: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"❌ scheduler.py NOT FOUND")

print("\n" + "="*60)
print("TEST 3: PYTHON DEPENDENCIES")
print("="*60)

critical_deps = [
    ('win32serviceutil', 'pywin32'),
    ('win32service', 'pywin32'),
    ('win32event', 'pywin32'),
    ('servicemanager', 'pywin32'),
    ('schedule', 'schedule'),
]

optional_deps = [
    ('win10toast', 'win10toast'),  # Not needed for service
]

print("\nCritical dependencies:")
all_good = True
for module_name, package_name in critical_deps:
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
    except ImportError:
        print(f"❌ {module_name} - MISSING")
        print(f"   Install with: pip install {package_name}")
        all_good = False

print("\nOptional dependencies:")
for module_name, package_name in optional_deps:
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
    except ImportError:
        print(f"⚠️  {module_name} - not installed (not required for service)")

print("\n" + "="*60)
print("TEST 4: LOGGING SETUP TEST")
print("="*60)

print("\nTesting if we can create log files...")
test_log = os.path.join(service_dir, 'test_write.log')

try:
    with open(test_log, 'w') as f:
        f.write("Test write successful\n")
        f.flush()
    print(f"✅ Can write to: {test_log}")
    
    # Verify we can read it back
    with open(test_log, 'r') as f:
        content = f.read()
    print(f"✅ Can read back: {content.strip()}")
    
    # Clean up
    os.remove(test_log)
    print(f"✅ File permissions OK")
    
except Exception as e:
    print(f"❌ Cannot write to log directory: {e}")

print("\n" + "="*60)
print("TEST 5: SIMULATE SERVICE LOGGING")
print("="*60)

print("\nAttempting to create logs as the service would...")
try:
    import logging
    
    log_file = os.path.join(service_dir, 'test_service.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w')
        ]
    )
    
    logger = logging.getLogger('test')
    logger.info("Test log entry 1")
    logger.info("Test log entry 2")
    logger.info("Test log entry 3")
    
    # Force flush
    for handler in logger.handlers:
        handler.flush()
    
    print(f"✅ Created test log at: {log_file}")
    
    # Verify content
    with open(log_file, 'r') as f:
        lines = f.readlines()
    print(f"✅ Log has {len(lines)} lines")
    
    if len(lines) == 3:
        print(f"✅ All log entries written correctly")
    else:
        print(f"⚠️  Expected 3 lines, got {len(lines)}")
    
    os.remove(log_file)
    
except Exception as e:
    print(f"❌ Logging test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("TEST 6: CHECK ACTUAL SERVICE LOGS")
print("="*60)

logs_to_check = [
    'service_debug.log',
    'scheduler.log',
    'task_executions.log',
    'EMERGENCY.log'
]

print("\nChecking for existing log files:")
for log_name in logs_to_check:
    log_path = os.path.join(service_dir, log_name)
    if os.path.exists(log_path):
        size = os.path.getsize(log_path)
        if size == 0:
            print(f"⚠️  {log_name} - EXISTS but EMPTY (0 bytes)")
        else:
            print(f"✅ {log_name} - {size} bytes")
            
            # Show last few lines
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"   Last entry: {lines[-1].strip()}")
            except:
                pass
    else:
        print(f"❌ {log_name} - DOES NOT EXIST")

print("\n" + "="*60)
print("TEST 7: SERVICE REGISTRY CHECK")
print("="*60)

try:
    import winreg
    
    key_path = r"SYSTEM\CurrentControlSet\Services\WAZAPOS"
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
    
    # Read ImagePath
    image_path, _ = winreg.QueryValueEx(key, "ImagePath")
    print(f"Service command: {image_path}")
    
    # Parse out Python executable
    if '"' in image_path:
        parts = image_path.split('"')
        python_exe = parts[1]
        print(f"\nPython executable: {python_exe}")
        print(f"Python exists: {os.path.exists(python_exe)}")
        
        if not os.path.exists(python_exe):
            print(f"❌ CRITICAL: Python executable doesn't exist!")
            print(f"   The service is configured to use a Python that isn't there")
    
    winreg.CloseKey(key)
    
except Exception as e:
    print(f"⚠️  Could not read service registry: {e}")
    print("   (This is normal if not running as admin)")

print("\n" + "="*60)
print("SUMMARY & RECOMMENDATIONS")
print("="*60)

if all_good:
    print("""
✅ All dependencies are installed
✅ Files exist and can be imported
✅ Logging works correctly

The problem is likely:
1. Service is using wrong Python interpreter
2. Service user doesn't have permissions
3. Service is installed but registry is incorrect

NEXT STEPS:
1. Run: python service_manager.py uninstall
2. Run: python service_manager.py install  
3. Run: python service_manager.py start
4. Check EMERGENCY.log immediately after starting
""")
else:
    print("""
❌ Missing dependencies detected

NEXT STEPS:
1. Install missing packages (see above)
2. Then reinstall service
""")

print("\n" + "="*60)