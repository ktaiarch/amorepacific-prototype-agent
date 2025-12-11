"""IngredientWorker 테스트

원료 검색 Worker의 동작을 검증합니다.
"""

import os

import pytest

from src.workers.ingredient import INGREDIENT_INSTRUCTIONS, IngredientWorker
from src.workers.tools import initialize_search_clients


@pytest.fixture(autouse=True)
def setup_search_tools():
    """모든 테스트에서 Mock Search 클라이언트 자동 초기화"""
    os.environ["USE_MOCK_SEARCH"] = "true"
    initialize_search_clients()
    yield
    os.environ.pop("USE_MOCK_SEARCH", None)


@pytest.fixture
def ingredient_worker():
    """테스트용 IngredientWorker 생성"""
    # NOTE: BaseWorker의 _run_agent()가 Mock이므로
    # chat_client는 None으로 전달 가능
    from src.workers.tools import search_documents, search_with_filter

    tools = [search_documents, search_with_filter]
    return IngredientWorker(chat_client=None, tools=tools)


class TestIngredientWorkerInit:
    """IngredientWorker 초기화 테스트"""

    def test_init_with_tools(self):
        """Tool과 함께 초기화를 확인합니다."""
        # Arrange
        from src.workers.tools import search_documents, search_with_filter

        tools = [search_documents, search_with_filter]

        # Act
        worker = IngredientWorker(chat_client=None, tools=tools)

        # Assert
        assert worker is not None
        assert worker.instructions == INGREDIENT_INSTRUCTIONS
        assert len(worker.tools) == 2

    def test_init_creates_agent(self):
        """ChatAgent가 생성되는지 확인합니다."""
        # Arrange & Act
        worker = IngredientWorker(chat_client=None, tools=[])

        # Assert
        # chat_client가 None이면 테스트 모드 (agent도 None)
        assert worker.agent is None
        assert worker.chat_client is None

    def test_instructions_content(self):
        """시스템 프롬프트 내용을 확인합니다."""
        # Assert
        assert "화장품 원료 검색 전문 에이전트" in INGREDIENT_INSTRUCTIONS
        assert "search_documents" in INGREDIENT_INSTRUCTIONS
        assert "search_with_filter" in INGREDIENT_INSTRUCTIONS
        assert "원료코드" in INGREDIENT_INSTRUCTIONS
        assert "CAS 번호" in INGREDIENT_INSTRUCTIONS


