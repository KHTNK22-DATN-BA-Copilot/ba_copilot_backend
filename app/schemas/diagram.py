from pydantic import BaseModel,Field
from typing import Optional

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
    mermaid_code:str=Field(..., description="Diagram content")
    description: str = Field(
        ..., description="Wireframe description after generate"
    )


class DiagramResponse(BaseModel):
    """Response schema for getting/updating diagram """
    diagram_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    title: str = Field(..., description="Diagram title")
    diagram_type: str = Field(..., description="Type of diagram")
    update_at: str = Field(..., description="Timestamp when document was generated")
    mermaid_code: str = Field(..., description="Diagram content")
    description: str = Field(..., description="Wireframe description after generate")
