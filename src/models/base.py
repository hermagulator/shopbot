# src/models/base.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class TimeStampedModel(BaseModel):
    """Base model with timestamp fields"""
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)