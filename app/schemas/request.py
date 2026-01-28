"""
Request schemas for LinkedIn Post Generator.
Defines all input models with validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class ToneType(str, Enum):
    """Available tone options for posts."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    STORYTELLING = "storytelling"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"
    HUMOROUS = "humorous"


class AudienceType(str, Enum):
    """Target audience types."""
    RECRUITERS = "recruiters"
    ENGINEERS = "engineers"
    FOUNDERS = "founders"
    MARKETERS = "marketers"
    GENERAL = "general"
    STUDENTS = "students"


class LengthType(str, Enum):
    """Post length options."""
    SHORT = "short"      # ~100-300 characters
    MEDIUM = "medium"    # ~300-800 characters
    LONG = "long"        # ~800-2000 characters


class StyleMode(str, Enum):
    """How to use memory for generation."""
    SIMILAR = "similar"      # Match past writing style
    DIFFERENT = "different"  # Avoid past patterns


class PostRequest(BaseModel):
    """
    Main request model for generating a LinkedIn post.
    This is the only place where user intention is defined.
    """
    
    # Required fields
    user_id: str = Field(
        ..., 
        description="Unique user identifier for memory lookup",
        min_length=1
    )
    topic: str = Field(
        ..., 
        description="The main topic or subject of the post",
        min_length=3,
        max_length=500
    )
    
    # Style configuration
    tone: ToneType = Field(
        default=ToneType.PROFESSIONAL,
        description="The tone/voice of the post"
    )
    audience: AudienceType = Field(
        default=AudienceType.GENERAL,
        description="Target audience for the post"
    )
    length: LengthType = Field(
        default=LengthType.MEDIUM,
        description="Desired length of the post"
    )
    style_mode: StyleMode = Field(
        default=StyleMode.SIMILAR,
        description="Similar = match past style, Different = fresh approach"
    )
    
    # Additional preferences
    include_emoji: bool = Field(
        default=True,
        description="Whether to include emojis in the post"
    )
    include_hashtags: bool = Field(
        default=True,
        description="Whether to include hashtags"
    )
    num_hashtags: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of hashtags to include"
    )
    
    # Series configuration
    is_series: bool = Field(
        default=False,
        description="Whether this post belongs to a series"
    )
    series_id: Optional[str] = Field(
        default=None,
        description="Series ID to continue. Leave empty to start new series or standalone post."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "topic": "The importance of work-life balance in tech",
                "tone": "professional",
                "audience": "engineers",
                "length": "medium",
                "style_mode": "similar",
                "include_emoji": True,
                "include_hashtags": True,
                "num_hashtags": 3,
                "is_series": False,
                "series_id": " "
            }
        }



