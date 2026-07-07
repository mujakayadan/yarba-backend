"""Shared MongoDB async types (PyMongo; Beanie 2.x)."""

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

AsyncMongoClientType = AsyncMongoClient
AsyncMongoDatabase = AsyncDatabase
