# windows-service/tasks.py
import logging
import sys
from datetime import datetime

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

def your_task_function():
    """Your scheduled task logic here"""
    try:
        logger.info("Task started")
        
        # Your task logic here
        # Example: Process data, send notifications, etc.
        
        logger.info("Task completed successfully")
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")