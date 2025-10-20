from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .model import ServiceResponse
from .service import service_manager

service_router = APIRouter(
    prefix="/service",
    tags=["service management"]
)



@app.post("/service/install", response_model=ServiceResponse)
async def install_service():
    try:
        result = service_manager.install_service()
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/service/uninstall", response_model=ServiceResponse)
async def uninstall_service():
    try:
        result = service_manager.uninstall_service()
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/service/status", response_model=ServiceResponse)
async def get_status():
    try:
        status = service_manager.get_service_status()
        return {"success": True, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/service/start", response_model=ServiceResponse)
async def start_service():
    try:
        result = service_manager.start_service()
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/service/stop", response_model=ServiceResponse)
async def stop_service():
    try:
        result = service_manager.stop_service()
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))