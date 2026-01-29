import time
import uuid
from typing import List, Dict, Any, Tuple, Optional
from app.schemas.request import PostRequest, StyleMode
from app.schemas.response import PostResponse, PostMetadata, TopicInfo
from app.chains.linkedin_chain import linkedin_chain
from app.utils.validators import post_validator
from app.vectorstore.store import vector_store
from app.config.settings import settings


class PostGeneratorService:
 
    
    def __init__(self):
        self.store = vector_store
        self.chain = linkedin_chain
        self.validator = post_validator
        self.similarity_threshold = settings.similarity_threshold
    
    async def generate_post(self, request: PostRequest) -> PostResponse:
        """
        Generate a LinkedIn post with memory-aware context.
        
        Pipeline:
        1. Check if series mode
        2. For series: fetch series posts, extract facts, generate with context
        3. For standalone: single vector search, generate based on style mode
        4. Validate and save
        5. Return response
        """
        start_time = time.time()
        
        series_id: Optional[str] = None
        series_order: Optional[int] = None
        topic_exists = False
        similar_topics = []
        topic_message = ""
        
        if request.is_series:
            # Series mode
            if request.series_id:
                # Continue existing series
                series_id = request.series_id
                series_posts = self.store.get_series_posts(request.user_id, series_id)
                series_order = len(series_posts) + 1
                
                # Extract facts from all previous posts in a SINGLE LLM call
                all_facts = await self.chain.extract_facts(series_posts)
                summaries = [
                    f"Post {post['metadata']['series_order']}: {post['metadata']['topic']}"
                    for post in series_posts
                ]
                
                # Generate with series context
                generated_post = await self.chain.generate_series_post(
                    topic=request.topic,
                    tone=request.tone.value,
                    audience=request.audience.value,
                    length=request.length.value,
                    series_facts=self._format_series_facts(all_facts),
                    post_summaries="\n".join(summaries) if summaries else "This is the first post in the series.",
                    series_order=series_order,
                    include_emoji=request.include_emoji,
                    include_hashtags=request.include_hashtags,
                    num_hashtags=request.num_hashtags
                )
                topic_message = f"Continuing series (Post #{series_order}). Built on {len(series_posts)} previous posts."
            else:
                # Start new series
                series_id = str(uuid.uuid4())
                series_order = 1
                
                # For first post in series, use similar mode generation
                similar_posts = self.store.search_similar_posts(
                    user_id=request.user_id,
                    query=request.topic,
                    n_results=settings.max_similar_posts_to_retrieve
                )
                memory_context = self._build_similar_context(similar_posts)
                generated_post = await self.chain.generate_similar_post(
                    topic=request.topic,
                    tone=request.tone.value,
                    audience=request.audience.value,
                    length=request.length.value,
                    writing_examples=memory_context["writing_examples"],
                    tone_patterns=memory_context["tone_patterns"],
                    include_emoji=request.include_emoji,
                    include_hashtags=request.include_hashtags,
                    num_hashtags=request.num_hashtags
                )
                topic_message = f"Started new series (Post #1). Series ID: {series_id}"
        else:
            # Standalone post - existing logic
            similar_posts = self.store.search_similar_posts(
                user_id=request.user_id,
                query=request.topic,
                n_results=settings.max_similar_posts_to_retrieve
            )
            
            topic_exists, similar_topics = self._check_topic_from_results(similar_posts)
            topic_message = self._get_topic_message(topic_exists, similar_topics, request.style_mode)
            
            if request.style_mode == StyleMode.SIMILAR:
                memory_context = self._build_similar_context(similar_posts)
                generated_post = await self.chain.generate_similar_post(
                    topic=request.topic,
                    tone=request.tone.value,
                    audience=request.audience.value,
                    length=request.length.value,
                    writing_examples=memory_context["writing_examples"],
                    tone_patterns=memory_context["tone_patterns"],
                    include_emoji=request.include_emoji,
                    include_hashtags=request.include_hashtags,
                    num_hashtags=request.num_hashtags
                )
            else:
                avoidance_context = self._build_different_context(similar_posts)
                generated_post = await self.chain.generate_different_post(
                    topic=request.topic,
                    tone=request.tone.value,
                    audience=request.audience.value,
                    length=request.length.value,
                    topics_to_avoid=avoidance_context["topics_to_avoid"],
                    patterns_to_avoid=avoidance_context["patterns_to_avoid"],
                    include_emoji=request.include_emoji,
                    include_hashtags=request.include_hashtags,
                    num_hashtags=request.num_hashtags
                )
        
        # Validate output
        self.validator.validate_all(generated_post)
        
        # Save to memory with series metadata
        self.store.add_post(
            user_id=request.user_id,
            topic=request.topic,
            post_content=generated_post,
            tone=request.tone.value,
            audience=request.audience.value,
            length=request.length.value,
            series_id=series_id,
            series_order=series_order
        )
        
        generation_time = (time.time() - start_time) * 1000
        
        return PostResponse(
            post=generated_post,
            topic_exists=topic_exists,
            similar_topics=[
                TopicInfo(
                    topic=t["topic"],
                    similarity_score=t["similarity_score"],
                    created_at=t.get("created_at")
                )
                for t in similar_topics
            ],
            message=topic_message,
            metadata=PostMetadata(
                tone=request.tone.value,
                audience=request.audience.value,
                length=request.length.value,
                style_mode=request.style_mode.value,
                generation_time_ms=generation_time,
                model_used=settings.azure_openai_deployment,
                series_id=series_id,
                series_order=series_order
            )
        )
    
    def _check_topic_from_results(
        self, similar_posts: List[Dict[str, Any]]
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Extract topic existence and similar topics from search results."""
        if not similar_posts:
            return False, []
        
        similar_topics = []
        for post in similar_posts:
            if post["similarity_score"] >= self.similarity_threshold:
                similar_topics.append({
                    "topic": post["metadata"].get("topic"),
                    "similarity_score": post["similarity_score"],
                    "created_at": post["metadata"].get("created_at")
                })
        
        return len(similar_topics) > 0, similar_topics
    
    def _get_topic_message(
        self, topic_exists: bool, similar_topics: List[Dict], style_mode: StyleMode
    ) -> str:
        """Generate user-friendly message about topic history."""
        if not topic_exists:
            return "This is a fresh topic for you!"
        
        top_topic = similar_topics[0]
        similarity_percent = int(top_topic["similarity_score"] * 100)
        
        if style_mode == StyleMode.SIMILAR:
            return (
                f"You've posted about '{top_topic['topic']}' before "
                f"({similarity_percent}% similar). I'll match your established style."
            )
        return (
            f"You've posted about '{top_topic['topic']}' before "
            f"({similarity_percent}% similar). I'll bring a fresh angle."
        )
    
    def _build_similar_context(self, similar_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build context for similar-style generation."""
        if not similar_posts:
            return {"writing_examples": [], "tone_patterns": []}
        
        writing_examples = []
        tone_patterns = set()
        
        for post in similar_posts:
            metadata = post["metadata"]
            writing_examples.append({
                "topic": metadata.get("topic"),
                "content": metadata.get("post_content", ""),
                "tone": metadata.get("tone"),
                "similarity": post["similarity_score"]
            })
            tone_patterns.add(metadata.get("tone"))
        
        return {
            "writing_examples": writing_examples,
            "tone_patterns": list(tone_patterns)
        }
    
    def _build_different_context(self, similar_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build context for different-style generation (patterns to avoid)."""
        if not similar_posts:
            return {"topics_to_avoid": [], "patterns_to_avoid": []}
        
        topics_to_avoid = []
        patterns_to_avoid = []
        
        for post in similar_posts:
            if post["similarity_score"] > self.similarity_threshold:
                metadata = post["metadata"]
                topics_to_avoid.append({
                    "topic": metadata.get("topic"),
                    "similarity": post["similarity_score"]
                })
                patterns_to_avoid.append({
                    "tone": metadata.get("tone"),
                    "length": metadata.get("length"),
                    "audience": metadata.get("audience")
                })
        
        return {
            "topics_to_avoid": topics_to_avoid,
            "patterns_to_avoid": patterns_to_avoid
        }
    
    def _format_series_facts(self, all_facts: List[Dict]) -> str:
        """Format extracted facts for the series prompt."""
        if not all_facts:
            return "No previous facts available (this is the first post)."
        
        formatted = []
        for i, facts in enumerate(all_facts, 1):
            formatted.append(f"### From Post {i}")
            for key, values in facts.items():
                if values and isinstance(values, list) and len(values) > 0:
                    formatted.append(f"**{key.replace('_', ' ').title()}**: {', '.join(str(v) for v in values)}")
        
        return "\n".join(formatted) if formatted else "No specific facts extracted."


# Global generator service instance
generator_service = PostGeneratorService()
