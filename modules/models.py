from pydantic import BaseModel, Field
from typing import List, Optional

class SocialMediaPost(BaseModel):
    """
    Represents a social media post with content, platform, and optional hashtags.
    """
    content: str = Field(..., description="The main text content of the social media post.")
    platform: str = Field(..., description="The social media platform for which the post is intended (e.g., 'Twitter', 'LinkedIn', 'Instagram').")
    hashtags: Optional[List[str]] = Field(None, description="A list of relevant hashtags for the post.")
    call_to_action: Optional[str] = Field(None, description="An optional call to action for the post.")

class PostGenerationRequest(BaseModel):
    """
    Represents a request to generate a social media post.
    """
    topic: str = Field(..., description="The topic or subject for the social media post.")
    platform: str = Field(..., description="The target social media platform (e.g., 'Twitter', 'LinkedIn').")
    tone: Optional[str] = Field("neutral", description="The desired tone of the post (e.g., 'formal', 'casual', 'humorous').")
    keywords: Optional[List[str]] = Field(None, description="Optional keywords to include in the post.")
