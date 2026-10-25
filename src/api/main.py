"""ASGI entry point: uvicorn src.api.main:app"""
from .app import app

__all__ = ["app"]
