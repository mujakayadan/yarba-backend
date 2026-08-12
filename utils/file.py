"""File handling utilities for YARBA."""

import pathlib

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


def ensure_directory_exists(directory_path: str | pathlib.Path) -> pathlib.Path:
    """Ensure that a directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory to ensure exists

    Returns:
        pathlib.Path: The path to the directory
    """
    path = pathlib.Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_path(filename: str, subdir: str | None = None) -> pathlib.Path:
    """Get a path in the temporary directory.

    Args:
        filename: Name of the file
        subdir: Optional subdirectory within the temp directory

    Returns:
        pathlib.Path: Path to the temporary file
    """
    temp_dir = settings.paths.temp_dir
    if subdir:
        temp_dir = temp_dir / subdir
    ensure_directory_exists(temp_dir)
    return temp_dir / filename


def safe_file_write(
    file_path: str | pathlib.Path,
    content: str | bytes,
    mode: str = "w",
    encoding: str | None = "utf-8",
) -> None:
    """Safely write content to a file, ensuring the directory exists.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        mode: File mode ('w' for text, 'wb' for binary)
        encoding: File encoding (None for binary mode)
    """
    path = pathlib.Path(file_path)
    ensure_directory_exists(path.parent)

    try:
        with open(path, mode=mode, encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Successfully wrote to file: {path}")
    except Exception as e:
        logger.error(f"Error writing to file {path}: {str(e)}")
        raise


def safe_file_read(
    file_path: str | pathlib.Path,
    mode: str = "r",
    encoding: str | None = "utf-8",
) -> str | bytes:
    """Safely read content from a file.

    Args:
        file_path: Path to the file to read
        mode: File mode ('r' for text, 'rb' for binary)
        encoding: File encoding (None for binary mode)

    Returns:
        Union[str, bytes]: The file contents
    """
    path = pathlib.Path(file_path)

    try:
        with open(path, mode=mode, encoding=encoding) as f:
            content = f.read()
        logger.debug(f"Successfully read from file: {path}")
        return content if isinstance(content, bytes) else str(content)
    except Exception as e:
        logger.error(f"Error reading from file {path}: {str(e)}")
        raise
