"""SVG football pitch visualization."""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PlayerPosition:
    """Player position on pitch."""
    name: str
    number: int
    x: float  # 0-100 percentage
    y: float  # 0-100 percentage
    position: str  # GK, DF, MF, FW


class PitchSVG:
    """Generate SVG football pitch visualizations."""

    # Standard formations with position coordinates (x, y as percentages)
    FORMATIONS = {
        "4-4-2": {
            "GK": [(50, 95)],
            "DF": [(15, 75), (35, 75), (65, 75), (85, 75)],
            "MF": [(15, 50), (35, 50), (65, 50), (85, 50)],
            "FW": [(35, 25), (65, 25)],
        },
        "4-3-3": {
            "GK": [(50, 95)],
            "DF": [(15, 75), (35, 75), (65, 75), (85, 75)],
            "MF": [(30, 50), (50, 55), (70, 50)],
            "FW": [(20, 25), (50, 20), (80, 25)],
        },
        "3-5-2": {
            "GK": [(50, 95)],
            "DF": [(25, 75), (50, 75), (75, 75)],
            "MF": [(10, 50), (30, 45), (50, 50), (70, 45), (90, 50)],
            "FW": [(35, 25), (65, 25)],
        },
        "4-2-3-1": {
            "GK": [(50, 95)],
            "DF": [(15, 75), (35, 75), (65, 75), (85, 75)],
            "MF": [(35, 55), (65, 55), (20, 40), (50, 35), (80, 40)],
            "FW": [(50, 20)],
        },
        "3-4-3": {
            "GK": [(50, 95)],
            "DF": [(25, 75), (50, 75), (75, 75)],
            "MF": [(15, 50), (38, 50), (62, 50), (85, 50)],
            "FW": [(20, 25), (50, 20), (80, 25)],
        },
        "5-3-2": {
            "GK": [(50, 95)],
            "DF": [(10, 75), (30, 75), (50, 75), (70, 75), (90, 75)],
            "MF": [(30, 50), (50, 50), (70, 50)],
            "FW": [(35, 25), (65, 25)],
        },
        "4-1-4-1": {
            "GK": [(50, 95)],
            "DF": [(15, 75), (35, 75), (65, 75), (85, 75)],
            "MF": [(50, 60), (15, 45), (38, 40), (62, 40), (85, 45)],
            "FW": [(50, 20)],
        },
    }

    def __init__(self, width: int = 400, height: int = 600):
        """Initialize pitch generator.

        Args:
            width: SVG width in pixels
            height: SVG height in pixels
        """
        self.width = width
        self.height = height

    def generate_pitch(
        self,
        home_formation: str = "4-3-3",
        away_formation: str = "4-3-3",
        home_players: Optional[List[Dict]] = None,
        away_players: Optional[List[Dict]] = None,
        home_team: str = "Home",
        away_team: str = "Away",
        home_color: str = "#3498db",
        away_color: str = "#e74c3c"
    ) -> str:
        """Generate SVG pitch with both teams' formations.

        Args:
            home_formation: Formation string (e.g., "4-3-3")
            away_formation: Formation string
            home_players: List of player dicts with name, number, position
            away_players: List of player dicts
            home_team: Home team name
            away_team: Away team name
            home_color: Home team color
            away_color: Away team color

        Returns:
            SVG string
        """
        svg_parts = [
            f'<svg viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg" class="pitch-svg">',
            self._draw_pitch_markings(),
            self._draw_team_label(away_team, "away"),
            self._draw_team_label(home_team, "home"),
        ]

        # Draw away team (top half, attacking down)
        away_positions = self._get_formation_positions(away_formation, is_home=False)
        svg_parts.append(self._draw_players(away_positions, away_players, away_color, "away"))

        # Draw home team (bottom half, attacking up)
        home_positions = self._get_formation_positions(home_formation, is_home=True)
        svg_parts.append(self._draw_players(home_positions, home_players, home_color, "home"))

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def _draw_pitch_markings(self) -> str:
        """Draw pitch lines and markings."""
        w, h = self.width, self.height

        return f'''
        <defs>
            <pattern id="grass" patternUnits="userSpaceOnUse" width="40" height="40">
                <rect width="40" height="40" fill="#2d8a3e"/>
                <rect width="40" height="20" fill="#2a8039"/>
            </pattern>
        </defs>

        <!-- Pitch background -->
        <rect width="{w}" height="{h}" fill="url(#grass)"/>

        <!-- Pitch outline -->
        <rect x="10" y="10" width="{w-20}" height="{h-20}" fill="none" stroke="white" stroke-width="2"/>

        <!-- Center line -->
        <line x1="10" y1="{h/2}" x2="{w-10}" y2="{h/2}" stroke="white" stroke-width="2"/>

        <!-- Center circle -->
        <circle cx="{w/2}" cy="{h/2}" r="50" fill="none" stroke="white" stroke-width="2"/>
        <circle cx="{w/2}" cy="{h/2}" r="3" fill="white"/>

        <!-- Top penalty area (away) -->
        <rect x="{w/2-80}" y="10" width="160" height="80" fill="none" stroke="white" stroke-width="2"/>
        <rect x="{w/2-40}" y="10" width="80" height="30" fill="none" stroke="white" stroke-width="2"/>
        <circle cx="{w/2}" cy="70" r="3" fill="white"/>
        <!-- Penalty arc -->
        <path d="M {w/2-40} 90 Q {w/2} 110 {w/2+40} 90" fill="none" stroke="white" stroke-width="2"/>

        <!-- Bottom penalty area (home) -->
        <rect x="{w/2-80}" y="{h-90}" width="160" height="80" fill="none" stroke="white" stroke-width="2"/>
        <rect x="{w/2-40}" y="{h-40}" width="80" height="30" fill="none" stroke="white" stroke-width="2"/>
        <circle cx="{w/2}" cy="{h-70}" r="3" fill="white"/>
        <!-- Penalty arc -->
        <path d="M {w/2-40} {h-90} Q {w/2} {h-110} {w/2+40} {h-90}" fill="none" stroke="white" stroke-width="2"/>

        <!-- Corner arcs -->
        <path d="M 10 20 Q 20 10 30 10" fill="none" stroke="white" stroke-width="2"/>
        <path d="M {w-30} 10 Q {w-20} 10 {w-10} 20" fill="none" stroke="white" stroke-width="2"/>
        <path d="M 10 {h-20} Q 20 {h-10} 30 {h-10}" fill="none" stroke="white" stroke-width="2"/>
        <path d="M {w-30} {h-10} Q {w-20} {h-10} {w-10} {h-20}" fill="none" stroke="white" stroke-width="2"/>
        '''

    def _get_formation_positions(self, formation: str, is_home: bool) -> List[tuple]:
        """Get player positions for formation.

        Args:
            formation: Formation string
            is_home: Whether this is the home team

        Returns:
            List of (x, y, position_type) tuples
        """
        positions = self.FORMATIONS.get(formation, self.FORMATIONS["4-3-3"])
        all_positions = []

        for pos_type, coords in positions.items():
            for x, y in coords:
                if not is_home:
                    # Mirror for away team (flip vertically)
                    y = 100 - y
                all_positions.append((x, y, pos_type))

        return all_positions

    def _draw_players(
        self,
        positions: List[tuple],
        players: Optional[List[Dict]],
        color: str,
        team_class: str
    ) -> str:
        """Draw player markers.

        Args:
            positions: List of (x, y, position) tuples
            players: Player data list
            color: Team color
            team_class: CSS class for team

        Returns:
            SVG group string
        """
        parts = []

        for i, (x_pct, y_pct, pos_type) in enumerate(positions):
            x = self.width * x_pct / 100
            y = self.height * y_pct / 100

            # Get player info if available
            player = players[i] if players and i < len(players) else None
            number = player.get("number", i + 1) if player else i + 1
            name = ""
            if player:
                full_name = player.get("name", "")
                # Get last name, truncated
                name_parts = full_name.split()
                if name_parts:
                    name = name_parts[-1][:8]

            parts.append(f'''
            <g class="player {team_class}" transform="translate({x}, {y})">
                <circle r="15" fill="{color}" stroke="white" stroke-width="2"/>
                <text y="5" text-anchor="middle" fill="white" font-size="11" font-weight="bold">{number}</text>
                <text y="28" text-anchor="middle" fill="white" font-size="8">{name}</text>
            </g>
            ''')

        return "\n".join(parts)

    def _draw_team_label(self, team_name: str, side: str) -> str:
        """Draw team name label.

        Args:
            team_name: Team name
            side: "home" or "away"

        Returns:
            SVG text element
        """
        y = self.height - 5 if side == "home" else 8
        return f'<text x="{self.width/2}" y="{y}" text-anchor="middle" fill="white" font-size="12" font-weight="bold" opacity="0.8">{team_name}</text>'

    def generate_single_team(
        self,
        formation: str = "4-3-3",
        players: Optional[List[Dict]] = None,
        team_name: str = "Team",
        color: str = "#3498db"
    ) -> str:
        """Generate SVG for a single team's formation.

        Args:
            formation: Formation string
            players: Player data list
            team_name: Team name
            color: Team color

        Returns:
            SVG string
        """
        svg_parts = [
            f'<svg viewBox="0 0 {self.width} {self.height//2 + 50}" xmlns="http://www.w3.org/2000/svg" class="pitch-svg-half">',
        ]

        # Half pitch background
        svg_parts.append(f'''
        <defs>
            <pattern id="grass-half" patternUnits="userSpaceOnUse" width="40" height="40">
                <rect width="40" height="40" fill="#2d8a3e"/>
                <rect width="40" height="20" fill="#2a8039"/>
            </pattern>
        </defs>
        <rect width="{self.width}" height="{self.height//2 + 50}" fill="url(#grass-half)"/>
        <rect x="10" y="10" width="{self.width-20}" height="{self.height//2 + 30}" fill="none" stroke="white" stroke-width="2"/>
        ''')

        # Draw players
        positions = self._get_formation_positions(formation, is_home=True)
        # Adjust positions for half pitch view
        adjusted_positions = [(x, (y - 50) * 0.6 + 30, pos) for x, y, pos in positions]
        svg_parts.append(self._draw_players(adjusted_positions, players, color, "team"))

        # Team label
        svg_parts.append(f'<text x="{self.width/2}" y="{self.height//2 + 45}" text-anchor="middle" fill="white" font-size="14" font-weight="bold">{team_name} ({formation})</text>')

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)


def get_pitch_svg(
    home_team: str,
    away_team: str,
    home_formation: str = "4-3-3",
    away_formation: str = "4-3-3",
    home_players: Optional[List[Dict]] = None,
    away_players: Optional[List[Dict]] = None
) -> str:
    """Convenience function to generate pitch SVG.

    Args:
        home_team: Home team name
        away_team: Away team name
        home_formation: Home team formation
        away_formation: Away team formation
        home_players: Home team players
        away_players: Away team players

    Returns:
        SVG string
    """
    pitch = PitchSVG()
    return pitch.generate_pitch(
        home_formation=home_formation,
        away_formation=away_formation,
        home_players=home_players,
        away_players=away_players,
        home_team=home_team,
        away_team=away_team
    )
