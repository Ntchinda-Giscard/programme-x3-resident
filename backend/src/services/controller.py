# backend/src/services/controller.py
import logging
import sys
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .model import ServiceResponse, ServiceStatus
import service_manager

service_router = APIRouter(
    prefix="/service",
    tags=["service management"]
)

# Configure logging to help with debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

logger = logging.getLogger(__name__)



@service_router.post("/install", response_model=ServiceResponse)
async def install_service():
    try:
        result = service_manager.install_service()
        logger.info(f"Service result: {result}")
        return ServiceResponse( success=True, message="Service installed successfully." )
    except Exception as e:
        logger.error(f"Error installing service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/uninstall", response_model=ServiceResponse)
async def uninstall_service():
    try:
        result = service_manager.uninstall_service()
        logger.info(f"Service result: {result}")
        return ServiceResponse( success=True, message="Service uninstalled successfully." )
    except Exception as e:
        logger.error(f"Error uninstalling service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.get("/status", response_model=ServiceResponse)
async def get_status():
    try:
        status = service_manager.get_service_status()
        logger.info(f"Service status: {status}")
        return ServiceResponse( success=True, message=f"Service status retrieved successfully.", status=ServiceStatus( status=status["installed"], installed=status["status"]) )
    except Exception as e:
        logger.error(f"Error status service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/start", response_model=ServiceResponse)
async def start_service():
    try:
        result = service_manager.start_service()
        logger.info(f"Service result: {result}")
        return ServiceResponse( success=True, message="Service started successfully." )
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/stop", response_model=ServiceResponse)
async def stop_service():
    try:
        result = service_manager.stop_service()
        return ServiceResponse( success=True, message="Service stopped successfully." )
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        raise HTTPException(status_code=500, detail=str(e))