from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv

# Import routes
from home.routes import urls_router, health_router, projects_router, servers_router, gpu_router, gpu_servers_router, users_router
from home.routes.azure_users import router as azure_users_router

# Import services
from home.services import health_checker, db_cleanup_service
from home.services.gpu_monitor import gpu_monitor

# Import config
from home.config import init_database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting URL Monitoring System...")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Start health checker
    health_checker.start()
    
    # Start GPU monitor
    gpu_monitor.start()
    
    # Start database cleanup service
    db_cleanup_service.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down URL Monitoring System...")
    health_checker.stop()
    gpu_monitor.stop()
    db_cleanup_service.stop()

# Create FastAPI app
app = FastAPI(
    title="URL Monitoring System",
    description="Real-time URL health monitoring with WebSocket support",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(urls_router)
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(servers_router)
app.include_router(gpu_router)
app.include_router(gpu_servers_router)
app.include_router(users_router)
app.include_router(azure_users_router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    health_checker.add_websocket_connection(websocket)
    gpu_monitor.add_websocket(websocket)
    logger.info("WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "pong",
                "message": "Connection alive"
            })
    except WebSocketDisconnect:
        health_checker.remove_websocket_connection(websocket)
        gpu_monitor.remove_websocket(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        health_checker.remove_websocket_connection(websocket)
        gpu_monitor.remove_websocket(websocket)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "URL Monitoring System API",
        "version": "1.0.0",
        "status": "running"
    }

# Health check endpoint
@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "pong"}

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8080))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )