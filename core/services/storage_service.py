"""Storage service module.

This module re-exports the storage provider from utils.storage.
"""

from utils.storage import (
    AWSS3StorageProvider,
    LocalStorageProvider,
    StorageProvider,
    get_storage_provider,
)

__all__ = [
    "StorageProvider",
    "LocalStorageProvider",
    "AWSS3StorageProvider",
    "get_storage_provider",
]
