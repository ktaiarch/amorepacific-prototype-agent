"""Worker Tools 테스트

search_documents, search_with_filter 함수들의 동작을 검증합니다.
"""

import json

import pytest

from src.workers.tools import get_search_client_manager, search_documents, search_with_filter
from tests.mocks import MockSearchClient


@pytest.fixture(autouse=True)
def setup_mock_search():
    """테스트용 Mock Search 클라이언트 초기화"""
    manager = get_search_client_manager()
    
    # Mock 클라이언트로 수동 초기화
    manager._clients["cosmetic-raw-materials"] = MockSearchClient("cosmetic-raw-materials")
    
    yield
    
    # 정리
    manager.clear()


class TestSearchDocuments:
    """search_documents 함수 테스트"""

    def test_search_basic(self):
        """기본 검색 동작을 확인합니다."""
        # Act
        result_json = search_documents(query="세테아릴", top_k=10)
        result = json.loads(result_json)

        # Assert
        assert "documents" in result
        assert "count" in result
        assert result["count"] > 0
        assert len(result["documents"]) > 0

    def test_search_english_query(self):
        """영문 검색어로 검색합니다."""
        # Act
        result_json = search_documents(query="Cetearyl", top_k=10)
        result = json.loads(result_json)

        # Assert
        assert result["count"] > 0
        # 첫 번째 결과에 "Cetearyl"이 포함되어야 함
        first_doc = result["documents"][0]
        assert (
            "Cetearyl" in first_doc.get("english_name", "")
            or "세테아릴" in first_doc.get("korean_name", "")
        )

    def test_search_top_k(self):
        """top_k 파라미터로 결과 수를 제한합니다."""
        # Act
        result_json = search_documents(query="알코올", top_k=2)
        result = json.loads(result_json)

        # Assert
        assert len(result["documents"]) <= 2

    def test_search_no_results(self):
        """검색 결과가 없는 경우를 확인합니다."""
        # Act
        result_json = search_documents(query="존재하지않는원료XYZ123", top_k=10)
        result = json.loads(result_json)

        # Assert
        assert result["count"] == 0
        assert len(result["documents"]) == 0

    def test_search_result_structure(self):
        """검색 결과의 구조를 확인합니다."""
        # Act
        result_json = search_documents(query="글리세린", top_k=10)
        result = json.loads(result_json)

        # Assert
        assert result["count"] > 0
        doc = result["documents"][0]

        # 필수 필드 확인
        assert "id" in doc
        assert "korean_name" in doc
        assert "english_name" in doc
        assert "cas_no" in doc
        assert "order_status" in doc
        assert "score" in doc


class TestSearchWithFilter:
    """search_with_filter 함수 테스트"""

    def test_filter_by_order_status(self):
        """발주 상태로 필터링합니다."""
        # Act
        result_json = search_with_filter(
            query="알코올", filter_expr="order_status eq '발주완료'", top_k=10
        )
        result = json.loads(result_json)

        # Assert
        assert result["count"] > 0
        # 모든 결과가 '발주완료' 상태여야 함
        for doc in result["documents"]:
            assert doc["order_status"] == "발주완료"

    def test_filter_검토중_status(self):
        """'검토중' 상태로 필터링합니다."""
        # Act
        result_json = search_with_filter(
            query="세테아릴", filter_expr="order_status eq '검토중'", top_k=10
        )
        result = json.loads(result_json)

        # Assert
        if result["count"] > 0:
            for doc in result["documents"]:
                assert doc["order_status"] == "검토중"

    def test_filter_empty_expression(self):
        """빈 필터 표현식은 일반 검색과 동일합니다."""
        # Act
        result_json = search_with_filter(query="글리세린", filter_expr="", top_k=10)
        result = json.loads(result_json)

        # Assert
        assert result["count"] > 0

    def test_filter_complex_query(self):
        """복잡한 쿼리와 필터를 조합합니다."""
        # Arrange
        query = "Cetearyl alcohol"
        filter_expr = "order_status eq '발주완료'"

        # Act
        result_json = search_with_filter(query=query, filter_expr=filter_expr, top_k=5)
        result = json.loads(result_json)

        # Assert
        # 1. Cetearyl alcohol을 포함하고
        # 2. 발주완료 상태인 원료만 반환
        for doc in result["documents"]:
            assert doc["order_status"] == "발주완료"
            # 영문 또는 한글명에 검색어 포함
            name_match = (
                "cetearyl" in doc.get("english_name", "").lower()
                or "세테아릴" in doc.get("korean_name", "").lower()
            )
            assert name_match


