from src.windowsService.scheduler import TaskScheduler
import time

if __name__ == "__main__":
    sched = TaskScheduler()
    sched.start()

    print("Scheduler running... Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        sched.stop()
