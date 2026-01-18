from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import Depends
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.user import User

# Define the dependencies between various project documents.
DOCUMENT_DEPENDENCIES = {
    "stakeholder-register": {
        "required": [],
        "recommended": [],
    },
    "high-level-requirements": {
        "required": [],
        "recommended": ["stakeholder-register"],
    },
    "requirements-management-plan": {
        "required": [],
        "recommended": ["stakeholder-register", "high-level-requirements"],
    },
    "business-case": {
        "required": [],
        "recommended": ["stakeholder-register", "high-level-requirements"],
    },
    "scope-statement": {
        "required": ["business-case", "high-level-requirements"],
        "recommended": ["stakeholder-register"],
    },
    "product-roadmap": {
        "required": ["scope-statement", "high-level-requirements"],
        "recommended": ["business-case"],
    },
    "feasibility-study": {
        "required": ["business-case", "scope-statement", "high-level-requirements"],
        "recommended": ["product-roadmap"],
    },
    "cost-benefit-analysis": {
        "required": ["business-case", "feasibility-study", "scope-statement"],
        "recommended": ["product-roadmap"],
    },
    "risk-register": {
        "required": ["feasibility-study", "scope-statement"],
        "recommended": ["cost-benefit-analysis", "stakeholder-register"],
    },
    "compliance": {
        "required": ["scope-statement", "high-level-requirements"],
        "recommended": ["risk-register"],
    },
    "srs": {
        "required": ["high-level-requirements", "scope-statement", "feasibility-study"],
        "recommended": ["compliance", "stakeholder-register"],
    },
    "hld-arch": {
        "required": ["srs", "feasibility-study", "high-level-requirements"],
        "recommended": [],
    },
    "hld-cloud": {
        "required": ["hld-arch", "srs"],
        "recommended": ["cost-benefit-analysis"],
    },
    "hld-tech": {"required": ["hld-arch", "srs"], "recommended": ["feasibility-study"]},
    "lld-arch": {"required": ["hld-arch", "srs", "hld-tech"], "recommended": []},
    "lld-db": {"required": ["srs", "lld-arch"], "recommended": ["hld-tech"]},
    "lld-api": {"required": ["srs", "lld-arch", "lld-db"], "recommended": ["hld-tech"]},
    "lld-pseudo": {"required": ["srs"], "recommended": ["lld-api", "lld-db"]},
    "uiux-wireframe": {
        "required": ["srs", "high-level-requirements"],
        "recommended": ["stakeholder-register"],
    },
    "uiux-mockup": {"required": ["uiux-wireframe", "srs"], "recommended": []},
    "uiux-prototype": {
        "required": ["uiux-mockup", "uiux-wireframe"],
        "recommended": ["lld-api"],
    },
    "rtm": {
        "required": ["srs", "high-level-requirements"],
        "recommended": ["lld-arch", "lld-db", "lld-api", "uiux-wireframe"],
    },
}


# Validate that the required and recommended documents are present for a given document type.
def validate_dependencies(
    project_id: int,
    document_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deps = DOCUMENT_DEPENDENCIES.get(document_type, {})
    sql_query = """
    SELECT DISTINCT(file_type) FROM files
    WHERE project_id = :project_id 
    AND updated_by = :user_id
    AND status != 'deleted'
    """

    result = db.execute(
        text(sql_query), {"project_id": project_id, "user_id": current_user.id}
    ).fetchall()

    existing_file_types = [r[0] for r in result]

    missing_required = [
        d for d in deps.get("required", []) if d not in existing_file_types
    ]

    missing_recommended = [
        d for d in deps.get("recommended", []) if d not in existing_file_types
    ]

    return {
        "can_proceed": len(missing_required) == 0,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
    }
