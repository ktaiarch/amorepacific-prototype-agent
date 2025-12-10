"""Worker Tools 데이터 모델"""

from pydantic import BaseModel, ConfigDict


class SearchDocument(BaseModel):
    """검색 결과 문서 모델"""

    model_config = ConfigDict(extra="allow")

    id: str
    ingredient_name_ko: str | None = None
    ingredient_name_en: str | None = None
    cas_no: str | None = None
    order_status: str | None = None
    score: float | None = None


class SearchResult(BaseModel):
    """검색 결과 모델"""

    documents: list[SearchDocument]
    count: int
    error: str | None = None
