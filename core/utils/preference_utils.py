"""Utility for robust, DRY user preference handling for prompt injection."""

import logging
from typing import Any, Dict, Optional

from config.settings import settings
from core.models.profile import Profile

logger = logging.getLogger("core.utils.preference_utils")

# Define the canonical structure expected by the prompt
PREFERENCE_STRUCTURE = {
    "project": {
        "max_projects": int,
        "bullet_points_per_project": int,
    },
    "work_experience": {
        "max_jobs": int,
        "bullet_points_per_job": int,
    },
    "skills": {
        "max_categories": int,
        "min_per_category": int,
        "max_per_category": int,
    },
    "career_summary": {
        "min_words": int,
        "max_words": int,
    },
    "education": {
        "max_entries": int,
        "max_courses": int,
    },
    "cover_letter": {
        "paragraphs": int,
        "target_age": int,
    },
    "awards": {
        "max_awards": int,
    },
    "publications": {
        "max_publications": int,
    },
}


def get_prompt_preferences(profile: Optional[Profile]) -> Dict[str, Any]:
    """
    Get preferences for prompt injection, falling back to settings when needed.
    Returns a dict matching the structure expected by the prompt templates.

    The function checks multiple sources in this order:
    1. Profile's prompt_preferences structure (if available)
    2. Settings fallback values

    Args:
        profile: Optional Profile object containing user preferences

    Returns:
        Dict in the canonical structure expected by the prompt templates
    """
    # Start with empty result structure
    result = {section: {} for section in PREFERENCE_STRUCTURE}

    # Get settings fallback values first
    settings_fallback = settings.preferences.get_prompt_variables()

    # Start by copying the settings fallback
    for section, section_values in settings_fallback.items():
        if section in result:
            result[section].update(section_values)

    # Early return if no profile
    if not profile:
        logger.debug("No profile provided, using settings fallback values")
        return result

    # Check for values in prompt_preferences structure
    if hasattr(profile, "prompt_preferences") and profile.prompt_preferences:
        prompt_prefs = profile.prompt_preferences
        for section_name in PREFERENCE_STRUCTURE:
            if hasattr(prompt_prefs, section_name):
                section_prefs = getattr(prompt_prefs, section_name)
                if section_prefs:  # Only update if there are values
                    if section_name in result:
                        result[section_name].update(section_prefs)

    # Log the final structure for debugging
    logger.debug(f"Final preferences after merging: {result}")

    # Validate all required keys exist
    for section, section_schema in PREFERENCE_STRUCTURE.items():
        if section not in result:
            logger.warning(f"Missing preference section: {section}")
            result[section] = {}

        for key in section_schema:
            if key not in result[section]:
                logger.warning(
                    f"Missing preference key: {section}.{key} - will use fallback"
                )

                # Try to get fallback from settings
                if section in settings_fallback and key in settings_fallback[section]:
                    result[section][key] = settings_fallback[section][key]
                    logger.debug(
                        f"Used fallback for {section}.{key}: {result[section][key]}"
                    )

    return result


def print_preferences_structure(preferences: dict):
    import json

    print("\n==== PREFERENCES STRUCTURE ====")
    print(json.dumps(preferences, indent=2, default=str))
