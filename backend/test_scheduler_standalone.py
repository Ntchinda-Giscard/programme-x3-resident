"""
Test the scheduler directly without the Windows service
This will run the scheduler for 2 minutes so you can verify it works

Usage: python test_scheduler_standalone.py
"""
import sys
import os
import time

# Add the service directory to path so we can import scheduler
service_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'WAZAPOS', 'service')
sys.path.insert(0, service_dir)

print("=" * 70)
print("STANDALONE SCHEDULER TEST")
print("=" * 70)
print(f"Service directory: {service_dir}")
print(f"Log files will be in: {service_dir}")
print()

# Import the scheduler
try:
    from scheduler import TaskScheduler
    print("✅ Successfully imported TaskScheduler")
except ImportError as e:
    print(f"❌ Failed to import TaskScheduler: {e}")
    print("\nMake sure scheduler.py is in the service directory:")
    print(f"  {service_dir}")
    sys.exit(1)

# Create and start the scheduler
print("\n" + "=" * 70)
print("STARTING SCHEDULER")
print("=" * 70)

try:
    scheduler = TaskScheduler()
    print("✅ TaskScheduler created")
    
    scheduler.start()
    print("✅ Scheduler started")
    print()
    print("Scheduler is now running...")
    print("Tasks are scheduled to run:")
    print("  - Every 5 minutes")
    print("  - Every hour")
    print("  - Daily at 10:30 AM")
    print()
    print("This test will run for 2 minutes (enough to see if it's working)")
    print("Watch the console output and check the log files")
    print()
    print("Press Ctrl+C to stop early")
    print("=" * 70)
    print()
    
    # Run for 2 minutes
    for i in range(120):
        time.sleep(1)
        
        # Show progress every 10 seconds
        if (i + 1) % 10 == 0:
            elapsed = i + 1
            remaining = 120 - elapsed
            print(f"⏱️  {elapsed}s elapsed, {remaining}s remaining... (Total tasks executed: {scheduler.task_count})")
    
    print()
    print("=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)
    
except KeyboardInterrupt:
    print("\n\n⏹️  Stopped by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Stop the scheduler
    try:
        scheduler.stop()
        print(f"\n✅ Scheduler stopped")
        print(f"📊 Total tasks executed: {scheduler.task_count}")
    except:
        pass
    
    # Show log file locations
    print("\n" + "=" * 70)
    print("CHECK THESE LOG FILES:")
    print("=" * 70)
    print(f"1. Scheduler log:")
    print(f"   {os.path.join(service_dir, 'scheduler.log')}")
    print()
    print(f"2. Task executions log:")
    print(f"   {os.path.join(service_dir, 'task_executions.log')}")
    print()
    
    # Try to show task execution count from log
    task_log = os.path.join(service_dir, 'task_executions.log')
    if os.path.exists(task_log):
        with open(task_log, 'r') as f:
            lines = f.readlines()
        print(f"✅ Found {len(lines)} task execution(s) in log file")
        if lines:
            print("\nLast 5 executions:")
            for line in lines[-5:]:
                print(f"  {line.strip()}")
    else:
        print("⚠️  No task_executions.log found - no tasks have executed yet")
        print("   This might mean:")
        print("   - The 5-minute timer hasn't triggered yet (wait longer)")
        print("   - There's an error in the task function")
    
    print("\n" + "=" * 70)