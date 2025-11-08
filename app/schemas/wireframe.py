from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional, List
from datetime import datetime


class WireframeGenerateResponse(BaseModel):
    """Response schema for Wireframe generation."""

    wireframe_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    user_id: Optional[str] = Field(
        None, description="User ID who generated the document"
    )
    generated_at: str = Field(..., description="Timestamp when document was generated")
    input_description: str = Field(
        ..., description="Original input used for generation"
    )
    # figma_link: str = Field(..., description="Link Wireframe in Figma")
    # wireframe_description:str=Field(...,description="Wireframe description after generate")
    html_content: str = Field(..., description="Wireframe HTML content")
    css_content: str = Field(..., description="Wireframe CSS content")
