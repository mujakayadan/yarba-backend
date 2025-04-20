"""Utilities for handling and repairing JSON data from LLMs."""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union

from beanie import PydanticObjectId
from bson import ObjectId, json_util
from pydantic import BaseModel, ValidationError

# Configure logging
logger = logging.getLogger(__name__)


class CustomEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles MongoDB types, Pydantic models, and datetime objects."""

    def default(self, obj):
        if isinstance(obj, (PydanticObjectId, ObjectId)):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return super().default(obj)


def convert_to_serializable(data: Any) -> Any:
    """
    Convert data to a JSON serializable format.

    Args:
        data: The data to convert (any type)

    Returns:
        The data in a serializable format
    """
    try:
        if data is None:
            return None
        elif isinstance(data, (PydanticObjectId, ObjectId)):
            # Convert ObjectId to string
            return str(data)
        elif isinstance(data, datetime):
            # Convert datetime to ISO format string
            return data.isoformat()
        elif hasattr(data, "model_dump"):
            # For Pydantic models, use model_dump()
            return data.model_dump()
        elif isinstance(data, (list, dict)):
            # Process list or dict recursively
            if isinstance(data, list):
                return [convert_to_serializable(item) for item in data]
            else:  # dict
                return {
                    key: convert_to_serializable(value) for key, value in data.items()
                }
        elif isinstance(data, (str, int, float, bool)):
            # Primitive types can be returned as is
            return data
        else:
            # For custom types, try string representation
            return str(data)
    except Exception as e:
        # Log error and return string representation
        logger.error(
            f"Error converting {type(data).__name__} to serializable format: {e}"
        )
        return str(data)


def repair_json(json_str: str) -> str:
    """
    Repair invalid JSON strings often returned by LLMs.

    Args:
        json_str: The potentially invalid JSON string to repair

    Returns:
        A valid JSON string
    """
    try:
        # Try the json_repair library first (most comprehensive solution)
        try:
            from json_repair import repair_json as external_repair_json

            return external_repair_json(json_str)
        except ImportError:
            logger.warning("json_repair package not installed. Using fallback methods.")

        # If json_repair is not available, try our simple repair methods
        return manual_json_repair(json_str)

    except Exception as e:
        logger.error(f"Error repairing JSON: {e}")
        # Return the original string if all repair methods fail
        return json_str


def manual_json_repair(json_str: str) -> str:
    """
    Manual JSON repair function when json_repair package is not available.

    Args:
        json_str: The potentially invalid JSON string to repair

    Returns:
        A repaired JSON string
    """
    # Remove markdown code blocks if present
    if "```json" in json_str or "```" in json_str:
        json_str = extract_from_markdown(json_str)

    # Try to clean up some common JSON issues
    json_str = json_str.strip()

    # Replace single quotes with double quotes (but not inside already double-quoted strings)
    # This is a simplified approach and may not work for all cases
    json_str = re.sub(r"(?<!\")\'([^\']+)\'(?!\")", r'"\1"', json_str)

    # Try to fix trailing commas in objects and arrays
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*\]", "]", json_str)

    # Try to add missing quotes to keys
    json_str = re.sub(r"([{,]\s*)([a-zA-Z0-9_]+)(\s*:)", r'\1"\2"\3', json_str)

    # Try to fix unquoted or improperly capitalized boolean/null values
    json_str = re.sub(r":\s*True", r": true", json_str)
    json_str = re.sub(r":\s*False", r": false", json_str)
    json_str = re.sub(r":\s*None", r": null", json_str)

    return json_str


def extract_from_markdown(text: str) -> str:
    """
    Extract JSON from markdown code blocks.

    Args:
        text: Text potentially containing markdown code blocks

    Returns:
        Extracted JSON string
    """
    # Try to extract JSON from code blocks
    if "```json" in text:
        parts = text.split("```json")
        if len(parts) > 1:
            json_part = parts[1].split("```")[0].strip()
            return json_part
    elif "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            # Get the content between the first pair of ```
            json_part = parts[1].strip()
            return json_part

    # If we can't find code blocks, return the original text
    return text


def parse_json_with_repair(
    json_str: str, schema_model: Optional[Type[BaseModel]] = None
) -> Union[Dict[str, Any], BaseModel]:
    """
    Parse a JSON string with repair if needed.

    Args:
        json_str: The JSON string to parse
        schema_model: Optional Pydantic model to validate against

    Returns:
        Parsed JSON as dict or Pydantic model instance

    Raises:
        json.JSONDecodeError: If JSON cannot be parsed after repair attempts
        ValidationError: If schema_model is provided and validation fails
    """
    try:
        # First try to parse as is
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        # If that fails, try to repair
        repaired_json = repair_json(json_str)
        parsed = json.loads(repaired_json)

    # If a schema model was provided, validate against it
    if schema_model:
        return schema_model.model_validate(parsed)

    return parsed


def dumps(obj: Any, **kwargs) -> str:
    """
    Serialize obj to a JSON formatted string using CustomEncoder.

    This is a convenience wrapper around json.dumps with CustomEncoder.

    Args:
        obj: The Python object to serialize to JSON
        **kwargs: Additional arguments to pass to json.dumps

    Returns:
        JSON formatted string
    """
    kwargs.setdefault("cls", CustomEncoder)
    return json.dumps(obj, **kwargs)


def loads(json_str: str, **kwargs) -> Any:
    """
    Deserialize json_str to Python objects.

    This is a convenience wrapper around json.loads.

    Args:
        json_str: The JSON string to deserialize
        **kwargs: Additional arguments to pass to json.loads

    Returns:
        Python object representation of the JSON
    """
    return json.loads(json_str, **kwargs)
