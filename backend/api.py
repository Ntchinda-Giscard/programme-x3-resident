# python-backend/api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.service.controller import folder_router

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

@app.get("/")
def read_root():
    return {"API_CHECK": "UP and Running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)