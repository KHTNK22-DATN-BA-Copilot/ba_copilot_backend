# AI Service Implementation Guide

## BA Copilot AI - Document Generation Service

**Version:** 1.0  
**Date:** January 2, 2026  
**Authors:** BA Copilot Team  
**Status:** Active  
**Repository:** ba_copilot_ai  
**Companion Documents:**
- [DOCUMENT_CONSTRAINTS_SPECIFICATION.md](./DOCUMENT_CONSTRAINTS_SPECIFICATION.md)
- [ai_api_specs.md](./ai_api_specs.md)

---

## 1. Overview

This guide provides implementation details for the **AI Service** component of the BA Copilot constraint system. The AI Service is a **pure generation service** with NO constraint enforcement responsibilities.

### 1.1 AI Service Responsibilities

The AI Service focuses exclusively on:

✅ **Document Generation**: Generate business analysis artifacts using LLM APIs  
✅ **Context Processing**: Accept and utilize prerequisite document context from Backend  
✅ **LangGraph Workflows**: Orchestrate multi-step generation workflows  
✅ **Response Formatting**: Return structured AIResponse objects  

❌ **NOT Responsible For**:
- Constraint checking or validation
- Prerequisite detection
- Enforcement of document dependencies
- Direct database access for constraints

### 1.2 Architecture Context

```
┌────────────────────────────────────────────────────────────────┐
│                    AI SERVICE ROLE                              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   Backend (Validated Request)                                  │
│         │                                                      │
│         │ POST /api/ai/generate/{doc_type}                     │
│         │ {                                                    │
│         │   "project_id": "...",                               │
│         │   "context": {                                       │
│         │     "feasibility-study": "...",                      │
│         │     "business-case": "..."                           │
│         │   }                                                  │
│         │ }                                                    │
│         ▼                                                      │
│   ┌──────────────┐                                            │
│   │  AI Service  │                                            │
│   │  (FastAPI)   │                                            │
│   └──────┬───────┘                                            │
│          │                                                     │
│          │ 1. Route to LangGraph Workflow                     │
│          ▼                                                     │
│   ┌─────────────────┐                                         │
│   │ LangGraph       │                                         │
│   │ Workflow        │                                         │
│   │                 │                                         │
│   │ ┌─────────────┐ │                                         │
│   │ │ Context     │ │                                         │
│   │ │ Preparation │ │                                         │
│   │ └──────┬──────┘ │                                         │
│   │        │        │                                         │
│   │        ▼        │                                         │
│   │ ┌─────────────┐ │                                         │
│   │ │ LLM Call    │ │───────▶ OpenAI/Anthropic               │
│   │ └──────┬──────┘ │                                         │
│   │        │        │                                         │
│   │        ▼        │                                         │
│   │ ┌─────────────┐ │                                         │
│   │ │ Post-       │ │                                         │
│   │ │ Processing  │ │                                         │
│   │ └──────┬──────┘ │                                         │
│   └────────┼────────┘                                         │
│            │                                                   │
│            │ Return AIResponse                                │
│            ▼                                                   │
│      Backend (Stores Result)                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. File Structure

```
ba_copilot_ai/
├── main.py                    # FastAPI app with 26 generation endpoints
├── models/                    # Request/Response Pydantic models
│   ├── __init__.py
│   ├── business_case.py       # BusinessCaseRequest/Response
│   ├── feasibility_study.py
│   ├── srs.py
│   └── ...                    # One file per document type
├── workflows/                 # LangGraph workflow implementations
│   ├── __init__.py
│   ├── business_case_workflow/
│   │   ├── __init__.py
│   │   ├── nodes.py           # Workflow nodes
│   │   ├── graph.py           # LangGraph definition
│   │   └── state.py           # State models
│   ├── feasibility_study_workflow/
│   └── ...                    # One folder per document type
└── services/                  # Shared services
    └── mermaid_validator/     # Diagram validation utilities
```

---

## 3. Request/Response Models

### 3.1 Unified AIRequest Format

All 26 document generation endpoints accept the same request format:

```python
# models/base.py (or in main.py)

