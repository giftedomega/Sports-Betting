"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from src.utils.config import get_config
from src.utils.logger import init_logging, get_logger
from src.database.models import create_tables
from src.api.routes import fixtures, teams, players, predictions, news, status, formations, h2h

# Initialize logging
init_logging()
logger = get_logger(__name__)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")


# Global connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Football Betting Analysis application...")

    # Initialize database
    config = get_config()
    db_path = Path(config.database.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    create_tables(str(db_path))
    logger.info(f"Database initialized at {db_path}")

    # Store manager in app state
    app.state.ws_manager = manager

    # Start background scheduler
    from src.queue.scheduler import BackgroundScheduler
    scheduler = BackgroundScheduler(broadcast_fn=manager.broadcast)
    app.state.scheduler = scheduler
    asyncio.create_task(scheduler.start())
    logger.info("Background scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="Football Betting Analysis",
    description="AI-powered Premier League betting analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Templates
templates_path = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Include routers
app.include_router(fixtures.router, prefix="/api/fixtures", tags=["fixtures"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(formations.router, prefix="/api/formations", tags=["formations"])
app.include_router(h2h.router, prefix="/api/h2h", tags=["head-to-head"])
app.include_router(status.router, prefix="/api", tags=["status"])


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/fixtures", response_class=HTMLResponse)
async def fixtures_page(request: Request):
    """Render fixtures page."""
    return templates.TemplateResponse("fixtures.html", {"request": request})


@app.get("/predictions", response_class=HTMLResponse)
async def predictions_page(request: Request):
    """Render predictions page."""
    return templates.TemplateResponse("predictions.html", {"request": request})


@app.get("/teams", response_class=HTMLResponse)
async def teams_page(request: Request):
    """Render teams page."""
    return templates.TemplateResponse("teams.html", {"request": request})


@app.get("/match/{fixture_id}", response_class=HTMLResponse)
async def match_page(request: Request, fixture_id: int):
    """Render match analysis page."""
    return templates.TemplateResponse("match.html", {
        "request": request,
        "fixture_id": fixture_id
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "football-betting-analysis"}
