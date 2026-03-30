import math
import logging
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.global_search import SearchResponse, SearchResultItem
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=SearchResponse)
def global_search(
    keyword: str = Query(..., min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # Get projects owned by the user
        project_rows = db.execute(
            text("""
                SELECT id from projects WHERE user_id = :user_id
            """),
            {"user_id": current_user.id},
        ).fetchall()
        project_ids = [row.id for row in project_rows]
        if not project_ids:
            return SearchResponse(
                keyword=keyword, total=0, page=page, total_pages=0, results=[]
            )
        offset = (page - 1) * limit

        # Use raw SQL for efficient full-text search with pagination
        search_query = text("""
            SELECT 
                entity_id, 
                entity_type, 
                project_id,
                title, 
                ts_rank(search_vector, websearch_to_tsquery('english', :keyword)) AS rank,
                COUNT(*) OVER() AS total_count
            FROM 
                global_search_index
            WHERE 
                search_vector @@ websearch_to_tsquery('english', :keyword)
                AND project_id = ANY(:project_ids)
            ORDER BY 
                rank DESC
            LIMIT :limit OFFSET :offset
        """)

        search_results = db.execute(
            search_query,
            {
                "keyword": keyword,
                "project_ids": project_ids,
                "limit": limit,
                "offset": offset,
            },
        ).fetchall()
        total_records = search_results[0].total_count if search_results else 0
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        results = [
            SearchResultItem(
                entity_id=row.entity_id,
                entity_type=row.entity_type,
                project_id=row.project_id,
                title=row.title,
                rank=round(row.rank, 4),
            )
            for row in search_results
        ]

        return SearchResponse(
            keyword=keyword,
            total=total_records,
            page=page,
            total_pages=total_pages,
            results=results,
        )

    except Exception as e:
        logger.error(f"Error fetching user projects: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