from pydantic import BaseModel
from typing import Optional, List, Dict

class AIRequest(BaseModel):
    """Unified request format for all AI generation endpoints."""
    
    # User input
    message: str                           # Required: User prompt/description
    
    # Context enrichment
    content_id: Optional[str] = None       # UUID for chat history lookup
    storage_paths: Optional[List[str]] = None  # Files in Supabase Storage
    
    # Backend-provided context (NEW for constraint system)
    project_id: Optional[str] = None       # Project UUID
    project_name: Optional[str] = None     # Project name
    project_description: Optional[str] = None  # Project overview
    context: Optional[Dict[str, str]] = None   # Prerequisite documents
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Generate high-level architecture design",
                "content_id": "123e4567-e89b-12d3-a456-426614174000",
                "storage_paths": ["uploads/requirements.pdf"],
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "project_name": "E-Commerce Platform",
                "project_description": "Modern web-based e-commerce solution",
                "context": {
                    "feasibility-study": "# Feasibility Study\n\n...",
                    "business-case": "# Business Case\n\n..."
                }
            }
        }
```

### 3.2 AIResponse Format

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class AIResponse(BaseModel):
    """Unified response format for all AI generation endpoints."""
    
    success: bool                          # True if generation succeeded
    content: Optional[str] = None          # Generated document (markdown or mermaid)
    metadata: Optional[Dict[str, Any]] = None  # Generation metadata
    error: Optional[str] = None            # Error message if failed
    details: Optional[str] = None          # Additional error details
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "content": "# High-Level Design\n\n## System Overview...",
                "metadata": {
                    "model": "claude-3-7-sonnet-20250219",
                    "tokens": 2847,
                    "duration": 12.3,
                    "prerequisites_used": ["feasibility-study", "business-case"]
                }
            }
        }
```

---

## 4. Endpoint Implementation

### 4.1 Main API File Structure

```python
# main.py

from fastapi import FastAPI, HTTPException
from models.business_case import AIRequest, AIResponse
from workflows.business_case_workflow import generate_business_case

app = FastAPI(title="BA Copilot AI Service")

# ============================================================================
# Phase 2: Business Planning
# ============================================================================

@app.post("/api/ai/generate/business-case", response_model=AIResponse)
async def generate_business_case_endpoint(request: AIRequest):
    """
    Generate Business Case document.
    
    Prerequisites (provided by Backend in request.context):
    - stakeholder-register (required)
    - high-level-requirements (recommended)
    
    The AI Service does NOT validate prerequisites - Backend already did this.
    We simply use whatever context is provided.
    """
    try:
        # Extract context from request
        context = request.context or {}
        
        # Call LangGraph workflow
        result = await generate_business_case(
            user_prompt=request.message,
            project_id=request.project_id,
            project_name=request.project_name,
            project_description=request.project_description,
            prerequisite_context=context,
            chat_history_id=request.content_id,
            storage_paths=request.storage_paths
        )
        
        return AIResponse(
            success=True,
            content=result["content"],
            metadata={
                "model": result.get("model", "unknown"),
                "tokens": result.get("tokens", 0),
                "duration": result.get("duration", 0),
                "prerequisites_used": list(context.keys())
            }
        )
        
    except Exception as e:
        return AIResponse(
            success=False,
            error="Failed to generate document",
            details=str(e)
        )

# Repeat for all 26 document types...
```

### 4.2 Complete Endpoint List

All 26 endpoints follow the same pattern:

```
POST /api/ai/generate/stakeholder-register
POST /api/ai/generate/high-level-requirements
POST /api/ai/generate/requirements-management-plan
POST /api/ai/generate/business-case
POST /api/ai/generate/scope-statement
POST /api/ai/generate/product-roadmap
POST /api/ai/generate/feasibility-study
POST /api/ai/generate/cost-benefit-analysis
POST /api/ai/generate/risk-register
POST /api/ai/generate/compliance
POST /api/ai/generate/hld-arch
POST /api/ai/generate/hld-cloud
POST /api/ai/generate/hld-tech
POST /api/ai/generate/lld-arch
POST /api/ai/generate/lld-db
POST /api/ai/generate/lld-api
POST /api/ai/generate/lld-pseudo
POST /api/ai/generate/uiux-wireframe
POST /api/ai/generate/uiux-mockup
POST /api/ai/generate/uiux-prototype
POST /api/ai/generate/rtm
POST /api/ai/generate/srs
POST /api/ai/generate/class-diagram
POST /api/ai/generate/usecase-diagram
POST /api/ai/generate/activity-diagram
POST /api/ai/generate/wireframe
```

---

## 5. LangGraph Workflow Implementation

### 5.1 Workflow State Model

```python
# workflows/business_case_workflow/state.py

from typing import TypedDict, List, Dict, Optional

class BusinessCaseState(TypedDict):
    """State for business case generation workflow."""
    
    # Input from endpoint
    user_prompt: str
    project_id: Optional[str]
    project_name: Optional[str]
    project_description: Optional[str]
    prerequisite_context: Dict[str, str]  # NEW: Context from Backend
    chat_history: List[Dict[str, str]]
    file_contents: List[str]
    
    # Generated during workflow
    enriched_prompt: str
    llm_response: str
    final_content: str
    
    # Metadata
    model_used: str
    tokens_used: int
    duration: float
```

### 5.2 Context Preparation Node

```python
# workflows/business_case_workflow/nodes.py

from typing import Dict
from .state import BusinessCaseState

def prepare_context(state: BusinessCaseState) -> Dict:
    """
    Prepare enriched prompt with prerequisite context.
    
    This is where we utilize the context provided by the Backend.
    We do NOT validate prerequisites - Backend already ensured they exist.
    """
    
    user_prompt = state["user_prompt"]
    prerequisite_context = state.get("prerequisite_context", {})
    
    # Build enriched prompt with context
    context_sections = []
    
    # Add prerequisite documents
    if "stakeholder-register" in prerequisite_context:
        context_sections.append(
            f"## Stakeholder Register (Prerequisite)\n\n{prerequisite_context['stakeholder-register']}"
        )
    
    if "high-level-requirements" in prerequisite_context:
        context_sections.append(
            f"## High-Level Requirements (Prerequisite)\n\n{prerequisite_context['high-level-requirements']}"
        )
    
    # Add project context
    project_context = ""
    if state.get("project_name"):
        project_context += f"Project Name: {state['project_name']}\n"
    if state.get("project_description"):
        project_context += f"Project Description: {state['project_description']}\n"
    
    # Combine into enriched prompt
    enriched_prompt = f"""
You are generating a Business Case document for a software project.

{project_context}

## Available Context

{"".join(context_sections) if context_sections else "No prerequisite documents provided."}

## User Request

{user_prompt}

## Instructions

Generate a comprehensive Business Case document following industry standards (BABOK, PMBOK).
Include sections: Executive Summary, Problem Statement, Proposed Solution, Cost-Benefit Analysis, Risk Assessment, Recommendation.

Use the prerequisite context above to ensure consistency and traceability.
"""
    
    return {"enriched_prompt": enriched_prompt}
```

### 5.3 LLM Generation Node

```python
# workflows/business_case_workflow/nodes.py (continued)

import time
from openai import AsyncOpenAI

async def generate_with_llm(state: BusinessCaseState) -> Dict:
    """
    Call LLM API to generate document content.
    """
    
    client = AsyncOpenAI()  # Uses OPENAI_API_KEY from env
    
    start_time = time.time()
    
    response = await client.chat.completions.create(
        model="gpt-4o",  # or from config
        messages=[
            {"role": "system", "content": "You are an expert business analyst."},
            {"role": "user", "content": state["enriched_prompt"]}
        ],
        temperature=0.7,
        max_tokens=4000
    )
    
    duration = time.time() - start_time
    
    return {
        "llm_response": response.choices[0].message.content,
        "model_used": response.model,
        "tokens_used": response.usage.total_tokens,
        "duration": duration
    }
```

### 5.4 Post-Processing Node

