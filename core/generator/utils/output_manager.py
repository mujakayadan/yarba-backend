"""Output management utilities for the generator package."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.logging_config import get_logger
from config.settings import Settings
from utils.file import ensure_directory_exists

logger = get_logger(__name__)
settings = Settings()


class OutputManager:
    """Manager for handling output files and directories."""

    def __init__(self, user_id: str, resume_id: str):
        """
        Initialize the output manager.

        Args:
            user_id: User ID
            resume_id: Resume ID
        """
        self.user_id = user_id
        self.resume_id = resume_id
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Set up output directory
        self.output_dir = self._setup_output_directory()

    def _setup_output_directory(self) -> Path:
        """
        Set up the output directory structure.

        Returns:
            Path: Path to the output directory
        """
        # Create unique directory path
        output_dir = (
            settings.paths.output_dir / self.user_id / self.resume_id / self.timestamp
        )

        # Ensure directory exists
        ensure_directory_exists(output_dir)
        logger.debug(f"Created output directory: {output_dir}")

        return output_dir

    def get_resume_path(self, extension: str = ".tex") -> Path:
        """
        Get path for a resume file.

        Args:
            extension: File extension

        Returns:
            Path: Path to the resume file
        """
        return self.output_dir / f"resume{extension}"

    def get_cover_letter_path(self, extension: str = ".tex") -> Path:
        """
        Get path for a cover letter file.

        Args:
            extension: File extension

        Returns:
            Path: Path to the cover letter file
        """
        return self.output_dir / f"cover_letter{extension}"

    def get_temp_path(self, filename: str) -> Path:
        """
        Get path for a temporary file.

        Args:
            filename: Name of the file

        Returns:
            Path: Path to the temporary file
        """
        return self.output_dir / filename

    def cleanup(self, keep_pdf: bool = True) -> None:
        """
        Clean up output files.

        Args:
            keep_pdf: Whether to keep PDF files
        """
        try:
            for file in self.output_dir.glob("*"):
                if keep_pdf and file.suffix.lower() == ".pdf":
                    continue
                if file.is_file():
                    file.unlink()
                    logger.debug(f"Removed file: {file}")

            # Remove empty directory
            if not any(self.output_dir.iterdir()):
                self.output_dir.rmdir()
                logger.debug(f"Removed empty directory: {self.output_dir}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def copy_file(
        self,
        source: Path,
        destination: Optional[Path] = None,
        new_name: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Copy a file to the output directory.

        Args:
            source: Source file path
            destination: Optional destination path
            new_name: Optional new filename

        Returns:
            Optional[Path]: Path to the copied file if successful
        """
        try:
            if not source.exists():
                logger.error(f"Source file does not exist: {source}")
                return None

            if destination is None:
                destination = self.output_dir

            if new_name:
                destination = destination / new_name
            else:
                destination = destination / source.name

            shutil.copy2(source, destination)
            logger.debug(f"Copied file from {source} to {destination}")

            return destination

        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return None
