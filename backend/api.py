# python-backend/api.py
import logging
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.configs.controller import folder_router
from src.services.controller import service_router
from src.odbc.controller import odbc_router
from src.email_config.controller import email_router
from src.database.session import engine, Base



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

logger.info(f'Creating app.db...')
Base.metadata.create_all(bind=engine)
logger.info(f'Created app.db')

app = FastAPI(
    title="Service Manager API",
    description="API to manage local services (install, uninstall, start, stop, status)",
    version="1.0.0"
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(folder_router)
app.include_router(service_router)
app.include_router(odbc_router)
app.include_router(email_router)

@app.get("/")
def read_root():
    return {"API_CHECK": "UP and Running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)