```python
# workflows/business_case_workflow/nodes.py (continued)

def post_process(state: BusinessCaseState) -> Dict:
    """
    Clean up and format the generated content.
    """
    
    content = state["llm_response"]
    
    # Remove any unwanted artifacts
    content = content.strip()
    
    # Ensure proper markdown formatting
    if not content.startswith("#"):
        content = "# Business Case\n\n" + content
    
    return {"final_content": content}
```

### 5.5 LangGraph Definition

```python
# workflows/business_case_workflow/graph.py

from langgraph.graph import StateGraph, END
from .state import BusinessCaseState
from .nodes import prepare_context, generate_with_llm, post_process

def create_business_case_graph():
    """Create the LangGraph workflow for business case generation."""
    
    workflow = StateGraph(BusinessCaseState)
    
    # Add nodes
    workflow.add_node("prepare_context", prepare_context)
    workflow.add_node("generate_llm", generate_with_llm)
    workflow.add_node("post_process", post_process)
    
    # Define edges
    workflow.set_entry_point("prepare_context")
    workflow.add_edge("prepare_context", "generate_llm")
    workflow.add_edge("generate_llm", "post_process")
    workflow.add_edge("post_process", END)
    
    return workflow.compile()

# Export compiled graph
business_case_graph = create_business_case_graph()
```

### 5.6 Workflow Entrypoint

```python
# workflows/business_case_workflow/__init__.py

from .graph import business_case_graph
from .state import BusinessCaseState
from typing import Dict, List, Optional

async def generate_business_case(
    user_prompt: str,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    project_description: Optional[str] = None,
    prerequisite_context: Optional[Dict[str, str]] = None,
    chat_history_id: Optional[str] = None,
    storage_paths: Optional[List[str]] = None
) -> Dict:
    """
    Generate a business case document using LangGraph workflow.
    
    Args:
        user_prompt: User's generation request
        project_id: Project UUID
        project_name: Name of the project
        project_description: Project overview
        prerequisite_context: Dict of prerequisite documents (from Backend)
        chat_history_id: UUID for conversation context
        storage_paths: Files in Supabase Storage
    
    Returns:
        Dict with 'content', 'model', 'tokens', 'duration'
    """
    
    # Prepare initial state
    initial_state: BusinessCaseState = {
        "user_prompt": user_prompt,
        "project_id": project_id,
        "project_name": project_name,
        "project_description": project_description,
        "prerequisite_context": prerequisite_context or {},
        "chat_history": [],  # TODO: Fetch from DB using chat_history_id
        "file_contents": [],  # TODO: Fetch from storage_paths
        "enriched_prompt": "",
        "llm_response": "",
        "final_content": "",
        "model_used": "",
        "tokens_used": 0,
        "duration": 0.0
    }
    
    # Run workflow
    result = await business_case_graph.ainvoke(initial_state)
    
    # Return structured result
    return {
        "content": result["final_content"],
        "model": result["model_used"],
        "tokens": result["tokens_used"],
        "duration": result["duration"]
    }
```

---

## 6. Environment Configuration

### 6.1 Required Environment Variables

```bash
# .env

# ============================================================================
# LLM Provider API Keys
# ============================================================================
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Default model to use
DEFAULT_MODEL=claude-3-7-sonnet-20250219  # or gpt-4o

# ============================================================================
# Service Configuration
# ============================================================================
# Port for AI service
PORT=8001

# Enable debug logging
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR

# ============================================================================
# NO CONSTRAINT ENFORCEMENT VARIABLES
# ============================================================================
# The AI service does NOT need:
# - CONSTRAINT_ENFORCEMENT_MODE
# - MIN_PREREQUISITE_CONTENT_LENGTH
# - Database connection strings (Backend handles DB)
# - Supabase credentials (Backend provides file contents)
```

### 6.2 Configuration Class

