from pydantic import BaseModel
from typing import List


class SearchResultItem(BaseModel):
    entity_id: str
    entity_type: str
    project_id: int
    title: str
    rank: float


class SearchResponse(BaseModel):
    keyword: str
    total: int
    page: int
    total_pages: int
    results: List[SearchResultItem]
