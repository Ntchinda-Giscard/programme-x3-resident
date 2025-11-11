# windowsService/tasks.py
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

logger = logging.getLogger(__name__)

# backend/src/windowsService/tasks.py
def your_task_function():
    """Example task function"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Task executed")