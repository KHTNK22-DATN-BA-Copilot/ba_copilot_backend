from pydantic import BaseModel,Field
from typing import Optional,List

class DiagramGenerateResponse(BaseModel):
    """Response schema for diagram generation."""

    diagram_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    title: str=Field(..., description="Diagram title")
    diagram_type: str = Field(..., description="Type of diagram")
    user_id: Optional[str] = Field(
        None, description="User ID who generated the document"
    )
    generated_at: str = Field(..., description="Timestamp when document was generated")
    input_description: str = Field(
        ..., description="Original input used for generation"
    )
    content_md:str=Field(..., description="Diagram content")
    description: str = Field(
        ..., description="Wireframe description after generate"
    )


class DiagramResponse(BaseModel):
    """Response schema for updating diagram """
    diagram_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    title: str = Field(..., description="Diagram title")
    diagram_type: str = Field(..., description="Type of diagram")
    update_at: str = Field(..., description="Timestamp when document was generated")
    content_md: str = Field(..., description="Diagram content")
    description: str = Field(..., description="Wireframe description after generate")


class DiagramListResponse(BaseModel):
    diagrams: List[DiagramResponse] = Field(..., description="List of user's project's diagram")


class DiagramUpdateResponse(BaseModel):
    """Response schema for updating diagram"""
    diagram_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    title: str = Field(..., description="Diagram title")
    diagram_type: str = Field(..., description="Type of diagram")
    update_at: str = Field(..., description="Timestamp when document was generated")
    content_md: str = Field(..., description="Diagram content")