class TestSearchClientManager:
    """SearchClientManager 클래스 테스트"""

    def test_mock_initialization(self):
        """Mock 클라이언트 초기화를 확인합니다."""
        # Arrange
        manager = get_search_client_manager()
        manager._clients["cosmetic-raw-materials"] = MockSearchClient("cosmetic-raw-materials")

        # Act & Assert - 검색이 동작해야 함
        result_json = search_documents(query="글리세린", top_k=10)
        result = json.loads(result_json)
        assert "error" not in result or result["error"] is None
        
        # 정리
        manager.clear()

    def test_uninitialized_client_error(self):
        """초기화되지 않은 클라이언트 사용 시 에러를 확인합니다."""
        # Arrange - 클라이언트 초기화 없이 검색 시도
        manager = get_search_client_manager()
        manager.clear()

        # Act
        result_json = search_documents(query="테스트", top_k=10)
        result = json.loads(result_json)

        # Assert
        assert "error" in result
        assert result["count"] == 0
        assert "not initialized" in result["error"].lower()
        
        # 정리 - 다시 Mock 클라이언트 설정
        manager._clients["cosmetic-raw-materials"] = MockSearchClient("cosmetic-raw-materials")


class TestMockSearchClient:
    """MockSearchClient 동작 테스트"""

    def test_mock_data_exists(self):
        """Mock 데이터가 존재하는지 확인합니다."""
        # Act
        result_json = search_documents(query="글리세린", top_k=10)
        result = json.loads(result_json)

        # Assert
        assert result["count"] > 0
        # 글리세린이 Mock 데이터에 있어야 함
        found = False
        for doc in result["documents"]:
            if "글리세린" in doc.get("korean_name", ""):
                found = True
                assert doc["cas_no"] == "56-81-5"
                break
        assert found

    def test_mock_score_ordering(self):
        """Mock 검색 결과가 score 순으로 정렬되는지 확인합니다."""
        # Act
        result_json = search_documents(query="세테아릴", top_k=10)
        result = json.loads(result_json)

        # Assert
        if result["count"] > 1:
            scores = [doc["score"] for doc in result["documents"]]
            # score가 내림차순으로 정렬되어야 함
            assert scores == sorted(scores, reverse=True)


class TestRealWorldScenarios:
    """실제 사용 시나리오 테스트"""

    def test_scenario_find_ingredient_by_korean_name(self):
        """한글 원료명으로 검색하는 시나리오"""
        # Act
        result_json = search_documents(query="나이아신아마이드", top_k=5)
        result = json.loads(result_json)

        # Assert
        assert result["count"] > 0
        doc = result["documents"][0]
        assert "나이아신아마이드" in doc["korean_name"]
        assert doc["cas_no"] == "98-92-0"

    def test_scenario_find_available_ingredients(self):
        """발주 가능한 원료만 검색하는 시나리오"""
        # Act
        result_json = search_with_filter(
            query="알코올", filter_expr="order_status eq '발주완료'", top_k=10
        )
        result = json.loads(result_json)

        # Assert
        for doc in result["documents"]:
            assert doc["order_status"] == "발주완료"

    def test_scenario_search_by_cas_number(self):
        """CAS 번호로 원료를 찾는 시나리오 (간접 검색)"""
        # Mock에서는 텍스트 검색만 지원하므로 원료명으로 검색
        # Act
        result_json = search_documents(query="Glycerin", top_k=5)
        result = json.loads(result_json)

        # Assert
        if result["count"] > 0:
            # 글리세린이 검색되면 CAS 번호 확인
            glycerin = next(
                (
                    doc
                    for doc in result["documents"]
                    if "glycerin" in doc.get("ingredient_name_en", "").lower()
                ),
                None,
            )
            if glycerin:
                assert glycerin["cas_no"] == "56-81-5"
