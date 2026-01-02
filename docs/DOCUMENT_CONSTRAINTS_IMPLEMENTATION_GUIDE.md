# Backend Implementation Guide

## BA Copilot - Constraint Enforcement Service

**Version:** 1.0  
**Date:** January 2, 2026  
**Authors:** BA Copilot Team  
**Status:** Active  
**Repository:** ba_copilot_backend  
**Companion Document:** [DOCUMENT_CONSTRAINTS_SPECIFICATION.md](../ba_copilot_ai/docs/DOCUMENT_CONSTRAINTS_SPECIFICATION.md)

---

## 1. Overview

This guide provides implementation details for the **Backend Service** component of the BA Copilot constraint system. The Backend is the **sole and primary enforcer** of all document constraints.

### 1.1 Backend Responsibilities

The Backend Service is responsible for:

✅ **Constraint Enforcement**: Check and enforce prerequisite dependencies  
✅ **Database Queries**: Detect existing documents in the project  
✅ **Metadata Validation**: Extract and validate document metadata  
✅ **Context Preparation**: Gather prerequisite documents for AI generation  
✅ **AI Service Integration**: Forward validated requests to AI Service  
✅ **Error/Warning Responses**: Return structured responses to Frontend

❌ **NOT Responsible For**:

- Document generation (AI Service handles this)
- UI display (Frontend handles this)
- LLM API calls (AI Service handles this)

### 1.2 Architecture Context

```
┌────────────────────────────────────────────────────────────────┐
│                   BACKEND SERVICE ROLE                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   Frontend (Request)                                           │
│         │                                                      │
│         │ POST /api/documents/generate                         │
│         │ {                                                    │
│         │   "doc_type": "hld-arch",                            │
│         │   "project_id": "...",                               │
│         │   "description": "..."                               │
│         │ }                                                    │
│         ▼                                                      │
│   ┌──────────────────┐                                        │
│   │ Backend Service  │                                        │
│   │   (FastAPI)      │                                        │
│   └────────┬─────────┘                                        │
│            │                                                   │
│            │ 1. Check Constraints                             │
│            ├───────────────┐                                  │
│            │               │                                  │
│            │  ┌────────────▼──────────┐                       │
│            │  │ ConstraintService     │                       │
│            │  │                       │                       │
│            │  │ - Load constraint def │                       │
│            │  │ - Query DB for docs   │                       │
│            │  │ - Compare required vs │                       │
│            │  │   available           │                       │
│            │  └────────────┬──────────┘                       │
│            │               │                                  │
│            │◀──────────────┘                                  │
│            │                                                   │
│            │ 2. Has Violations?                               │
│            ├─────YES─────▶ Return 422 Error                   │
│            │              (Frontend shows error)              │
│            │                                                   │
│            │ 3. Has Warnings?                                 │
│            ├─────YES─────▶ Return 200 with warnings           │
│            │              (Frontend shows warning modal)       │
│            │                                                   │
│            │ 4. Fetch Context                                 │
│            ├───────────────┐                                  │
│            │               │                                  │
│            │  ┌────────────▼──────────┐                       │
│            │  │ Database + Storage    │                       │
│            │  │                       │                       │
│            │  │ - Query documents     │                       │
│            │  │ - Get file contents   │                       │
│            │  │ - Build context dict  │                       │
│            │  └────────────┬──────────┘                       │
│            │               │                                  │
│            │◀──────────────┘                                  │
│            │                                                   │
│            │ 5. Call AI Service                               │
│            │ POST /api/ai/generate/{doc_type}                 │
│            │ {                                                │
│            │   "project_id": "...",                           │
│            │   "context": {                                   │
│            │     "feasibility-study": "...",                  │
│            │     "business-case": "..."                       │
│            │   }                                              │
│            │ }                                                │
│            ▼                                                  │
│      AI Service (Generates)                                   │
│            │                                                  │
│            │ 6. Store Result                                  │
│            ▼                                                  │
│      Database + Storage                                       │
│            │                                                  │
│            │ 7. Return Success                                │
│            ▼                                                  │
│      Frontend (Shows result)                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. File Structure

```
ba_copilot_backend/
├── app/
│   ├── core/
│   │   ├── config.py                    # Add constraint config
│   │   └── document_constraints.py      # NEW: Constraint definitions
│   ├── services/
│   │   └── constraint_service.py        # NEW: Constraint enforcement logic
│   ├── utils/
│   │   └── metadata_utils.py            # Add metadata extraction helpers
│   ├── schemas/
│   │   ├── constraint_schemas.py        # NEW: Pydantic models
│   │   └── ai_service_schemas.py        # NEW: AI Service request models
│   └── api/v1/
│       ├── constraints.py               # NEW: Constraint check endpoint
│       ├── documents.py                 # Update with constraint checks
│       └── ai_integration.py            # NEW: AI Service integration
├── tests/
│   ├── test_constraint_service.py       # Unit tests
│   └── test_constraint_integration.py   # Integration tests
└── docs/
    └── DOCUMENT_CONSTRAINTS_IMPLEMENTATION_GUIDE.md  # This file
```

---

## 3. Core Implementation

### 3.1 Constraint Definitions

**File:** `app/core/document_constraints.py`

```python
"""
Document Constraint Definitions

This module defines all 26 document type constraints based on:
- DOCUMENT_CONSTRAINTS_SPECIFICATION.md v1.1
- Industry standards (BABOK, PMBOK, IEEE 830, TOGAF)
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class EnforcementMode(str, Enum):
    """Constraint enforcement levels."""
    STRICT = "STRICT"         # Block if required missing
    GUIDED = "GUIDED"         # Warn but allow
    PERMISSIVE = "PERMISSIVE" # Log only


class DocumentPhase(int, Enum):
    """SDLC phases."""
    PROJECT_INITIATION = 1
    BUSINESS_PLANNING = 2
    FEASIBILITY_RISK = 3
    HIGH_LEVEL_DESIGN = 4
    LOW_LEVEL_DESIGN = 5
    UIUX_DESIGN = 6
    TESTING_QA = 7


@dataclass
class DocumentConstraint:
    """Constraint definition for a document type."""
    doc_type: str
    display_name: str
    phase: DocumentPhase
    required: List[str]      # Hard block if missing
    recommended: List[str]   # Informational - user can upload/generate/skip
    description: str
    category: str


# =============================================================================
# ALL 26 DOCUMENT CONSTRAINTS
# =============================================================================

DOCUMENT_CONSTRAINTS: Dict[str, DocumentConstraint] = {
    # Phase 1: Project Initiation
    "stakeholder-register": DocumentConstraint(
        doc_type="stakeholder-register",
        display_name="Stakeholder Register",
        phase=DocumentPhase.PROJECT_INITIATION,
        required=[],
        recommended=[],
        description="Registry of all project stakeholders",
        category="planning"
    ),
    "high-level-requirements": DocumentConstraint(
        doc_type="high-level-requirements",
        display_name="High-Level Requirements",
        phase=DocumentPhase.PROJECT_INITIATION,
        required=[],
        recommended=["stakeholder-register"],
        description="High-level functional requirements",
        category="planning"
    ),
    "requirements-management-plan": DocumentConstraint(
        doc_type="requirements-management-plan",
        display_name="Requirements Management Plan",
        phase=DocumentPhase.PROJECT_INITIATION,
        required=[],
        recommended=["stakeholder-register", "high-level-requirements"],
        description="Plan for managing requirements",
        category="planning"
    ),

    # Phase 2: Business Planning
    "business-case": DocumentConstraint(
        doc_type="business-case",
        display_name="Business Case",
        phase=DocumentPhase.BUSINESS_PLANNING,
        required=["stakeholder-register"],
        recommended=["high-level-requirements"],
        description="Business justification",
        category="planning"
    ),
    "scope-statement": DocumentConstraint(
        doc_type="scope-statement",
        display_name="Scope Statement",
        phase=DocumentPhase.BUSINESS_PLANNING,
        required=["high-level-requirements"],
        recommended=["stakeholder-register", "business-case"],
        description="Project scope and boundaries",
        category="planning"
    ),
    "product-roadmap": DocumentConstraint(
        doc_type="product-roadmap",
        display_name="Product Roadmap",
        phase=DocumentPhase.BUSINESS_PLANNING,
        required=["scope-statement"],
        recommended=["business-case", "high-level-requirements"],
        description="Feature timeline",
        category="planning"
    ),

    # Phase 3: Feasibility & Risk
    "feasibility-study": DocumentConstraint(
        doc_type="feasibility-study",
        display_name="Feasibility Study",
        phase=DocumentPhase.FEASIBILITY_RISK,
        required=["business-case", "scope-statement"],
        recommended=["high-level-requirements"],
        description="Technical and operational feasibility",
        category="analysis"
    ),
    "cost-benefit-analysis": DocumentConstraint(
        doc_type="cost-benefit-analysis",
        display_name="Cost-Benefit Analysis",
        phase=DocumentPhase.FEASIBILITY_RISK,
        required=["business-case"],
        recommended=["feasibility-study", "scope-statement"],
        description="Financial analysis",
        category="analysis"
    ),
    "risk-register": DocumentConstraint(
        doc_type="risk-register",
        display_name="Risk Register",
        phase=DocumentPhase.FEASIBILITY_RISK,
        required=["scope-statement"],
        recommended=["feasibility-study", "stakeholder-register"],
        description="Risk identification and mitigation",
        category="analysis"
    ),
    "compliance": DocumentConstraint(
        doc_type="compliance",
        display_name="Compliance Document",
        phase=DocumentPhase.FEASIBILITY_RISK,
        required=["scope-statement"],
        recommended=["risk-register", "high-level-requirements"],
        description="Regulatory compliance requirements",
        category="analysis"
    ),

    # Phase 4: High-Level Design
    "hld-arch": DocumentConstraint(
        doc_type="hld-arch",
        display_name="System Architecture (HLD)",
        phase=DocumentPhase.HIGH_LEVEL_DESIGN,
        required=["high-level-requirements", "scope-statement"],
        recommended=["feasibility-study"],
        description="High-level system architecture",
        category="design"
    ),
    "hld-cloud": DocumentConstraint(
        doc_type="hld-cloud",
        display_name="Cloud Infrastructure Design",
        phase=DocumentPhase.HIGH_LEVEL_DESIGN,
        required=["hld-arch"],
        recommended=["feasibility-study", "cost-benefit-analysis"],
        description="Cloud deployment architecture",
        category="design"
    ),
    "hld-tech": DocumentConstraint(
        doc_type="hld-tech",
        display_name="Technology Stack Selection",
        phase=DocumentPhase.HIGH_LEVEL_DESIGN,
        required=["hld-arch"],
        recommended=["cost-benefit-analysis"],
        description="Technology selection and justification",
        category="design"
    ),

    # Phase 5: Low-Level Design
    "lld-arch": DocumentConstraint(
        doc_type="lld-arch",
        display_name="Detailed Architecture (LLD)",
        phase=DocumentPhase.LOW_LEVEL_DESIGN,
        required=["hld-arch"],
        recommended=["hld-tech"],
        description="Component-level architecture",
        category="design"
    ),
    "lld-db": DocumentConstraint(
        doc_type="lld-db",
        display_name="Database Schema Design",
        phase=DocumentPhase.LOW_LEVEL_DESIGN,
        required=["hld-arch", "high-level-requirements"],
        recommended=["lld-arch"],
        description="Database schema and relationships",
        category="design"
    ),
    "lld-api": DocumentConstraint(
        doc_type="lld-api",
        display_name="API Specifications",
        phase=DocumentPhase.LOW_LEVEL_DESIGN,
        required=["hld-arch", "high-level-requirements"],
        recommended=["lld-arch", "lld-db"],
        description="API endpoint specifications",
        category="design"
    ),
    "lld-pseudo": DocumentConstraint(
        doc_type="lld-pseudo",
        display_name="Pseudocode Documentation",
        phase=DocumentPhase.LOW_LEVEL_DESIGN,
        required=["lld-arch"],
        recommended=["lld-api"],
        description="Algorithmic pseudocode",
        category="design"
    ),

    # Phase 6: UI/UX Design
    "uiux-wireframe": DocumentConstraint(
        doc_type="uiux-wireframe",
        display_name="UI/UX Wireframe",
        phase=DocumentPhase.UIUX_DESIGN,
        required=["high-level-requirements"],
        recommended=["scope-statement", "stakeholder-register"],
        description="Low-fidelity wireframes",
        category="design"
    ),
    "uiux-mockup": DocumentConstraint(
        doc_type="uiux-mockup",
        display_name="UI/UX Mockup",
        phase=DocumentPhase.UIUX_DESIGN,
        required=["uiux-wireframe"],
        recommended=["hld-arch"],
        description="High-fidelity visual designs",
        category="design"
    ),
    "uiux-prototype": DocumentConstraint(
        doc_type="uiux-prototype",
        display_name="UI/UX Prototype",
        phase=DocumentPhase.UIUX_DESIGN,
        required=["uiux-mockup"],
        recommended=["uiux-wireframe", "lld-api"],
        description="Interactive prototype",
        category="design"
    ),

    # Phase 7: Testing & QA
    "rtm": DocumentConstraint(
        doc_type="rtm",
        display_name="Requirements Traceability Matrix",
        phase=DocumentPhase.TESTING_QA,
        required=["high-level-requirements", "srs"],
        recommended=["scope-statement"],
        description="Requirements to test cases mapping",
        category="srs"
    ),

    # Synthesis Documents
    "srs": DocumentConstraint(
        doc_type="srs",
        display_name="Software Requirements Specification",
        phase=DocumentPhase.TESTING_QA,
        required=["high-level-requirements", "scope-statement"],
        recommended=["stakeholder-register", "business-case"],
        description="Comprehensive SRS document",
        category="srs"
    ),

    # Diagram Documents
    "class-diagram": DocumentConstraint(
        doc_type="class-diagram",
        display_name="Class Diagram",
        phase=DocumentPhase.TESTING_QA,
        required=["high-level-requirements"],
        recommended=["lld-arch", "lld-db"],
        description="UML class diagram",
        category="diagram"
    ),
    "usecase-diagram": DocumentConstraint(
        doc_type="usecase-diagram",
        display_name="Use Case Diagram",
        phase=DocumentPhase.TESTING_QA,
        required=["high-level-requirements"],
        recommended=["stakeholder-register"],
        description="UML use case diagram",
        category="diagram"
    ),
    "activity-diagram": DocumentConstraint(
        doc_type="activity-diagram",
        display_name="Activity Diagram",
        phase=DocumentPhase.TESTING_QA,
        required=["high-level-requirements"],
        recommended=["scope-statement"],
        description="UML activity diagram",
        category="diagram"
    ),
    "wireframe": DocumentConstraint(
        doc_type="wireframe",
        display_name="Wireframe",
        phase=DocumentPhase.TESTING_QA,
        required=["high-level-requirements"],
        recommended=["uiux-wireframe"],
        description="UI wireframe design",
        category="diagram"
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_constraint(doc_type: str) -> Optional[DocumentConstraint]:
    """Get constraint definition for a document type."""
    return DOCUMENT_CONSTRAINTS.get(doc_type)


def get_required_prerequisites(doc_type: str) -> List[str]:
    """Get required prerequisites for a document type."""
    constraint = get_constraint(doc_type)
    return constraint.required if constraint else []


def get_recommended_prerequisites(doc_type: str) -> List[str]:
    """Get recommended prerequisites for a document type."""
    constraint = get_constraint(doc_type)
    return constraint.recommended if constraint else []


def is_entry_point(doc_type: str) -> bool:
    """Check if document has no required prerequisites."""
    return len(get_required_prerequisites(doc_type)) == 0
```

### 3.2 Pydantic Schemas

**File:** `app/schemas/constraint_schemas.py`

```python
"""Pydantic schemas for constraint checking."""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class EnforcementMode(str, Enum):
    STRICT = "STRICT"
    GUIDED = "GUIDED"
    PERMISSIVE = "PERMISSIVE"


class ConstraintCheckRequest(BaseModel):
    """Request to check constraints for a document type."""
    document_type: str
    project_id: str  # UUID
    user_id: str     # UUID


class ConstraintViolation(BaseModel):
    """Representation of a constraint violation."""
    type: str  # "REQUIRED" or "RECOMMENDED"
    missing_document: str
    display_name: str
    message: str


class ConstraintCheckResponse(BaseModel):
    """Response from constraint check."""
    can_generate: bool
    violations: List[ConstraintViolation] = Field(default_factory=list)
    warnings: List[ConstraintViolation] = Field(default_factory=list)


class AIServiceRequest(BaseModel):
    """Request payload to AI Service."""
    project_id: str
    user_id: str
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    context: dict[str, str] = Field(default_factory=dict)  # Prerequisite documents


class AIServiceResponse(BaseModel):
    """Response from AI Service."""
    success: bool
    content: Optional[str] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None
    details: Optional[str] = None
```

### 3.3 Constraint Service

**File:** `app/services/constraint_service.py`

```python
"""
Constraint Service

This service is the heart of the constraint system. It:
1. Queries database for existing documents
2. Compares required/recommended prerequisites
3. Returns structured violation/warning responses
"""

from typing import List, Tuple
from sqlalchemy.orm import Session
from app.core.document_constraints import (
    get_constraint,
    get_required_prerequisites,
    get_recommended_prerequisites,
    EnforcementMode
)
from app.schemas.constraint_schemas import (
    ConstraintCheckResponse,
    ConstraintViolation
)
from app.models import Document  # Your Document model


class ConstraintService:
    """Service for checking document constraints."""

    def __init__(self, db: Session, enforcement_mode: EnforcementMode = EnforcementMode.GUIDED):
        self.db = db
        self.enforcement_mode = enforcement_mode

    def check_constraints(self, document_type: str, project_id: str) -> ConstraintCheckResponse:
        """
        Check if constraints are satisfied for generating a document.

        Args:
            document_type: Type of document to generate (e.g., "hld-arch")
            project_id: Project UUID

        Returns:
            ConstraintCheckResponse with violations and warnings
        """
        # Get constraint definition
        constraint = get_constraint(document_type)
        if not constraint:
            raise ValueError(f"Unknown document type: {document_type}")

        # Get existing documents in project
        existing_docs = self._get_existing_document_types(project_id)

        # Check required prerequisites
        missing_required = []
        for req in constraint.required:
            if req not in existing_docs:
                req_constraint = get_constraint(req)
                missing_required.append(
                    ConstraintViolation(
                        type="REQUIRED",
                        missing_document=req,
                        display_name=req_constraint.display_name if req_constraint else req,
                        message=f"Required prerequisite missing: {req_constraint.display_name if req_constraint else req}"
                    )
                )

        # Check recommended prerequisites
        missing_recommended = []
        for rec in constraint.recommended:
            if rec not in existing_docs:
                rec_constraint = get_constraint(rec)
                missing_recommended.append(
                    ConstraintViolation(
                        type="RECOMMENDED",
                        missing_document=rec,
                        display_name=rec_constraint.display_name if rec_constraint else rec,
                        message=f"Recommended prerequisite missing: {rec_constraint.display_name if rec_constraint else rec}"
                    )
                )

        # Determine if generation can proceed
        can_generate = True
        if self.enforcement_mode == EnforcementMode.STRICT and missing_required:
            can_generate = False
        elif self.enforcement_mode == EnforcementMode.GUIDED and missing_required:
            can_generate = False

        return ConstraintCheckResponse(
            can_generate=can_generate,
            violations=missing_required,
            warnings=missing_recommended
        )

    def get_prerequisite_context(self, document_type: str, project_id: str) -> dict[str, str]:
        """
        Fetch prerequisite documents from database and return as context dict.

        Args:
            document_type: Document type being generated
            project_id: Project UUID

        Returns:
            Dict mapping document_type -> document_content
        """
        constraint = get_constraint(document_type)
        if not constraint:
            return {}

        # Get all prerequisites (required + recommended)
        all_prerequisites = constraint.required + constraint.recommended

        # Query database for these documents
        context = {}
        for prereq in all_prerequisites:
            doc = self.db.query(Document).filter(
                Document.project_id == project_id,
                Document.document_type == prereq
            ).first()

            if doc and doc.content:
                context[prereq] = doc.content

        return context

    def _get_existing_document_types(self, project_id: str) -> List[str]:
        """
        Query database to get list of document types already generated/uploaded.

        Args:
            project_id: Project UUID

        Returns:
            List of document type strings (e.g., ["stakeholder-register", "business-case"])
        """
        docs = self.db.query(Document.document_type).filter(
            Document.project_id == project_id
        ).distinct().all()

        return [doc.document_type for doc in docs]
```

---

## 4. API Endpoints

### 4.1 Constraint Check Endpoint

**File:** `app/api/v1/constraints.py`

```python
"""
Constraint checking API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.constraint_service import ConstraintService
from app.schemas.constraint_schemas import (
    ConstraintCheckRequest,
    ConstraintCheckResponse
)
from app.core.config import settings

router = APIRouter(prefix="/api/constraints", tags=["constraints"])


@router.post("/check", response_model=ConstraintCheckResponse)
async def check_constraints(
    request: ConstraintCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check if constraints are satisfied for generating a document.

    This endpoint is called by the Frontend BEFORE showing the generate modal.

    Returns:
    - can_generate: True if no violations (or PERMISSIVE mode)
    - violations: List of REQUIRED prerequisites missing (blocks generation)
    - warnings: List of RECOMMENDED prerequisites missing (informational)
    """
    service = ConstraintService(db, enforcement_mode=settings.CONSTRAINT_ENFORCEMENT_MODE)

    result = service.check_constraints(
        document_type=request.document_type,
        project_id=request.project_id
    )

    return result
```

### 4.2 Document Generation Endpoint

**File:** `app/api/v1/documents.py`

```python
"""
Document generation endpoints with constraint enforcement.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.constraint_service import ConstraintService
from app.services.ai_service_client import AIServiceClient
from app.schemas.constraint_schemas import AIServiceRequest, AIServiceResponse
from app.models import Document
from app.core.config import settings
import httpx

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/generate")
async def generate_document(
    document_type: str,
    project_id: str,
    user_id: str,
    description: str,
    db: Session = Depends(get_db)
):
    """
    Generate a document with constraint enforcement.

    Flow:
    1. Check constraints
    2. Block if violations (STRICT/GUIDED mode)
    3. Fetch prerequisite context
    4. Call AI Service
    5. Store result in database
    6. Return success
    """

    # Step 1: Check constraints
    constraint_service = ConstraintService(
        db,
        enforcement_mode=settings.CONSTRAINT_ENFORCEMENT_MODE
    )

    check_result = constraint_service.check_constraints(document_type, project_id)

    # Step 2: Block if violations
    if not check_result.can_generate:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "PREREQUISITE_MISSING",
                "message": f"Cannot generate {document_type}. Required prerequisites are missing.",
                "violations": [v.dict() for v in check_result.violations]
            }
        )

    # Step 3: Fetch prerequisite context
    context = constraint_service.get_prerequisite_context(document_type, project_id)

    # Get project details
    # (Assuming you have a Project model and can fetch project name/description)
    # project = db.query(Project).filter(Project.id == project_id).first()

    # Step 4: Call AI Service
    ai_request = AIServiceRequest(
        project_id=project_id,
        user_id=user_id,
        project_name="Example Project",  # From DB
        project_description=description,
        context=context
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.AI_SERVICE_URL}/api/ai/generate/{document_type}",
            json=ai_request.dict(),
            timeout=60.0
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI Service failed to generate document"
            )

        ai_response = AIServiceResponse(**response.json())

    if not ai_response.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {ai_response.error}"
        )

    # Step 5: Store result in database
    new_document = Document(
        project_id=project_id,
        user_id=user_id,
        document_type=document_type,
        content=ai_response.content,
        metadata=ai_response.metadata
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    # Step 6: Return success
    return {
        "success": True,
        "document_id": new_document.id,
        "content": new_document.content,
        "warnings": [w.dict() for w in check_result.warnings]
    }
```

---

## 5. Environment Configuration

### 5.1 Required Environment Variables

```bash
# .env

# ============================================================================
# Database
# ============================================================================
DATABASE_URL=postgresql://user:password@localhost:5432/ba_copilot

# ============================================================================
# Constraint Enforcement
# ============================================================================
CONSTRAINT_ENFORCEMENT_MODE=GUIDED  # STRICT | GUIDED | PERMISSIVE

# Minimum content length to consider prerequisite valid
MIN_PREREQUISITE_CONTENT_LENGTH=100

# Allow admin override
ALLOW_CONSTRAINT_OVERRIDE=true

# ============================================================================
# AI Service Integration
# ============================================================================
AI_SERVICE_URL=http://localhost:8001

# ============================================================================
# Storage
# ============================================================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
SUPABASE_BUCKET=documents
```

### 5.2 Configuration Class

```python
# app/core/config.py

from pydantic_settings import BaseSettings
from app.core.document_constraints import EnforcementMode


class Settings(BaseSettings):
    # Database
    database_url: str

    # Constraint enforcement
    constraint_enforcement_mode: EnforcementMode = EnforcementMode.GUIDED
    min_prerequisite_content_length: int = 100
    allow_constraint_override: bool = True

    # AI Service
    ai_service_url: str = "http://localhost:8001"

    # Supabase Storage
    supabase_url: str
    supabase_key: str
    supabase_bucket: str = "documents"

    class Config:
        env_file = ".env"


settings = Settings()
```

---

## 6. Testing

### 6.1 Unit Tests

```python
# tests/test_constraint_service.py

import pytest
from app.services.constraint_service import ConstraintService
from app.core.document_constraints import EnforcementMode


def test_entry_point_no_violations(db_session):
    """Entry point documents should have no violations."""
    service = ConstraintService(db_session, EnforcementMode.STRICT)

    result = service.check_constraints("stakeholder-register", "project-123")

    assert result.can_generate is True
    assert len(result.violations) == 0


def test_missing_required_blocks_strict_mode(db_session, create_project):
    """Missing required prerequisite should block in STRICT mode."""
    project_id = create_project()
    service = ConstraintService(db_session, EnforcementMode.STRICT)

    # hld-arch requires high-level-requirements and scope-statement
    result = service.check_constraints("hld-arch", project_id)

    assert result.can_generate is False
    assert len(result.violations) > 0
    assert any(v.missing_document == "high-level-requirements" for v in result.violations)


def test_missing_recommended_warns_only(db_session, create_project, create_document):
    """Missing recommended prerequisite should only warn."""
    project_id = create_project()

    # Create required docs for hld-arch
    create_document(project_id, "high-level-requirements")
    create_document(project_id, "scope-statement")

    service = ConstraintService(db_session, EnforcementMode.GUIDED)

    result = service.check_constraints("hld-arch", project_id)

    assert result.can_generate is True
    assert len(result.violations) == 0
    assert len(result.warnings) > 0  # Missing recommended: feasibility-study


def test_get_prerequisite_context(db_session, create_project, create_document):
    """Should fetch prerequisite documents as context."""
    project_id = create_project()

    # Create prerequisites
    doc1 = create_document(project_id, "stakeholder-register", "# Stakeholders\n\nUser, Admin")
    doc2 = create_document(project_id, "high-level-requirements", "# Requirements\n\nAuth, Catalog")

    service = ConstraintService(db_session)

    context = service.get_prerequisite_context("business-case", project_id)

    assert "stakeholder-register" in context
    assert "high-level-requirements" in context
    assert "Stakeholders" in context["stakeholder-register"]
```

### 6.2 Integration Tests

```python
# tests/test_constraint_integration.py

import pytest
from fastapi.testclient import TestClient


def test_generate_with_missing_required_returns_422(client, auth_headers, create_project):
    """Should return 422 when required prerequisites missing."""
    project_id = create_project()

    response = client.post(
        "/api/documents/generate",
        params={
            "document_type": "hld-arch",
            "project_id": project_id,
            "user_id": "user-123",
            "description": "Test"
        },
        headers=auth_headers
    )

    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["error"] == "PREREQUISITE_MISSING"
    assert len(data["detail"]["violations"]) > 0


def test_generate_entry_point_succeeds(client, auth_headers, create_project):
    """Entry point document should generate without prerequisites."""
    project_id = create_project()

    response = client.post(
        "/api/documents/generate",
        params={
            "document_type": "stakeholder-register",
            "project_id": project_id,
            "user_id": "user-123",
            "description": "Create stakeholder register"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
```

---

## 7. Best Practices

### 7.1 Database Queries

✅ **DO**:

- Use `.distinct()` when querying document types
- Add indexes on `project_id` and `document_type` columns
- Cache constraint definitions (they don't change at runtime)

❌ **DON'T**:

- Query for full document content if only checking existence
- Make separate DB calls for each prerequisite (batch them)

### 7.2 Error Responses

Always return structured error responses:

```python
# Good
raise HTTPException(
    status_code=422,
    detail={
        "error": "PREREQUISITE_MISSING",
        "message": "Cannot generate High-Level Architecture",
        "violations": [
            {
                "type": "REQUIRED",
                "missing_document": "scope-statement",
                "display_name": "Scope Statement",
                "message": "Required prerequisite missing"
            }
        ]
    }
)

# Bad
raise HTTPException(status_code=400, detail="Missing prerequisites")
```

### 7.3 Logging

```python
import logging

logger = logging.getLogger(__name__)

async def generate_document(...):
    logger.info(f"Generating {document_type} for project {project_id}")

    check_result = constraint_service.check_constraints(...)

    if not check_result.can_generate:
        logger.warning(
            f"Constraint violation for {document_type}: {len(check_result.violations)} missing"
        )
        raise HTTPException(...)

    logger.debug(f"Context size: {len(context)} prerequisites")
```

---

## 8. Troubleshooting

| Issue                      | Cause                                       | Solution                                       |
| -------------------------- | ------------------------------------------- | ---------------------------------------------- |
| Constraint always fails    | Document type not in `DOCUMENT_CONSTRAINTS` | Add constraint definition                      |
| Context not passed to AI   | `get_prerequisite_context` not called       | Ensure context is fetched before AI call       |
| Warnings not shown         | Frontend doesn't handle warnings            | Check API response includes `warnings` field   |
| Wrong enforcement behavior | Env var not loaded                          | Verify `CONSTRAINT_ENFORCEMENT_MODE` in `.env` |

---

**Document End**
