"""Azure AI Search 클라이언트 관리

Azure AI Search 클라이언트의 초기화와 생명주기를 관리합니다.
싱글톤 패턴을 사용하여 전역적으로 하나의 클라이언트 인스턴스를 유지합니다.
"""

from __future__ import annotations

from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from ...utils.config import get_config
from ...utils.logger import get_logger

logger = get_logger(__name__)


class SearchClientManager:
    """Azure AI Search 클라이언트 관리자 (싱글톤)
    
    클라이언트 초기화 및 접근을 중앙에서 관리합니다.
    """

    _instance: SearchClientManager | None = None
    _clients: dict[str, Any] = {}  # SearchClient 또는 Mock 가능

    def __new__(cls) -> SearchClientManager:
        """싱글톤 인스턴스 생성"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(
        self, indexes: dict[str, dict[str, str]] | None = None
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
            >>> manager = SearchClientManager()
            >>> manager.initialize()  # config.py 설정 사용
            
            >>> manager.initialize({
            ...     "cosmetic-raw-materials": {
            ...         "endpoint": "https://my-search.search.windows.net",
            ...         "api_key": "...",
            ...     }
            ... })
        
        Raises:
            ValueError: 필수 설정이 없는 경우
        """
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

        # 클라이언트 생성
        for index_name, config in indexes.items():
            endpoint = config.get("endpoint")
            api_key = config.get("api_key")

            if not endpoint or not api_key:
                raise ValueError(
                    f"인덱스 '{index_name}'의 endpoint와 api_key가 필요합니다"
                )

            self._clients[index_name] = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=AzureKeyCredential(api_key),
            )

        logger.info(f"Azure AI Search 클라이언트 초기화 완료: {list(indexes.keys())}")

    def get_client(self, index_name: str) -> Any:
        """인덱스 이름으로 클라이언트를 가져옵니다.
        
        Args:
            index_name: 인덱스 이름
            
        Returns:
            SearchClient 또는 None (초기화되지 않은 경우)
            
        Examples:
            >>> manager = SearchClientManager()
            >>> manager.initialize()
            >>> client = manager.get_client("cosmetic-raw-materials")
        """
        return self._clients.get(index_name)

    def has_client(self, index_name: str) -> bool:
        """인덱스가 초기화되었는지 확인합니다.
        
        Args:
            index_name: 인덱스 이름
            
        Returns:
            초기화 여부
        """
        return index_name in self._clients

    def clear(self) -> None:
        """모든 클라이언트를 제거합니다. (테스트용)"""
        self._clients.clear()
        logger.info("모든 Search 클라이언트 제거됨")


def get_search_client_manager() -> SearchClientManager:
    """SearchClientManager 싱글톤 인스턴스를 반환합니다.
    
    Returns:
        SearchClientManager 인스턴스
        
    Examples:
        >>> manager = get_search_client_manager()
        >>> manager.initialize()
        >>> client = manager.get_client("cosmetic-raw-materials")
    """
    return SearchClientManager()
