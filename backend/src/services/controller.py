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
    """Install the Windows service"""
    try:
        logger.info("=== CONTROLLER: Starting install request ===")
        result = service_manager.install_service()
        logger.info(f"=== CONTROLLER: Service manager returned: {result} ===")
        
        # Check if result is None (this should never happen now)
        if result is None:
            logger.error("=== CONTROLLER: Received None from install_service! ===")
            raise HTTPException(
                status_code=500, 
                detail="Service installation returned no result"
            )
        
        logger.info(f"=== CONTROLLER: Returning success response ===")
        return ServiceResponse(
            # success=True, 
            message=result  # Return the actual message from service_manager
        )
    except Exception as e:
        logger.error(f"=== CONTROLLER: Error installing service: {e} ===")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/uninstall", response_model=ServiceResponse)
async def uninstall_service():
    """Uninstall the Windows service"""
    try:
        logger.info("=== CONTROLLER: Starting uninstall request ===")
        result = service_manager.uninstall_service()
        logger.info(f"=== CONTROLLER: Service manager returned: {result} ===")
        
        if result is None:
            logger.error("=== CONTROLLER: Received None from uninstall_service! ===")
            raise HTTPException(
                status_code=500, 
                detail="Service uninstallation returned no result"
            )
        
        return ServiceResponse(
            # success=True, 
            message=result)
    except Exception as e:
        logger.error(f"=== CONTROLLER: Error uninstalling service: {e} ===")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.get("/status", response_model=ServiceResponse)
async def get_status():
    """Get the current service status"""
    try:
        logger.info("=== CONTROLLER: Getting service status ===")
        status = service_manager.get_service_status()
        logger.info(f"=== CONTROLLER: Service status: {status} ===")
        
        return ServiceResponse(
            # success=True, 
            message="Service status retrieved successfully.", 
            # status=ServiceStatus(
            #     status=status["status"],  # The status string (running, stopped, etc)
            #     installed=status["installed"]  # Boolean indicating if installed
            # )
        )
    except Exception as e:
        logger.error(f"=== CONTROLLER: Error getting status: {e} ===")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/start", response_model=ServiceResponse)
async def start_service():
    """Start the Windows service"""
    try:
        logger.info("=== CONTROLLER: Starting service start request ===")
        result = service_manager.start_service()
        logger.info(f"=== CONTROLLER: Service manager returned: {result} ===")
        
        if result is None:
            logger.error("=== CONTROLLER: Received None from start_service! ===")
            raise HTTPException(
                status_code=500, 
                detail="Service start returned no result"
            )
        
        return ServiceResponse(
            # success=True, 
            message=result)
    except Exception as e:
        logger.error(f"=== CONTROLLER: Error starting service: {e} ===")
        raise HTTPException(status_code=500, detail=str(e))


@service_router.post("/stop", response_model=ServiceResponse)
async def stop_service():
    """Stop the Windows service"""
    try:
        logger.info("=== CONTROLLER: Starting service stop request ===")
        result = service_manager.stop_service()
        logger.info(f"=== CONTROLLER: Service manager returned: {result} ===")
        
        if result is None:
            logger.error("=== CONTROLLER: Received None from stop_service! ===")
            raise HTTPException(
                status_code=500, 
                detail="Service stop returned no result"
            )
        
        return ServiceResponse(
            # success=True, 
            message=result)
    except Exception as e:
        logger.error(f"=== CONTROLLER: Error stopping service: {e} ===")
        raise HTTPException(status_code=500, detail=str(e))