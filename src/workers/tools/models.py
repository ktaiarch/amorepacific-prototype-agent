"""Worker Tools 데이터 모델"""

from pydantic import BaseModel, ConfigDict


class SearchDocument(BaseModel):
    """검색 결과 문서 모델
    
    Azure AI Search 인덱스의 필드명과 일치하도록 설계되었습니다.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    korean_name: str | None = None
    english_name: str | None = None
    cas_no: str | None = None
    order_status: str | None = None
    score: float | None = None


class SearchResult(BaseModel):
    """검색 결과 모델"""

    documents: list[SearchDocument]
    count: int
    error: str | None = None
