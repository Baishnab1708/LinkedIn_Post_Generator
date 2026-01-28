from fastapi import APIRouter, HTTPException

from app.schemas.request import PostRequest
from app.schemas.response import PostResponse, UserHistoryResponse, PostHistoryItem
from app.services.generator import generator_service
from app.vectorstore.store import vector_store

router = APIRouter()


@router.post("/generate", response_model=PostResponse)
async def generate_post(request: PostRequest):
    """
    Generate a LinkedIn post based on topic, tone, audience, and memory preferences.
    
    This is the main API endpoint. It returns:
    - The generated post
    - Whether the topic has been covered before
    - Similar topics (if any)
    - Generation metadata
    """
    try:
        return await generator_service.generate_post(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/history/{user_id}", response_model=UserHistoryResponse)
async def get_user_history(user_id: str, limit: int = 10):
    """Retrieve a user's past posts."""
    posts = vector_store.get_user_posts(user_id, limit)
    total_count = vector_store.count_user_posts(user_id)
    
    history_items = []
    for post in posts:
        metadata = post.get("metadata", {})
        content = metadata.get("post_content", "")
        history_items.append(PostHistoryItem(
            post_id=post.get("id", ""),
            topic=metadata.get("topic", "Unknown"),
            post_preview=content[:200] + "..." if len(content) > 200 else content,
            tone=metadata.get("tone", "unknown"),
            audience=metadata.get("audience", "unknown"),
            created_at=metadata.get("created_at", "")
        ))
    
    return UserHistoryResponse(user_id=user_id, total_posts=total_count, posts=history_items)


@router.get("/series/{user_id}")
async def get_user_series(user_id: str):
    """
    Get all series created by a user.
    Groups posts by series_id and returns summary for each series.
    """
    # Get all posts for user
    all_posts = vector_store.get_user_posts(user_id, limit=1000)
    
    # Group by series_id
    series_map = {}
    for post in all_posts:
        sid = post["metadata"].get("series_id")
        if sid:
            if sid not in series_map:
                series_map[sid] = []
            series_map[sid].append(post)
    
    # Sort posts within each series by series_order
    series_list = []
    for sid, posts in series_map.items():
        posts.sort(key=lambda x: x["metadata"].get("series_order", 0))
        series_list.append({
            "series_id": sid,
            "total_posts": len(posts),
            "first_topic": posts[0]["metadata"].get("topic", "Unknown"),
            "last_topic": posts[-1]["metadata"].get("topic", "Unknown"),
            "created_at": posts[0]["metadata"].get("created_at", "")
        })
    
    return {
        "user_id": user_id,
        "total_series": len(series_list),
        "series": series_list
    }