class TestIngredientWorkerProcess:
    """IngredientWorker.process() 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_process_basic(self, ingredient_worker):
        """기본 검색 동작을 확인합니다."""
        # Act
        result = await ingredient_worker.process("글리세린 원료 찾아줘")

        # Assert
        assert "content" in result
        assert "sources" in result
        assert "timestamp" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_process_result_structure(self, ingredient_worker):
        """반환 결과의 구조를 확인합니다."""
        # Act
        result = await ingredient_worker.process("나이아신아마이드")

        # Assert
        assert isinstance(result["content"], str)
        assert isinstance(result["sources"], list)
        assert "iterations" in result["metadata"]
        assert "tools_used" in result["metadata"]
        assert result["metadata"]["worker_type"] == "ingredient"

    @pytest.mark.asyncio
    async def test_process_with_context(self, ingredient_worker):
        """컨텍스트를 포함한 검색을 확인합니다."""
        # Arrange
        context = [
            {"role": "user", "content": "글리세린에 대해 알려줘"},
            {"role": "assistant", "content": "글리세린은..."},
        ]

        # Act
        result = await ingredient_worker.process("CAS 번호는?", context=context)

        # Assert
        assert "content" in result
        # Context는 전달되지만 Mock이므로 실제 사용되지 않음

    @pytest.mark.asyncio
    async def test_process_timestamp(self, ingredient_worker):
        """응답 시각이 포함되는지 확인합니다."""
        # Act
        result = await ingredient_worker.process("테스트")

        # Assert
        assert result["timestamp"] is not None
        # timestamp는 datetime 객체


class TestIngredientWorkerSourceExtraction:
    """IngredientWorker의 출처 추출 테스트"""

    def test_extract_sources_from_result(self, ingredient_worker):
        """Tool 결과에서 출처를 추출합니다."""
        # Arrange
        mock_result = {
            "tool_results": [
                {
                    "documents": [
                        {
                            "id": "RM001",
                            "ingredient_name_ko": "글리세린",
                            "@search.score": 5.2,
                        }
                    ]
                }
            ]
        }

        # Act
        sources = ingredient_worker._extract_sources(mock_result)

        # Assert
        assert len(sources) == 1
        assert sources[0]["id"] == "RM001"
        assert sources[0]["title"] == "글리세린"


class TestIngredientWorkerFormatResponse:
    """IngredientWorker의 응답 포맷팅 테스트"""

    def test_format_single_ingredient(self, ingredient_worker):
        """단일 원료 응답 포맷팅을 확인합니다."""
        # Arrange
        documents = [
            {
                "ingredient_name_ko": "글리세린",
                "ingredient_name_en": "Glycerin",
                "cas_no": "56-81-5",
                "order_status": "발주완료",
            }
        ]

        # Act
        response = ingredient_worker._format_ingredient_response(documents)

        # Assert
        assert "글리세린" in response
        assert "Glycerin" in response
        assert "56-81-5" in response
        assert "발주완료" in response

    def test_format_multiple_ingredients(self, ingredient_worker):
        """여러 원료 응답 포맷팅을 확인합니다."""
        # Arrange
        documents = [
            {
                "ingredient_name_ko": "글리세린",
                "ingredient_name_en": "Glycerin",
                "cas_no": "56-81-5",
            },
            {
                "ingredient_name_ko": "나이아신아마이드",
                "ingredient_name_en": "Niacinamide",
                "cas_no": "98-92-0",
            },
        ]

        # Act
        response = ingredient_worker._format_ingredient_response(documents)

        # Assert
        assert "2개의 원료" in response
        assert "글리세린" in response
        assert "나이아신아마이드" in response

    def test_format_no_results(self, ingredient_worker):
        """검색 결과가 없을 때를 확인합니다."""
        # Arrange
        documents = []

        # Act
        response = ingredient_worker._format_ingredient_response(documents)

        # Assert
        assert "검색 결과가 없습니다" in response

    def test_format_many_ingredients_limited_to_five(self, ingredient_worker):
        """많은 원료가 있을 때 최대 5개만 표시합니다."""
        # Arrange
        documents = [
            {"ingredient_name_ko": f"원료{i}", "ingredient_name_en": f"Ingredient{i}"}
            for i in range(10)
        ]

        # Act
        response = ingredient_worker._format_ingredient_response(documents)

        # Assert
        assert "10개의 원료" in response
        # 1-5까지만 표시
        assert "1." in response
        assert "5." in response
        assert "6." not in response


class TestIngredientWorkerStatus:
    """IngredientWorker 상태 조회 테스트"""

    def test_get_status(self, ingredient_worker):
        """Worker 상태를 확인합니다."""
        # Act
        status = ingredient_worker.get_status()

        # Assert
        assert status["worker_type"] == "IngredientWorker"
        assert status["tools_count"] == 2
        assert "timestamp" in status


class TestIngredientWorkerIntegration:
    """IngredientWorker 통합 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_scenario_search_by_korean_name(self, ingredient_worker):
        """한글명으로 원료 검색 시나리오"""
        # Arrange
        query = "글리세린 원료 정보 알려줘"

        # Act
        result = await ingredient_worker.process(query)

        # Assert
        assert result["content"] is not None
        assert isinstance(result["content"], str)
        assert result["metadata"]["worker_type"] == "ingredient"

    @pytest.mark.asyncio
    async def test_scenario_search_by_english_name(self, ingredient_worker):
        """영문명으로 원료 검색 시나리오"""
        # Arrange
        query = "Cetearyl Alcohol 원료 찾아줘"

        # Act
        result = await ingredient_worker.process(query)

        # Assert
        assert result["content"] is not None
        # Mock이므로 실제 검색 결과는 확인 불가

    @pytest.mark.asyncio
    async def test_scenario_search_with_filter(self, ingredient_worker):
        """필터 조건으로 검색 시나리오"""
        # Arrange
        query = "발주완료된 원료 목록 보여줘"

        # Act
        result = await ingredient_worker.process(query)

        # Assert
        assert result["content"] is not None
        assert result["metadata"]["worker_type"] == "ingredient"

    @pytest.mark.asyncio
    async def test_scenario_contextual_search(self, ingredient_worker):
        """컨텍스트 기반 검색 시나리오"""
        # Arrange
        context = [
            {"role": "user", "content": "글리세린에 대해 알려줘"},
            {"role": "assistant", "content": "글리세린(Glycerin)은 보습 원료입니다..."},
        ]
        query = "이 원료의 CAS 번호는?"

        # Act
        result = await ingredient_worker.process(query, context=context)

        # Assert
        assert result["content"] is not None
        # Context가 전달되었지만 Mock이므로 실제 처리는 안됨


class TestIngredientWorkerEdgeCases:
    """IngredientWorker 엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_query(self, ingredient_worker):
        """빈 쿼리 처리를 확인합니다."""
        # Act
        result = await ingredient_worker.process("")

        # Assert
        assert "content" in result
        # Mock이므로 빈 쿼리도 응답

    @pytest.mark.asyncio
    async def test_very_long_query(self, ingredient_worker):
        """매우 긴 쿼리 처리를 확인합니다."""
        # Arrange
        long_query = "원료 " * 100  # 200자

        # Act
        result = await ingredient_worker.process(long_query)

        # Assert
        assert "content" in result

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, ingredient_worker):
        """특수 문자가 포함된 쿼리를 확인합니다."""
        # Arrange
        query = "C16-18 알코올 (100%) 원료 찾아줘!"

        # Act
        result = await ingredient_worker.process(query)

        # Assert
        assert "content" in result
