# app/utils/metadata_utils.py
"""
Utility functions for handling file metadata.

This module provides helper functions for:
- Creating metadata for AI-generated files (auto-assign line ranges)
- Parsing metadata extraction responses
- Standardizing metadata format across the application
"""

from typing import Dict, Any, Optional, List


# List of all document types supported by the system
ALL_DOCUMENT_TYPES = [
    # Phase 1: Project Initiation
    "stakeholder-register",
    "high-level-requirements",
    "requirements-management-plan",
    # Phase 2: Business Planning
    "business-case",
    "scope-statement",
    "product-roadmap",
    # Phase 3: Feasibility & Risk Analysis
    "feasibility-study",
    "cost-benefit-analysis",
    "risk-register",
    "compliance",
    # Phase 4: High-Level Design
    "hld-arch",
    "hld-cloud",
    "hld-tech",
    # Phase 5: Low-Level Design
    "lld-arch",
    "lld-db",
    "lld-api",
    "lld-pseudo",
    # Phase 6: UI/UX Design
    "uiux-wireframe",
    "uiux-mockup",
    "uiux-prototype",
    # Phase 7: Testing & QA
    "rtm",
    # Additional
    "srs",
    "class-diagram",
    "usecase-diagram",
    "activity-diagram",
    "wireframe",
]


def count_lines(content: str) -> int:
    """
    Count the number of lines in content.
    
    Args:
        content: The text content
        
    Returns:
        Number of lines (at least 1)
    """
    if not content:
        return 1
    return len(content.split('\n'))


def create_ai_generated_metadata(
    doc_type: str,
    content: str,
    message: Optional[str] = None,
    ai_response: Optional[Dict] = None,
    step: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create metadata for AI-generated files.
    
    For AI-generated files, we know the entire content is a single document type,
    so we auto-assign line_start=1 and line_end=total_lines for that type,
    and -1 for all other types.
    
    Args:
        doc_type: The document type identifier (e.g., 'business-case')
        content: The generated content (to count lines)
        message: Optional user message/prompt
        ai_response: Optional raw AI response
        step: Optional step identifier (e.g., 'planning', 'analysis')
        
    Returns:
        Dict with structured metadata
    """
    total_lines = count_lines(content)
    
    # Build document_types dict with line ranges
    document_types = {}
    for dt in ALL_DOCUMENT_TYPES:
        if dt == doc_type:
            document_types[dt] = {
                "line_start": 1,
                "line_end": total_lines
            }
        else:
            document_types[dt] = {
                "line_start": -1,
                "line_end": -1
            }
    
    metadata = {
        "extraction_status": "auto_assigned",
        "document_types": document_types,
        "primary_type": doc_type,
        "total_lines": total_lines,
    }
    
    # Add optional fields
    if message:
        metadata["message"] = message
    if ai_response:
        metadata["ai_response"] = ai_response
    if step:
        metadata["step"] = step
    
    return metadata


def parse_metadata_response(response: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """
    Parse metadata extraction response from AI service into a dict format.
    
    Args:
        response: The response from AI metadata extraction service
        
    Returns:
        Dict mapping document type to {line_start, line_end}
    """
    document_types = {}
    
    if not response:
        return document_types
    
    items = response.get("response", [])
    if isinstance(items, list):
        for item in items:
            doc_type = item.get("type")
            if doc_type:
                document_types[doc_type] = {
                    "line_start": item.get("line_start", -1),
                    "line_end": item.get("line_end", -1)
                }
    
    return document_types


def get_detected_types(metadata: Dict[str, Any]) -> List[str]:
    """
    Get list of document types that were detected (line_start != -1).
    
    Args:
        metadata: The file metadata dict
        
    Returns:
        List of detected document type identifiers
    """
    detected = []
    document_types = metadata.get("document_types", {})
    
    for doc_type, ranges in document_types.items():
        if isinstance(ranges, dict) and ranges.get("line_start", -1) != -1:
            detected.append(doc_type)
    
    return detected


def create_user_upload_metadata(
    metadata_response: Dict[str, Any],
    content: str,
    filename: str
) -> Dict[str, Any]:
    """
    Create metadata for user-uploaded files after AI extraction.
    
    This provides a consistent structure matching AI-generated files.
    
    Args:
        metadata_response: Response from AI metadata extraction service
        content: The markdown content
        filename: Original filename
        
    Returns:
        Standardized metadata dict
    """
    document_types = parse_metadata_response(metadata_response)
    
    return {
        "extraction_status": "success",
        "document_types": document_types,
        "total_lines": count_lines(content),
        "source_file": filename,
    }


def merge_metadata(existing: Dict[str, Any], new_extraction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge existing metadata with new extraction results.
    
    Preserves existing fields while updating document_types.

    If there are name conflict, the new one takes precedence.
    
    Args:
        existing: Existing metadata dict
        new_extraction: New extraction results
        
    Returns:
        Merged metadata dict
    """
    merged = existing.copy()
    
    # Update document_types
    if "document_types" in new_extraction:
        merged["document_types"] = new_extraction["document_types"]
        merged["extraction_status"] = new_extraction.get("extraction_status", "updated")
    
    return merged
