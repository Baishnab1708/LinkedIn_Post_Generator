from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from app.config.settings import settings
from app.schemas.request import StyleMode


class LinkedInChain:
    
    def __init__(self):
        prompts_dir = Path(__file__).parent.parent / "prompts"
        
        with open(prompts_dir / "similar.txt", "r") as f:
            self.similar_template = f.read()
        
        with open(prompts_dir / "different.txt", "r") as f:
            self.different_template = f.read()
        
        with open(prompts_dir / "series.txt", "r") as f:
            self.series_template = f.read()
        
        with open(prompts_dir / "fact_extraction.txt", "r") as f:
            self.fact_extraction_template = f.read()
        
        self.output_parser = StrOutputParser()
    
    def _get_llm(self, style_mode: str) -> AzureChatOpenAI:
        """Get LLM with appropriate temperature based on style mode."""
        temperature = (
            settings.similar_mode_temperature 
            if style_mode == StyleMode.SIMILAR 
            else settings.different_mode_temperature
        )
        
        return AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            temperature=temperature,
            max_retries=5
        )
    
    def _format_writing_examples(self, examples: list) -> str:
        """Format past writing examples for the prompt."""
        if not examples:
            return "No past examples available. Create fresh content."
        
        formatted = []
        for i, ex in enumerate(examples, 1):
            formatted.append(
                f"### Example {i} (Topic: {ex.get('topic', 'N/A')})\n"
                f"{ex.get('content', '')}\n"
            )
        return "\n".join(formatted)
    
    def _format_topics_to_avoid(self, topics: list) -> str:
        """Format topics to avoid for the prompt."""
        if not topics:
            return "No previous topics to avoid."
        
        return "\n".join([
            f"- {t.get('topic', 'Unknown')} (similarity: {t.get('similarity', 0):.0%})"
            for t in topics
        ])
    
    def _format_patterns_to_avoid(self, patterns: list) -> str:
        """Format patterns to avoid for the prompt."""
        if not patterns:
            return "No specific patterns to avoid."
        
        unique_patterns = []
        seen = set()
        for p in patterns:
            key = f"{p.get('tone')}-{p.get('length')}"
            if key not in seen:
                seen.add(key)
                unique_patterns.append(
                    f"- Tone: {p.get('tone')}, Length: {p.get('length')}"
                )
        return "\n".join(unique_patterns)
    
    def _get_emoji_instruction(self, include_emoji: bool) -> str:
        """Get emoji usage instruction."""
        if include_emoji:
            return "Use 2-4 relevant emojis strategically placed"
        return "Do NOT use any emojis"
    
    def _get_hashtag_instruction(self, include_hashtags: bool, num_hashtags: int) -> str:
        """Get hashtag usage instruction."""
        if include_hashtags:
            return f"Include exactly {num_hashtags} relevant hashtags at the end"
        return "Do NOT include any hashtags"
    
    async def generate_similar_post(
        self,
        topic: str,
        tone: str,
        audience: str,
        length: str,
        writing_examples: list,
        tone_patterns: list,
        include_emoji: bool = True,
        include_hashtags: bool = True,
        num_hashtags: int = 3
    ) -> str:
        """
        Generate a post similar to user's past style.
        
        Args:
            topic: Post topic
            tone: Desired tone
            audience: Target audience
            length: Desired length
            writing_examples: Past writing examples
            tone_patterns: Established tone patterns
            include_emoji: Whether to include emojis
            include_hashtags: Whether to include hashtags
            num_hashtags: Number of hashtags
            
        Returns:
            Generated post content
        """
        llm = self._get_llm(StyleMode.SIMILAR)
        
        prompt = PromptTemplate.from_template(self.similar_template)
        
        chain = prompt | llm | self.output_parser
        
        result = await chain.ainvoke({
            "topic": topic,
            "tone": tone,
            "audience": audience,
            "length": length,
            "include_emoji": include_emoji,
            "include_hashtags": include_hashtags,
            "num_hashtags": num_hashtags,
            "writing_examples": self._format_writing_examples(writing_examples),
            "tone_patterns": ", ".join(tone_patterns) if tone_patterns else "None established",
            "emoji_instruction": self._get_emoji_instruction(include_emoji),
            "hashtag_instruction": self._get_hashtag_instruction(include_hashtags, num_hashtags)
        })
        
        return result
    
    async def generate_different_post(
        self,
        topic: str,
        tone: str,
        audience: str,
        length: str,
        topics_to_avoid: list,
        patterns_to_avoid: list,
        include_emoji: bool = True,
        include_hashtags: bool = True,
        num_hashtags: int = 3
    ) -> str:
        """
        Generate a post different from user's past style.
        
        Args:
            topic: Post topic
            tone: Desired tone
            audience: Target audience
            length: Desired length
            topics_to_avoid: Previously covered topics
            patterns_to_avoid: Patterns to not repeat
            include_emoji: Whether to include emojis
            include_hashtags: Whether to include hashtags
            num_hashtags: Number of hashtags
            
        Returns:
            Generated post content
        """
        llm = self._get_llm(StyleMode.DIFFERENT)
        
        prompt = PromptTemplate.from_template(self.different_template)
        
        chain = prompt | llm | self.output_parser
        
        result = await chain.ainvoke({
            "topic": topic,
            "tone": tone,
            "audience": audience,
            "length": length,
            "include_emoji": include_emoji,
            "include_hashtags": include_hashtags,
            "num_hashtags": num_hashtags,
            "topics_to_avoid": self._format_topics_to_avoid(topics_to_avoid),
            "patterns_to_avoid": self._format_patterns_to_avoid(patterns_to_avoid),
            "emoji_instruction": self._get_emoji_instruction(include_emoji),
            "hashtag_instruction": self._get_hashtag_instruction(include_hashtags, num_hashtags)
        })
        
        return result
    
    async def extract_facts(self, post_content: str, topic: str) -> Dict[str, List[str]]:
        """
        Extract key facts from a post for series context.
        
        Args:
            post_content: The post content to analyze
            topic: The topic of the post
            
        Returns:
            Dictionary with key_claims, personal_stories, lessons, questions
        """
        llm = self._get_llm(StyleMode.SIMILAR)
        prompt = PromptTemplate.from_template(self.fact_extraction_template)
        chain = prompt | llm | self.output_parser
        
        result = await chain.ainvoke({
            "post_content": post_content,
            "topic": topic
        })
        
        # Parse JSON response
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Return empty structure if parsing fails
            return {
                "key_claims": [],
                "personal_stories": [],
                "lessons": [],
                "questions": []
            }
    
    async def generate_series_post(
        self,
        topic: str,
        tone: str,
        audience: str,
        length: str,
        series_facts: str,
        post_summaries: str,
        series_order: int,
        include_emoji: bool = True,
        include_hashtags: bool = True,
        num_hashtags: int = 3
    ) -> str:
        """
        Generate a post that continues an existing series.
        
        Args:
            topic: Post topic
            tone: Desired tone
            audience: Target audience
            length: Desired length
            series_facts: Formatted facts from previous posts
            post_summaries: Summaries of previous posts
            series_order: Position in the series (1, 2, 3...)
            include_emoji: Whether to include emojis
            include_hashtags: Whether to include hashtags
            num_hashtags: Number of hashtags
            
        Returns:
            Generated post content
        """
        llm = self._get_llm(StyleMode.SIMILAR)  # Series always uses similar mode
        prompt = PromptTemplate.from_template(self.series_template)
        chain = prompt | llm | self.output_parser
        
        result = await chain.ainvoke({
            "topic": topic,
            "tone": tone,
            "audience": audience,
            "length": length,
            "series_facts": series_facts,
            "post_summaries": post_summaries,
            "series_order": series_order,
            "emoji_instruction": self._get_emoji_instruction(include_emoji),
            "hashtag_instruction": self._get_hashtag_instruction(include_hashtags, num_hashtags)
        })
        
        return result


# Global chain instance
linkedin_chain = LinkedInChain()
