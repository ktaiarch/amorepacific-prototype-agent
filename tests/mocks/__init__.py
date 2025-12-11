"""테스트용 Mock Search Client

테스트에서 실제 Azure AI Search 없이 동작할 수 있도록 Mock 구현을 제공합니다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MockSearchClient:
    """테스트용 Mock Azure AI Search 클라이언트
    
    실제 Azure AI Search와 동일한 인터페이스를 제공하지만,
    data/cosmetic_raw_materials.json 파일에서 Mock 데이터를 로드합니다.
    """

    def __init__(self, index_name: str):
        """Mock 클라이언트 초기화
        
        Args:
            index_name: 인덱스 이름
        """
        self.index_name = index_name
        self._mock_data = self._load_mock_data()

    def _load_mock_data(self) -> list[dict[str, Any]]:
        """Mock 데이터를 JSON 파일에서 로드합니다.
        
        Returns:
            Mock 데이터 리스트
        """
        if self.index_name not in ("raw-materials", "cosmetic-raw-materials"):
            return []
        
        # JSON 파일 경로 찾기 (tests/mocks에서 프로젝트 루트로)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        json_path = project_root / "data" / "cosmetic_raw_materials.json"
        
        if not json_path.exists():
            return []
        
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            
            # 검색 score 추가
            for i, item in enumerate(data):
                item["@search.score"] = 10.0 - (i * 0.1)
            
            return data
        except Exception:
            return []

    def search(
        self,
        search_text: str,
        top: int = 10,
        filter: str | None = None,
        select: list[str] | None = None,
        **kwargs: Any,
    ):
        """Mock 검색 실행
        
        Args:
            search_text: 검색 쿼리
            top: 최대 결과 수
            filter: OData 필터 표현식
            select: 반환할 필드 목록
            **kwargs: 기타 옵션
        
        Yields:
            검색 결과 문서
        """
        results = []

        # 텍스트 매칭
        for doc in self._mock_data:
            if search_text.lower() in doc.get("korean_name", "").lower():
                results.append(doc)
            elif search_text.lower() in doc.get("english_name", "").lower():
                results.append(doc)

        # 필터 적용
        if filter:
            filtered = []
            for doc in results:
                if self._match_filter(doc, filter):
                    filtered.append(doc)
            results = filtered

        # 정렬 (score 기준)
        results.sort(key=lambda x: x.get("@search.score", 0), reverse=True)

        # Top-K
        results = results[:top]

        # Select 필드 적용
        if select:
            results = [
                {k: doc.get(k) for k in select + ["@search.score"]} 
                for doc in results
            ]

        return iter(results)

    def _match_filter(self, doc: dict[str, Any], filter_expr: str) -> bool:
        """간단한 OData 필터 매칭
        
        Args:
            doc: 문서
            filter_expr: 필터 표현식
            
        Returns:
            매칭 여부
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