```python
# config.py (or in main.py)

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """AI Service configuration."""
    
    # LLM API Keys
    openai_api_key: str
    anthropic_api_key: str
    
    # Model settings
    default_model: str = "claude-3-7-sonnet-20250219"
    temperature: float = 0.7
    max_tokens: int = 4000
    
    # Service settings
    port: int = 8001
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 7. Testing Strategy

### 7.1 Unit Tests for Workflows

```python
# tests/test_business_case_workflow.py

import pytest
from workflows.business_case_workflow import generate_business_case

@pytest.mark.asyncio
async def test_generate_with_context():
    """Test generation with prerequisite context."""
    
    result = await generate_business_case(
        user_prompt="Create a business case for an e-commerce platform",
        project_name="E-Commerce Platform",
        project_description="Modern web-based shopping solution",
        prerequisite_context={
            "stakeholder-register": "# Stakeholder Register\n\n- Customer\n- Admin\n- Vendor",
            "high-level-requirements": "# Requirements\n\n- User authentication\n- Product catalog"
        }
    )
    
    assert result["content"] is not None
    assert "# Business Case" in result["content"]
    assert result["tokens"] > 0
    assert result["duration"] > 0

@pytest.mark.asyncio
async def test_generate_without_context():
    """Test generation without prerequisite context (entry point)."""
    
    result = await generate_business_case(
        user_prompt="Create a business case for a mobile app",
        prerequisite_context={}
    )
    
    assert result["content"] is not None
    assert "# Business Case" in result["content"]
```

### 7.2 Integration Tests

```python
# tests/test_api_endpoints.py

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_generate_business_case_endpoint():
    """Test business case generation endpoint."""
    
    response = client.post(
        "/api/ai/generate/business-case",
        json={
            "message": "Generate a business case",
            "project_name": "Test Project",
            "context": {
                "stakeholder-register": "# Stakeholders\n\n- User\n- Admin"
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["content"] is not None
    assert "business-case" in data["metadata"]["prerequisites_used"]

def test_generate_entry_point_document():
    """Test entry point document (no prerequisites)."""
    
    response = client.post(
        "/api/ai/generate/stakeholder-register",
        json={
            "message": "Create stakeholder register for CRM system",
            "context": {}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
```

---

## 8. Deployment

### 8.1 Docker Configuration

```dockerfile
# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 8.2 Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  ai-service:
    build: .
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DEFAULT_MODEL=claude-3-7-sonnet-20250219
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

---

## 9. Best Practices

### 9.1 Context Utilization

✅ **DO**:
- Always use prerequisite context when provided
- Include prerequisite context in LLM prompts
- Log which prerequisites were used in metadata
- Handle missing context gracefully (empty dict)

❌ **DON'T**:
- Validate whether context should exist (Backend's job)
- Query database directly for prerequisites
- Implement constraint checking logic
- Block generation if context is empty

### 9.2 Error Handling

```python
try:
    result = await generate_business_case(...)
    return AIResponse(success=True, content=result["content"], ...)
except OpenAIError as e:
    return AIResponse(
        success=False,
        error="LLM API error",
        details=str(e)
    )
except Exception as e:
    return AIResponse(
        success=False,
        error="Unexpected error",
        details=str(e)
    )
```

### 9.3 Logging

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/api/ai/generate/business-case")
async def generate_business_case_endpoint(request: AIRequest):
    logger.info(f"Generating business-case for project {request.project_id}")
    logger.debug(f"Prerequisites provided: {list(request.context.keys())}")
    
    result = await generate_business_case(...)
    
    logger.info(f"Generated {len(result['content'])} chars in {result['duration']}s")
    return AIResponse(...)
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty responses | LLM API key missing | Check `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` |
| Poor quality output | Context not used in prompt | Verify `prepare_context` node includes prerequisites |
| Slow generation | Large context size | Consider truncating very long prerequisite docs |
| Rate limit errors | Too many concurrent requests | Implement request throttling |

### 10.2 Debug Mode

```python
# In main.py

import logging

if settings.log_level == "DEBUG":
    logging.basicConfig(level=logging.DEBUG)
    
    @app.middleware("http")
    async def log_requests(request, call_next):
        logger.debug(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.debug(f"Response: {response.status_code}")
        return response
```

---

**Document End**
