import re
from typing import Tuple, List
from app.config.settings import settings


class PostValidator:
    """
    Validates generated LinkedIn posts.
    
    Checks:
    - Length within limits
    - LinkedIn-friendly content
    - Proper structure (hook, body, CTA)
    """
    
    def __init__(self):
        self.max_length = settings.max_post_length
        self.min_length = settings.min_post_length
        
        # Patterns that might indicate problematic content
        self.problematic_patterns = [
            r"(?i)http[s]?://(?!linkedin\.com)",  # External links (except LinkedIn)
            r"(?i)(buy now|click here|limited time)",  # Spammy phrases
            r"(?i)(dm me|message me for)",  # Overly promotional
        ]
    
    def validate_length(self, post: str) -> Tuple[bool, str]:
        """
        Check if post is within acceptable length.
        
        Args:
            post: The generated post
            
        Returns:
            Tuple of (is_valid, message)
        """
        length = len(post)
        
        if length < self.min_length:
            return False, f"Post too short ({length} chars). Minimum is {self.min_length}."
        
        if length > self.max_length:
            return False, f"Post too long ({length} chars). Maximum is {self.max_length}."
        
        return True, f"Length OK ({length} chars)"
    
    def validate_structure(self, post: str) -> Tuple[bool, List[str]]:
        """
        Check if post has proper structure: hook, body, CTA.
        
        Args:
            post: The generated post
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        lines = post.strip().split("\n")
        
        # Filter out empty lines
        content_lines = [l for l in lines if l.strip()]
        
        if len(content_lines) < 2:
            issues.append("Post needs more content (hook + body minimum)")
        
        # Check for hook (first line should be engaging)
        if content_lines:
            first_line = content_lines[0].strip()
            if len(first_line) < 10:
                issues.append("Hook (first line) is too short")
        
        # Check for some form of CTA or engagement prompt
        last_line = content_lines[-1].lower() if content_lines else ""
        cta_indicators = [
            "?", "comment", "share", "thoughts", "agree", "disagree",
            "let me know", "what do you", "how do you", "have you"
        ]
        
        has_cta = any(indicator in last_line for indicator in cta_indicators)
        if not has_cta:
            issues.append("Consider adding a call-to-action or question at the end")
        
        return len(issues) == 0, issues
    
    def validate_linkedin_friendly(self, post: str) -> Tuple[bool, List[str]]:
        """
        Check if content is LinkedIn-appropriate.
        
        Args:
            post: The generated post
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        for pattern in self.problematic_patterns:
            if re.search(pattern, post):
                issues.append(f"Contains potentially problematic content: {pattern}")
        
        # Check for excessive caps (shouty)
        words = post.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 2]
        if len(caps_words) > 3:
            issues.append("Too many ALL CAPS words - may seem aggressive")
        
        # Check for excessive emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        emojis = emoji_pattern.findall(post)
        if len(emojis) > 10:
            issues.append("Too many emojis - may reduce professional appearance")
        
        return len(issues) == 0, issues
    
    def validate_all(self, post: str) -> dict:
        """
        Run all validations on a post.
        
        Args:
            post: The generated post
            
        Returns:
            Dict with validation results
        """
        length_valid, length_msg = self.validate_length(post)
        structure_valid, structure_issues = self.validate_structure(post)
        linkedin_valid, linkedin_issues = self.validate_linkedin_friendly(post)
        
        all_valid = length_valid and structure_valid and linkedin_valid
        
        return {
            "is_valid": all_valid,
            "length": {
                "valid": length_valid,
                "message": length_msg
            },
            "structure": {
                "valid": structure_valid,
                "issues": structure_issues
            },
            "linkedin_friendly": {
                "valid": linkedin_valid,
                "issues": linkedin_issues
            }
        }


# Global validator instance
post_validator = PostValidator()
