"""Available portfolio website themes."""

from typing import Final

PORTFOLIO_WEBSITE_THEMES: Final[list[dict[str, str]]] = [
    {
        "id": "modern",
        "name": "Modern",
        "description": "Clean, professional layout with timelines and project cards.",
    },
    {
        "id": "threejs",
        "name": "Developer",
        "description": "Dark developer aesthetic with animated accents and code-inspired styling.",
    },
    {
        "id": "bento",
        "name": "Bento",
        "description": "Playful bento-grid layout with bold cards and soft gradients.",
    },
    {
        "id": "neon",
        "name": "Neon",
        "description": "Cyberpunk-inspired theme with glowing panels and grid backgrounds.",
    },
]

PORTFOLIO_WEBSITE_THEME_IDS: Final[frozenset[str]] = frozenset(
    theme["id"] for theme in PORTFOLIO_WEBSITE_THEMES
)
