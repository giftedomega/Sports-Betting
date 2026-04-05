"""Configuration management for the football betting analysis system."""

import os
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel, Field


def get_config_base_dir() -> Path:
    """Get the base directory for config files."""
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        bundled_dir = Path(sys._MEIPASS)
        user_config = exe_dir / "config" / "config.yaml"
        if user_config.exists():
            return exe_dir
        return bundled_dir
    else:
        return Path(__file__).parent.parent.parent


class LLMConfig(BaseModel):
    """LLM configuration."""
    model: str = "gemma2:9b"
    ollama_host: str = "http://localhost:11434"
    max_concurrent: int = 2
    temperature: float = 0.3
    seed: int = 42
    timeout: int = 300


class DatabaseConfig(BaseModel):
    """Database configuration."""
    path: str = "data/database.db"


class SportMonksConfig(BaseModel):
    """SportMonks API configuration."""
    api_key: str = ""
    primary: bool = True


class ScrapingConfig(BaseModel):
    """Scraping configuration."""
    sources: List[str] = Field(default_factory=lambda: ["fbref", "rss_news"])
    rate_limits: Dict[str, int] = Field(default_factory=lambda: {"fbref": 3, "rss": 1})
    cache_dir: str = "~/.soccerdata"
    season: str = "2425"


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""
    fixtures_interval: int = 3600
    stats_interval: int = 1800
    news_interval: int = 900
    lineups_interval: int = 600


class NewsSourceConfig(BaseModel):
    """News source configuration."""
    name: str
    url: str


class NewsConfig(BaseModel):
    """News configuration."""
    sources: List[NewsSourceConfig] = Field(default_factory=list)
    update_interval: int = 900
    cache_ttl: int = 600


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    host: str = "0.0.0.0"
    port: int = 8000


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "data/logs/app.log"


class AppConfig(BaseModel):
    """Main application configuration."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    sportmonks: SportMonksConfig = Field(default_factory=SportMonksConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: str | None = None):
        """Initialize configuration manager."""
        if config_path:
            self.config_path = Path(config_path)
        else:
            base_dir = get_config_base_dir()
            self.config_path = base_dir / "config" / "config.yaml"
        self._config: AppConfig | None = None

    def load_config(self) -> AppConfig:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            config_data = yaml.safe_load(f)

        self._config = AppConfig(**config_data)
        return self._config

    @property
    def config(self) -> AppConfig:
        """Get configuration, loading if necessary."""
        if self._config is None:
            self.load_config()
        return self._config

    def ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            "data/logs",
            "data",
            Path(self.config.database.path).parent,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config_manager: ConfigManager | None = None


def get_config() -> AppConfig:
    """Get global configuration instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.ensure_directories()
    return _config_manager.config


def reload_config() -> AppConfig:
    """Reload configuration from file."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    _config_manager._config = None
    return _config_manager.load_config()
