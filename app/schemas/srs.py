from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional


class SRSRequest(BaseModel):
    project_id: int
    user_id: int
    project_name: str
    description: str
    project_file_paths: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=5,
            description="List of file paths (maximum 5 files)",
        ),
    ]


class SRSGenerateResponse(BaseModel):
    """Response schema for SRS generation."""

    document_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    user_id: Optional[str] = Field(
        None, description="User ID who generated the document"
    )
    generated_at: str = Field(..., description="Timestamp when document was generated")
    input_description: str = Field(
        ..., description="Original input used for generation"
    )
    document: Dict[str, Any] = Field(
        ..., description="Generated SRS document in JSON format"
    )
    status: str = Field(..., description="Generation status")
