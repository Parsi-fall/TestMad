from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

# Re-export get_db for cleaner imports
__all__ = ["get_db"]
