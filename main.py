#!/usr/bin/env python3
"""
Premier League Football Betting Analysis Application

AI-powered betting analysis using Ollama/Gemma model.
Scrapes Premier League data and provides match predictions.
"""

import uvicorn
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import get_config
from src.utils.logger import init_logging, get_logger


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Premier League Football Betting Analysis"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (default: from config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (default: from config)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    # Initialize logging
    init_logging()
    logger = get_logger(__name__)

    # Load config
    config = get_config()

    # Use command line args or config defaults
    host = args.host or config.dashboard.host
    port = args.port or config.dashboard.port

    logger.info("=" * 60)
    logger.info("Premier League Football Betting Analysis")
    logger.info("=" * 60)
    logger.info(f"Starting server on http://{host}:{port}")
    logger.info(f"Ollama model: {config.llm.model}")
    logger.info(f"Database: {config.database.path}")
    logger.info("=" * 60)

    # Run the server
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="debug" if args.debug else "info"
    )


if __name__ == "__main__":
    main()
