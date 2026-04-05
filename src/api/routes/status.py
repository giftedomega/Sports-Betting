"""Status and system API routes."""

from datetime import datetime
from fastapi import APIRouter, HTTPException

from src.llm.client import OllamaClient
from src.scrapers.aggregator import DataAggregator
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/status")
async def get_status():
    """Get system status."""
    try:
        config = get_config()

        # Check Ollama
        ollama_client = OllamaClient()
        ollama_status = await ollama_client.check_status()

        return {
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "ollama": ollama_status,
            "config": {
                "model": config.llm.model,
                "database": config.database.path
            }
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/status/scraping")
async def get_scraping_status():
    """Get scraping status and last update times."""
    return {
        "status": "operational",
        "sources": {
            "fbref": {"status": "active", "rate_limit": "3s"},
            "news_rss": {"status": "active", "rate_limit": "1s"}
        }
    }


@router.post("/refresh")
async def refresh_data():
    """Manually refresh all data sources."""
    try:
        aggregator = DataAggregator()
        results = await aggregator.refresh_all_data()
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Data refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ollama/models")
async def get_ollama_models():
    """Get available Ollama models."""
    try:
        client = OllamaClient()
        status = await client.check_status()
        return {
            "models": status.get("available_models", []),
            "count": status.get("model_count", 0)
        }
    except Exception as e:
        logger.error(f"Failed to get Ollama models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/pull/{model_name}")
async def pull_ollama_model(model_name: str):
    """Pull/download an Ollama model."""
    try:
        client = OllamaClient()
        success = await client.pull_model(model_name)
        if success:
            return {"status": "success", "model": model_name}
        else:
            raise HTTPException(status_code=500, detail="Failed to pull model")
    except Exception as e:
        logger.error(f"Failed to pull model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
