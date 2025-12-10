"""Azure AI Search 연동 Tool 함수들

Mock과 실제 Azure AI Search를 환경변수로 전환 가능하도록 설계했습니다.
"""

from __future__ import annotations

import json
import os
from typing import Annotated, Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from pydantic import Field

from ...utils.config import get_config
from ...utils.logger import get_logger

logger = get_logger(__name__)

# 전역 클라이언트 저장소
_search_clients: dict[str, Any] = {}


class MockSearchClient:
    """프로토타입용 Mock Azure AI Search 클라이언트
    
    실제 Azure AI Search와 동일한 인터페이스를 제공하지만,
    data/cosmetic_raw_materials.json 파일에서 Mock 데이터를 로드합니다.
    """

    def __init__(self, index_name: str):
        self.index_name = index_name
        self._mock_data = self._load_mock_data()
        logger.info(f"MockSearchClient 초기화: {index_name}, 데이터: {len(self._mock_data)}개")

    def _load_mock_data(self) -> list[dict]:
        """Mock 데이터를 JSON 파일에서 로드합니다.
        
        data/cosmetic_raw_materials.json 파일을 읽어서 반환합니다.
        실제 Azure AI Search 스키마와 동일한 필드명을 사용합니다.
        """
        if self.index_name not in ("raw-materials", "cosmetic-raw-materials"):
            return []
        
        # JSON 파일 경로 찾기
        from pathlib import Path
        
        # 프로젝트 루트 찾기 (src/workers/tools에서 3단계 상위)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        json_path = project_root / "data" / "cosmetic_raw_materials.json"
        
        if not json_path.exists():
            logger.warning(f"Mock 데이터 파일을 찾을 수 없습니다: {json_path}")
            return []
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 검색 score 추가 (실제 Azure AI Search와 동일하게)
            for i, item in enumerate(data):
                item["@search.score"] = 10.0 - (i * 0.1)  # 순서대로 감소하는 score
            
            logger.info(f"Mock 데이터 로드 완료: {len(data)}개 원료")
            return data
            
        except Exception as e:
            logger.error(f"Mock 데이터 로드 실패: {e}", exc_info=True)
            return []

    def search(
        self,
        search_text: str,
        top: int = 10,
        filter: str | None = None,
        select: list[str] | None = None,
        **kwargs,
    ):
        """Mock 검색 실행
        
        키워드 매칭으로 간단한 검색을 시뮬레이션합니다.
        
        Args:
            search_text: 검색 쿼리
            top: 최대 결과 수
            filter: OData 필터 표현식
            select: 반환할 필드 목록
            **kwargs: 기타 옵션 (무시)
        
        Yields:
            검색 결과 문서
        """
        results = []

        # 1. 텍스트 매칭
        for doc in self._mock_data:
            if search_text.lower() in doc.get("korean_name", "").lower():
                results.append(doc)
            elif search_text.lower() in doc.get("english_name", "").lower():
                results.append(doc)

        # 2. 필터 적용 (간단한 파싱)
        if filter:
            filtered = []
            for doc in results:
                if self._match_filter(doc, filter):
                    filtered.append(doc)
            results = filtered

        # 3. 정렬 (score 기준)
        results.sort(key=lambda x: x.get("@search.score", 0), reverse=True)

        # 4. Top-K
        results = results[:top]

        # 5. Select 필드 적용
        if select:
            results = [{k: doc.get(k) for k in select + ["@search.score"]} for doc in results]

        logger.info(
            f"Mock 검색 실행: query='{search_text}', filter='{filter}', results={len(results)}"
        )

        return iter(results)

    def _match_filter(self, doc: dict, filter_expr: str) -> bool:
        """간단한 OData 필터 매칭
        
        예: "order_status eq '발주완료'"
        """
        try:
            # "field eq 'value'" 파싱
            if " eq " in filter_expr:
                field, value = filter_expr.split(" eq ")
                field = field.strip()
                value = value.strip().strip("'\"")
                return doc.get(field) == value
        except Exception:
            pass
        return True


def initialize_search_clients(
    indexes: dict[str, dict[str, str]] | None = None,
) -> None:
    """Azure AI Search 클라이언트 초기화
    
    환경변수 USE_MOCK_SEARCH에 따라 Mock 또는 실제 클라이언트를 생성합니다.
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
        >>> # Mock 사용 (기본)
        >>> os.environ["USE_MOCK_SEARCH"] = "true"
        >>> initialize_search_clients()
        
        >>> # 실제 Azure AI Search 사용 (config.py 설정)
        >>> os.environ["USE_MOCK_SEARCH"] = "false"
        >>> initialize_search_clients()
        
        >>> # 실제 Azure AI Search 사용 (직접 설정)
        >>> os.environ["USE_MOCK_SEARCH"] = "false"
        >>> initialize_search_clients({
        ...     "cosmetic-raw-materials": {
        ...         "endpoint": "https://my-search.search.windows.net",
        ...         "api_key": "...",
        ...     }
        ... })
    """
    global _search_clients

    use_mock = os.getenv("USE_MOCK_SEARCH", "true").lower() == "true"

    if use_mock:
        # Mock 클라이언트 생성 (두 인덱스 이름 모두 지원)
        _search_clients["raw-materials"] = MockSearchClient("raw-materials")
        _search_clients["cosmetic-raw-materials"] = MockSearchClient("cosmetic-raw-materials")
        logger.info("Mock Search 클라이언트 초기화 완료")
    else:
        # 실제 Azure AI Search 클라이언트 생성
        
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
        return json.dumps({"error": error_msg, "documents": [], "count": 0})

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
            documents.append(
                {
                    "id": result.get("id"),
                    "korean_name": result.get("korean_name"),
                    "english_name": result.get("english_name"),
                    "cas_no": result.get("cas_no"),
                    "order_status": result.get("order_status"),
                    "score": result.get("@search.score"),
                }
            )

        logger.info(f"검색 완료: query='{query}', results={len(documents)}")
        return json.dumps(
            {"documents": documents, "count": len(documents)}, ensure_ascii=False
        )

    except Exception as e:
        logger.error(f"검색 중 오류 발생: {e}", exc_info=True)
        return json.dumps({"error": str(e), "documents": [], "count": 0})


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
        return json.dumps({"error": error_msg, "documents": [], "count": 0})

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
            documents.append(
                {
                    "id": result.get("id"),
                    "korean_name": result.get("korean_name"),
                    "english_name": result.get("english_name"),
                    "cas_no": result.get("cas_no"),
                    "order_status": result.get("order_status"),
                    "score": result.get("@search.score"),
                }
            )

        logger.info(
            f"필터 검색 완료: query='{query}', filter='{filter_expr}', results={len(documents)}"
        )
        return json.dumps(
            {"documents": documents, "count": len(documents)}, ensure_ascii=False
        )

    except Exception as e:
        logger.error(f"필터 검색 중 오류 발생: {e}", exc_info=True)
        return json.dumps({"error": str(e), "documents": [], "count": 0})
