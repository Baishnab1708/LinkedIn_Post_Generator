"""
Response schemas for LinkedIn Post Generator.
Defines all output models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TopicInfo(BaseModel):
    """Information about a previously covered topic."""
    topic: str
    similarity_score: float
    created_at: Optional[str] = None


class PostMetadata(BaseModel):
    """Metadata about the generated post."""
    tone: str
    audience: str
    length: str
    style_mode: str
    generation_time_ms: float
    model_used: str
    series_id: Optional[str] = None
    series_order: Optional[int] = None


class PostResponse(BaseModel):
    """
    Response model for generated LinkedIn post.
    Delivers value to user with optional context.
    """
    
    # Main content
    post: str = Field(
        ..., 
        description="The generated LinkedIn post"
    )
    
    # Topic context
    topic_exists: bool = Field(
        default=False,
        description="Whether user has posted on this topic before"
    )
    similar_topics: List[TopicInfo] = Field(
        default=[],
        description="List of similar past topics if any"
    )
    
    # Optional message to user
    message: Optional[str] = Field(
        default=None,
        description="Optional context message (e.g., 'You've posted on this before')"
    )
    
    # Metadata
    metadata: PostMetadata

    class Config:
        json_schema_extra = {
            "example": {
                "post": "🚀 Work-life balance isn't just a buzzword...\n\n[Post content here]\n\n#TechLife #WorkLifeBalance #Engineering",
                "topic_exists": True,
                "similar_topics": [
                    {
                        "topic": "Burnout in software engineering",
                        "similarity_score": 0.82
                    }
                ],
                "message": "You've posted about similar topics before. This post brings a fresh angle.",
                "metadata": {
                    "tone": "professional",
                    "audience": "engineers",
                    "length": "medium",
                    "style_mode": "similar",
                    "generation_time_ms": 1523.5,
                    "model_used": "gpt-4o-mini",
                    "series_id": None,
                    "series_order": None
                }
            }
        }


class TopicCheckResponse(BaseModel):
    """Response for topic similarity check."""
    exists: bool = Field(..., description="Whether topic was covered before")
    similar_topics: List[TopicInfo] = Field(default=[])
    message: str = Field(..., description="Human-readable summary")


class PostHistoryItem(BaseModel):
    """A single post from user's history."""
    post_id: str
    topic: str
    post_preview: str = Field(..., description="First 200 chars of post")
    tone: str
    audience: str
    created_at: str


class UserHistoryResponse(BaseModel):
    """Response for user's post history."""
    user_id: str
    total_posts: int
    posts: List[PostHistoryItem]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: str
