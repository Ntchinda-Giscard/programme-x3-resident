import logging
import sys
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .model import ServiceResponse
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



@service_router.post("/service/install", response_model=ServiceResponse)
async def install_service():
    try:
        result = service_manager.install_service()
        return ServiceResponse( success=True, message="Service installed successfully." )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/service/uninstall", response_model=ServiceResponse)
async def uninstall_service():
    try:
        result = service_manager.uninstall_service()
        return ServiceResponse( success=True, message="Service uninstalled successfully." )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@service_router.get("/service/status", response_model=ServiceResponse)
async def get_status():
    try:
        status = service_manager.get_service_status()
        logger.info(f"Service status: {status}")
        return ServiceResponse( success=True, message=f"Service status: {status['message']}.", status=status["installed"] )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/service/start", response_model=ServiceResponse)
async def start_service():
    try:
        result = service_manager.start_service()
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/service/stop", response_model=ServiceResponse)
async def stop_service():
    try:
        result = service_manager.stop_service()
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))