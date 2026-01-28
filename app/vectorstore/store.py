"""
Vector Store Setup using Qdrant.
Handles embedding storage and similarity search for user posts.
Supports metadata filtering BEFORE vector search for better performance.
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    ScrollRequest
)
from fastembed import TextEmbedding
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from app.config.settings import settings


class VectorStore:
    """
    Qdrant-based vector store for LinkedIn posts.
    Each user has their posts stored with embeddings for similarity search.
    Supports metadata pre-filtering before vector search.
    """
    
    # Embedding dimension for fastembed's default model (BAAI/bge-small-en-v1.5)
    EMBEDDING_DIM = 384
    
    def __init__(self):
        """Initialize Qdrant client with persistent local storage."""
        # Local persistent storage
        self.client = QdrantClient(path=settings.qdrant_path)
        self.collection_name = settings.qdrant_collection_name
        
        # Initialize fastembed model for generating embeddings
        self.embedding_model = TextEmbedding()
        
        # Create collection if it doesn't exist
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create collection with vector config if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using fastembed."""
        embeddings = list(self.embedding_model.embed([text]))
        return embeddings[0].tolist()
    
    def add_post(
        self,
        user_id: str,
        topic: str,
        post_content: str,
        tone: str,
        audience: str,
        length: str,
        series_id: Optional[str] = None,
        series_order: Optional[int] = None
    ) -> str:
        """
        Add a new post to the vector store.
        
        Args:
            user_id: Unique user identifier
            topic: Post topic
            post_content: Full post content
            tone: Tone used
            audience: Target audience
            length: Post length category
            series_id: Optional series identifier for series posts
            series_order: Optional position in series (1, 2, 3...)
            
        Returns:
            Generated post ID
        """
        post_id = str(uuid.uuid4())
        
        # Combine topic and content for embedding
        document = f"Topic: {topic}\n\nPost: {post_content}"
        
        # Generate embedding
        embedding = self._get_embedding(document)
        
        # Create point with payload (metadata)
        point = PointStruct(
            id=post_id,
            vector=embedding,
            payload={
                "user_id": user_id,
                "topic": topic,
                "post_content": post_content,
                "document": document,
                "tone": tone,
                "audience": audience,
                "length": length,
                "series_id": series_id,
                "series_order": series_order,
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        return post_id
    
    def search_similar_posts(
        self,
        user_id: str,
        query: str,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for similar posts by a specific user.
        Filters by user_id FIRST (metadata filtering), then performs vector search.
        
        Args:
            user_id: User to search posts for
            query: Topic or text to find similar posts
            n_results: Maximum number of results
            
        Returns:
            List of similar posts with metadata and similarity scores
        """
        # Generate query embedding
        query_embedding = self._get_embedding(query)
        
        # Search with metadata filter - filter by user_id BEFORE vector search
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            ),
            limit=n_results
        )
        
        posts = []
        for hit in results.points:
            posts.append({
                "id": hit.id,
                "document": hit.payload.get("document", ""),
                "metadata": {
                    "user_id": hit.payload.get("user_id"),
                    "topic": hit.payload.get("topic"),
                    "post_content": hit.payload.get("post_content"),
                    "tone": hit.payload.get("tone"),
                    "audience": hit.payload.get("audience"),
                    "length": hit.payload.get("length"),
                    "series_id": hit.payload.get("series_id"),
                    "series_order": hit.payload.get("series_order"),
                    "created_at": hit.payload.get("created_at")
                },
                "similarity_score": hit.score  # Cosine similarity (0-1)
            })
        
        return posts
    
    def get_user_posts(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all posts for a user using scroll (metadata filter only).
        
        Args:
            user_id: User identifier
            limit: Maximum posts to return
            
        Returns:
            List of user's posts with metadata
        """
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        posts = []
        for point in results:
            posts.append({
                "id": point.id,
                "document": point.payload.get("document", ""),
                "metadata": {
                    "user_id": point.payload.get("user_id"),
                    "topic": point.payload.get("topic"),
                    "post_content": point.payload.get("post_content"),
                    "tone": point.payload.get("tone"),
                    "audience": point.payload.get("audience"),
                    "length": point.payload.get("length"),
                    "series_id": point.payload.get("series_id"),
                    "series_order": point.payload.get("series_order"),
                    "created_at": point.payload.get("created_at")
                }
            })
        
        return posts
    
    def get_user_topics(self, user_id: str) -> List[str]:
        """
        Get all topics a user has posted about.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of topics
        """
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            ),
            limit=1000,  # Get all posts
            with_payload=["topic"],
            with_vectors=False
        )
        
        return [point.payload.get("topic") for point in results if point.payload.get("topic")]
    
    def get_series_posts(self, user_id: str, series_id: str) -> List[Dict[str, Any]]:
        """
        Get all posts in a series using metadata filter on user_id + series_id.
        Returns posts ordered by series_order.
        
        Args:
            user_id: User identifier
            series_id: Series identifier
            
        Returns:
            List of posts in the series, ordered by series_order
        """
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    ),
                    FieldCondition(
                        key="series_id",
                        match=MatchValue(value=series_id)
                    )
                ]
            ),
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        posts = []
        for point in results:
            posts.append({
                "id": point.id,
                "document": point.payload.get("document", ""),
                "metadata": {
                    "user_id": point.payload.get("user_id"),
                    "topic": point.payload.get("topic"),
                    "post_content": point.payload.get("post_content"),
                    "tone": point.payload.get("tone"),
                    "audience": point.payload.get("audience"),
                    "length": point.payload.get("length"),
                    "series_id": point.payload.get("series_id"),
                    "series_order": point.payload.get("series_order"),
                    "created_at": point.payload.get("created_at")
                }
            })
        
        # Sort by series_order
        posts.sort(key=lambda x: x["metadata"].get("series_order", 0))
        return posts

    def count_user_posts(self, user_id: str) -> int:
        """Count total posts for a user."""
        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
        )
        return result.count


# Global vector store instance
vector_store = VectorStore()
