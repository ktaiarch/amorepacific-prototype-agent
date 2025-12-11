"""Azure AI Search 연동 Tool 함수들

Azure AI Search를 사용하여 문서를 검색하는 도구 함수들을 제공합니다.
"""

from __future__ import annotations

from typing import Annotated

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from pydantic import Field

from .models import SearchDocument, SearchResult
from ...utils.config import get_config
from ...utils.logger import get_logger

logger = get_logger(__name__)

# 전역 클라이언트 저장소
_search_clients: dict[str, SearchClient] = {}


def initialize_search_clients(
    indexes: dict[str, dict[str, str]] | None = None,
) -> None:
    """Azure AI Search 클라이언트 초기화
    
    indexes 파라미터가 없으면 config.py의 설정을 자동으로 사용합니다.
    
    Args:
        indexes: 인덱스별 설정 (선택사항)
            {
                "cosmetic-raw-materials": {
                    "endpoint": "https://...",
                    "api_key": "...",
                }
            }
            None인 경우 config.py의 Azure Search 설정 사용
            
    Examples:
        >>> # 실제 Azure AI Search 사용 (config.py 설정)
        >>> initialize_search_clients()
        
        >>> # 실제 Azure AI Search 사용 (직접 설정)
        >>> initialize_search_clients({
        ...     "cosmetic-raw-materials": {
        ...         "endpoint": "https://my-search.search.windows.net",
        ...         "api_key": "...",
        ...     }
        ... })
    """
    global _search_clients

    # indexes 파라미터가 없으면 config.py에서 설정 로드
    if not indexes:
        config = get_config()
        search_settings = config.azure_search

        if not search_settings.endpoint or not search_settings.api_key:
            raise ValueError(
                "Azure AI Search 설정이 필요합니다. "
                "환경변수 AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY를 설정하세요."
            )

        # config.py 설정으로 인덱스 생성
        index_name = search_settings.index_name or "cosmetic-raw-materials"
        indexes = {
            index_name: {
                "endpoint": search_settings.endpoint,
                "api_key": search_settings.api_key,
            }
        }

    for index_name, config in indexes.items():
        endpoint = config.get("endpoint")
        api_key = config.get("api_key")

        if not endpoint or not api_key:
            raise ValueError(f"인덱스 '{index_name}'의 endpoint와 api_key가 필요합니다")

        _search_clients[index_name] = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(api_key),
        )

    logger.info(f"Azure AI Search 클라이언트 초기화 완료: {list(indexes.keys())}")



def search_documents(
    query: Annotated[str, Field(description="검색 쿼리 텍스트")],
    index_name: Annotated[
        str, Field(description="검색할 인덱스 이름 (예: cosmetic-raw-materials)")
    ] = "cosmetic-raw-materials",
    top_k: Annotated[int, Field(description="반환할 최대 결과 수")] = 10,
) -> str:
    """Azure AI Search에서 문서를 검색합니다.
    
    Hybrid Search (키워드 + 시맨틱)를 적용하여 관련도 순으로 정렬합니다.
    
    Args:
        query: 검색 쿼리
        index_name: 인덱스 이름
        top_k: 최대 결과 수
    
    Returns:
        검색 결과 (JSON 문자열)
        {
            "documents": [
                {
                    "id": "RM001",
                    "korean_name": "세테아릴 알코올",
                    "english_name": "Cetearyl Alcohol",
                    "cas_no": "67762-27-0",
                    "order_status": "발주완료",
                    "score": 5.2
                },
                ...
            ],
            "count": 2
        }
    
    Examples:
        >>> result = search_documents("Cetearyl alcohol", "cosmetic-raw-materials", 5)
        >>> print(result)
        {"documents": [...], "count": 2}
    """
    client = _search_clients.get(index_name)
    if not client:
        error_msg = f"Index '{index_name}' not initialized. Call initialize_search_clients() first."
        logger.error(error_msg)
        result = SearchResult(documents=[], count=0, error=error_msg)
        return result.model_dump_json(exclude_none=True)

    try:
        results = client.search(
            search_text=query,
            top=top_k,
            select=[
                "id",
                "korean_name",
                "english_name",
                "cas_no",
                "order_status",
            ],
        )

        documents = []
        for result in results:
            doc = SearchDocument(
                id=result.get("id") or "",
                korean_name=result.get("korean_name"),
                english_name=result.get("english_name"),
                cas_no=result.get("cas_no"),
                order_status=result.get("order_status"),
                score=result.get("@search.score"),
            )
            documents.append(doc)

        logger.info(f"검색 완료: query='{query}', results={len(documents)}")
        search_result = SearchResult(documents=documents, count=len(documents))
        return search_result.model_dump_json(exclude_none=True)

    except Exception as e:
        logger.error(f"검색 중 오류 발생: {e}", exc_info=True)
        result = SearchResult(documents=[], count=0, error=str(e))
        return result.model_dump_json(exclude_none=True)


def search_with_filter(
    query: Annotated[str, Field(description="검색 쿼리 텍스트")],
    index_name: Annotated[
        str, Field(description="검색할 인덱스 이름")
    ] = "cosmetic-raw-materials",
    filter_expr: Annotated[
        str, Field(description="OData 필터 표현식 (예: order_status eq '발주완료')")
    ] = "",
    top_k: Annotated[int, Field(description="반환할 최대 결과 수")] = 10,
) -> str:
    """필터를 적용하여 Azure AI Search에서 문서를 검색합니다.
    
    OData 필터 표현식을 사용하여 검색 결과를 필터링합니다.
    
    Args:
        query: 검색 쿼리
        index_name: 인덱스 이름
        filter_expr: OData 필터 표현식
        top_k: 최대 결과 수
    
    Returns:
        검색 결과 (JSON 문자열)
    
    Examples:
        >>> result = search_with_filter(
        ...     "Cetearyl alcohol",
        ...     "cosmetic-raw-materials",
        ...     "order_status eq '발주완료'",
        ...     5
        ... )
        >>> print(result)
        {"documents": [...], "count": 1}
    """
    client = _search_clients.get(index_name)
    if not client:
        error_msg = f"Index '{index_name}' not initialized. Call initialize_search_clients() first."
        logger.error(error_msg)
        result = SearchResult(documents=[], count=0, error=error_msg)
        return result.model_dump_json(exclude_none=True)

    try:
        results = client.search(
            search_text=query,
            filter=filter_expr if filter_expr else None,
            top=top_k,
            select=[
                "id",
                "korean_name",
                "english_name",
                "cas_no",
                "order_status",
            ],
        )

        documents = []
        for result in results:
            doc = SearchDocument(
                id=result.get("id") or "",
                korean_name=result.get("korean_name"),
                english_name=result.get("english_name"),
                cas_no=result.get("cas_no"),
                order_status=result.get("order_status"),
                score=result.get("@search.score"),
            )
            documents.append(doc)

        logger.info(
            f"필터 검색 완료: query='{query}', filter='{filter_expr}', results={len(documents)}"
        )
        search_result = SearchResult(documents=documents, count=len(documents))
        return search_result.model_dump_json(exclude_none=True)

    except Exception as e:
        logger.error(f"필터 검색 중 오류 발생: {e}", exc_info=True)
        result = SearchResult(documents=[], count=0, error=str(e))
        return result.model_dump_json(exclude_none=True)
