"""Weather scraper using Open-Meteo API (free, no API key)."""

from datetime import datetime
from typing import List, Dict, Optional

import httpx

from src.scrapers.base_scraper import BaseScraper
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Premier League stadium coordinates (lat, lon)
STADIUM_COORDS = {
    "Arsenal": (51.5549, -0.1084),            # Emirates Stadium
    "Aston Villa": (52.5092, -1.8847),         # Villa Park
    "Bournemouth": (50.7352, -1.8384),         # Vitality Stadium
    "Brentford": (51.4907, -0.2887),           # Gtech Community Stadium
    "Brighton": (50.8616, -0.0834),            # Amex Stadium
    "Chelsea": (51.4817, -0.1910),             # Stamford Bridge
    "Crystal Palace": (51.3983, -0.0855),      # Selhurst Park
    "Everton": (53.4388, -2.9663),             # Goodison Park
    "Fulham": (51.4750, -0.2217),              # Craven Cottage
    "Ipswich": (52.0545, 1.1446),              # Portman Road
    "Ipswich Town": (52.0545, 1.1446),         # Portman Road
    "Leicester": (52.6204, -1.1422),           # King Power Stadium
    "Leicester City": (52.6204, -1.1422),      # King Power Stadium
    "Liverpool": (53.4308, -2.9608),           # Anfield
    "Manchester City": (53.4831, -2.2004),     # Etihad Stadium
    "Manchester United": (53.4631, -2.2913),   # Old Trafford
    "Manchester Utd": (53.4631, -2.2913),      # Old Trafford (variant)
    "Man United": (53.4631, -2.2913),          # Old Trafford (variant)
    "Newcastle": (54.9756, -1.6217),           # St James' Park
    "Newcastle United": (54.9756, -1.6217),    # St James' Park
    "Nottingham Forest": (52.9400, -1.1325),   # City Ground
    "Nott'ham Forest": (52.9400, -1.1325),     # City Ground (variant)
    "Southampton": (50.9058, -1.3910),         # St Mary's Stadium
    "Tottenham": (51.6042, -0.0662),           # Tottenham Hotspur Stadium
    "Tottenham Hotspur": (51.6042, -0.0662),   # Tottenham Hotspur Stadium
    "Spurs": (51.6042, -0.0662),               # Tottenham Hotspur Stadium
    "West Ham": (51.5387, 0.0166),             # London Stadium
    "West Ham United": (51.5387, 0.0166),      # London Stadium
    "Wolves": (52.5901, -2.1306),              # Molineux Stadium
    "Wolverhampton": (52.5901, -2.1306),       # Molineux Stadium
    # Promoted/other teams that may appear
    "Burnley": (53.7890, -2.2302),             # Turf Moor
    "Sunderland": (54.9146, -1.3882),          # Stadium of Light
    "Leeds": (53.7779, -1.5721),               # Elland Road
    "Leeds United": (53.7779, -1.5721),        # Elland Road
    "Sheffield United": (53.3706, -1.4710),    # Bramall Lane
    "Luton": (51.8843, -0.4316),              # Kenilworth Road
    "Luton Town": (51.8843, -0.4316),         # Kenilworth Road
    "Middlesbrough": (54.5783, -1.2170),       # Riverside Stadium
}


class WeatherScraper(BaseScraper):
    """Scraper for match-day weather from Open-Meteo (free)."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        config = get_config()
        rate_limit = config.scraping.rate_limits.get("weather", 1)
        super().__init__(rate_limit_seconds=rate_limit)
        self.client = httpx.AsyncClient(timeout=15.0)

    async def fetch_fixtures(self) -> List[Dict]:
        return []

    async def fetch_team_stats(self) -> List[Dict]:
        return []

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        return []

    async def fetch_match_weather(self, home_team: str, match_date: datetime) -> Optional[Dict]:
        """Fetch weather forecast for a match.

        Args:
            home_team: Home team name (determines venue)
            match_date: Match kickoff time

        Returns:
            Weather dict or None
        """
        coords = STADIUM_COORDS.get(home_team)
        if not coords:
            logger.warning(f"[WEATHER] No stadium coords for {home_team}")
            return None

        cache_key = f"weather_{home_team}_{match_date.strftime('%Y%m%d')}"
        cached = self._get_cached(cache_key, 21600)  # 6 hour cache
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            lat, lon = coords
            date_str = match_date.strftime("%Y-%m-%d")

            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,weather_code",
                "start_date": date_str,
                "end_date": date_str,
                "timezone": "Europe/London",
            }

            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            precip = hourly.get("precipitation_probability", [])
            wind = hourly.get("wind_speed_10m", [])
            codes = hourly.get("weather_code", [])

            # Find the hour closest to kickoff
            kickoff_hour = match_date.hour
            idx = min(kickoff_hour, len(times) - 1) if times else 0

            result = {
                "home_team": home_team,
                "match_date": date_str,
                "temperature": temps[idx] if idx < len(temps) else None,
                "precipitation_prob": precip[idx] if idx < len(precip) else None,
                "wind_speed": wind[idx] if idx < len(wind) else None,
                "weather_code": codes[idx] if idx < len(codes) else None,
                "condition": self._weather_code_to_text(codes[idx] if idx < len(codes) else 0),
            }

            self._set_cache(cache_key, result)
            logger.info(f"[WEATHER] {home_team}: {result['temperature']}C, "
                       f"{result['precipitation_prob']}% rain, {result['wind_speed']}km/h wind")
            return result

        except Exception as e:
            logger.error(f"[WEATHER] Failed for {home_team}: {e}")
            return None

    async def fetch_fixtures_weather(self, fixtures: List[Dict]) -> List[Dict]:
        """Fetch weather for a list of fixtures.

        Args:
            fixtures: List of fixture dicts with home_team and match_date

        Returns:
            List of weather dicts
        """
        results = []
        for fixture in fixtures:
            home_team = fixture.get("home_team", "")
            match_date = fixture.get("match_date")
            if match_date and isinstance(match_date, str):
                match_date = datetime.fromisoformat(match_date)
            if home_team and match_date:
                weather = await self.fetch_match_weather(home_team, match_date)
                if weather:
                    results.append(weather)
        return results

    def _weather_code_to_text(self, code: int) -> str:
        """Convert WMO weather code to readable text."""
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
        }
        return weather_codes.get(code, "Unknown")

    async def close(self):
        await self.client.aclose()
