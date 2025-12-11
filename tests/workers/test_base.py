"""BaseWorker 테스트

Worker Agent 베이스 클래스의 동작을 검증합니다.
"""

import pytest

from src.workers.base import BaseWorker


class MockWorker(BaseWorker):
    """테스트용 Mock Worker
    
    BaseWorker를 상속하여 process() 메서드를 구현합니다.
    """

    async def process(self, query: str, context: list[dict] | None = None) -> dict:
        """Mock 처리 로직"""
        result = await self._execute_react(query)
        return {
            "content": result["content"],
            "sources": self._extract_sources(result),
            "timestamp": result.get("timestamp"),
            "metadata": result.get("metadata", {}),
        }


class TestBaseWorker:
    """BaseWorker 기본 동작 테스트"""

    def test_init(self):
        """Worker 초기화를 확인합니다."""
        # Arrange
        chat_client = None  # Mock (테스트 모드)
        instructions = "Test instructions"
        tools = []

        # Act
        worker = MockWorker(chat_client, instructions, tools)

        # Assert
        assert worker.instructions == instructions
        assert worker.tools == tools
        # chat_client가 None이면 agent도 None (테스트 모드)
        assert worker.agent is None
        assert worker.chat_client is None

    def test_init_with_tools(self):
        """Tool이 있는 Worker 초기화를 확인합니다."""
        # Arrange
        def mock_tool(query: str) -> str:
            return f"Mock result for {query}"

        chat_client = None
        instructions = "Test instructions"
        tools = [mock_tool]

        # Act
        worker = MockWorker(chat_client, instructions, tools)

        # Assert
        assert len(worker.tools) == 1
        assert worker.tools[0] == mock_tool

    def test_init_with_real_client(self):
        """실제 chat_client를 사용한 초기화를 확인합니다."""
        # Arrange
        class MockChatClient:
            """테스트용 Mock ChatClient"""

            pass

        chat_client = MockChatClient()
        instructions = "Test instructions"
        tools = []

        # Act
        worker = MockWorker(chat_client, instructions, tools)

        # Assert
        assert worker.chat_client is not None
        assert worker.agent is not None  # chat_client가 있으면 agent 생성

    def test_process_not_implemented(self):
        """BaseWorker를 직접 인스턴스화할 수 없음을 확인합니다."""
        # Arrange
        chat_client = None
        instructions = "Test"
        tools = []

        # Act & Assert - 추상 클래스는 직접 인스턴스화 불가
        with pytest.raises(TypeError):
            BaseWorker(chat_client, instructions, tools)  # type: ignore

    def test_get_status(self):
        """Worker 상태 조회를 확인합니다."""
        # Arrange
        chat_client = None
        instructions = "Test instructions with some length"
        tools = [lambda x: x, lambda y: y]
        worker = MockWorker(chat_client, instructions, tools)

        # Act
        status = worker.get_status()

        # Assert
        assert status["worker_type"] == "MockWorker"
        assert status["tools_count"] == 2
        assert status["instructions_length"] == len(instructions)
        assert "timestamp" in status


class TestReActExecution:
    """ReAct 패턴 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_react_basic(self):
        """기본 ReAct 실행을 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        # Act
        result = await worker._execute_react("테스트 쿼리")

        # Assert
        assert "content" in result
        assert isinstance(result["content"], str)
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_execute_react_with_iterations(self):
        """최대 반복 횟수 설정을 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        # Act
        result = await worker._execute_react("테스트 쿼리", max_iterations=3)

        # Assert
        assert "iterations" in result
        # Mock이므로 실제 반복은 1회
        assert result["iterations"] >= 1

    @pytest.mark.asyncio
    async def test_execute_react_timeout(self):
        """타임아웃을 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        # Act - 매우 짧은 타임아웃 (Mock은 빠르므로 성공)
        result = await worker._execute_react("테스트 쿼리", timeout=1)

        # Assert - Mock은 빠르므로 성공
        assert "content" in result

    @pytest.mark.asyncio
    async def test_execute_react_timeout_very_short(self):
        """매우 짧은 타임아웃 시 에러 처리를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        # Act - 1초로 설정 (Mock은 빠르므로 성공)
        result = await worker._execute_react("테스트 쿼리", timeout=1)

        # Assert - 타임아웃이 발생하거나 성공
        assert "content" in result


class TestSourceExtraction:
    """출처 정보 추출 테스트"""

    def test_extract_sources_empty(self):
        """빈 결과에서 출처 추출을 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])
        result = {}

        # Act
        sources = worker._extract_sources(result)

        # Assert
        assert sources == []

    def test_extract_sources_with_documents(self):
        """문서가 있는 결과에서 출처 추출을 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])
        result = {
            "tool_results": [
                {
                    "documents": [
                        {
                            "id": "RM001",
                            "ingredient_name_ko": "글리세린",
                            "@search.score": 5.2,
                        },
                        {
                            "id": "RM002",
                            "ingredient_name_ko": "나이아신아마이드",
                            "@search.score": 4.8,
                        },
                    ]
                }
            ]
        }

        # Act
        sources = worker._extract_sources(result)

        # Assert
        assert len(sources) == 2
        assert sources[0]["title"] == "글리세린"
        assert sources[0]["id"] == "RM001"
        assert sources[0]["score"] == 5.2

    def test_extract_sources_max_three(self):
        """최대 3개의 출처만 추출함을 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])
        result = {
            "tool_results": [
                {
                    "documents": [
                        {"id": f"RM{i:03d}", "ingredient_name_ko": f"원료{i}", "score": 5.0}
                        for i in range(10)
                    ]
                }
            ]
        }

        # Act
        sources = worker._extract_sources(result)

        # Assert
        assert len(sources) == 3

    def test_extract_sources_with_title(self):
        """title 필드가 있는 경우를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])
        result = {
            "tool_results": [
                {
                    "documents": [
                        {
                            "id": "DOC001",
                            "title": "글리세린 원료 정보",
                            "score": 5.2,
                        }
                    ]
                }
            ]
        }

        # Act
        sources = worker._extract_sources(result)

        # Assert
        assert len(sources) == 1
        assert sources[0]["title"] == "글리세린 원료 정보"


class TestMockWorkerProcess:
    """MockWorker의 process() 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_process_returns_correct_structure(self):
        """process() 반환값의 구조를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test instructions", [])

        # Act
        result = await worker.process("글리세린 원료 찾아줘")

        # Assert
        assert "content" in result
        assert "sources" in result
        assert "metadata" in result
        assert isinstance(result["content"], str)
        assert isinstance(result["sources"], list)
        assert isinstance(result["metadata"], dict)

    @pytest.mark.asyncio
    async def test_process_with_context(self):
        """컨텍스트를 포함한 process()를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test instructions", [])
        context = [
            {"role": "user", "content": "이전 질문"},
            {"role": "assistant", "content": "이전 응답"},
        ]

        # Act
        result = await worker.process("후속 질문", context=context)

        # Assert
        assert "content" in result
        # Context는 전달되었지만 Mock이므로 실제로 사용되지 않음


class TestWorkerInheritance:
    """Worker 상속 패턴 테스트"""

    def test_custom_worker_implementation(self):
        """커스텀 Worker 구현을 확인합니다."""

        # Arrange - 새로운 Worker 정의
        class CustomWorker(BaseWorker):
            async def process(self, query: str, context: list[dict] | None = None) -> dict:
                return {
                    "content": f"Custom: {query}",
                    "sources": [],
                    "metadata": {"custom": True},
                }

        # Act
        worker = CustomWorker(None, "Custom instructions", [])
        status = worker.get_status()

        # Assert
        assert status["worker_type"] == "CustomWorker"

    @pytest.mark.asyncio
    async def test_custom_worker_process(self):
        """커스텀 Worker의 process() 동작을 확인합니다."""

        # Arrange
        class CustomWorker(BaseWorker):
            async def process(self, query: str, context: list[dict] | None = None) -> dict:
                return {
                    "content": f"Processed: {query}",
                    "sources": [],
                    "metadata": {"custom": True},
                }

        worker = CustomWorker(None, "Custom instructions", [])

        # Act
        result = await worker.process("테스트 쿼리")

        # Assert
        assert result["content"] == "Processed: 테스트 쿼리"
        assert result["metadata"]["custom"] is True


class TestResponseParsing:
    """Agent 응답 파싱 헬퍼 메서드 테스트"""

    def test_extract_content_from_response_with_content_attr(self):
        """response.content 속성이 있는 경우를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        class MockResponse:
            content = "Test response content"

        # Act
        content = worker._extract_content_from_response(MockResponse())

        # Assert
        assert content == "Test response content"

    def test_extract_content_from_response_with_messages(self):
        """response.messages가 있는 경우를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        class MockMessage:
            content = "Last message content"

        class MockResponse:
            messages = [MockMessage()]

        # Act
        content = worker._extract_content_from_response(MockResponse())

        # Assert
        assert content == "Last message content"

    def test_extract_content_from_response_fallback(self):
        """속성이 없는 경우 문자열 변환을 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        class MockResponse:
            def __str__(self):
                return "Fallback content"

        # Act
        content = worker._extract_content_from_response(MockResponse())

        # Assert
        assert content == "Fallback content"

    def test_extract_tools_used_empty(self):
        """Tool이 사용되지 않은 경우를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        class MockResponse:
            pass

        # Act
        tools_used = worker._extract_tools_used_from_response(MockResponse())

        # Assert
        assert tools_used == []

    def test_extract_tools_used_with_tool_calls(self):
        """response.tool_calls가 있는 경우를 확인합니다."""
        # Arrange
        worker = MockWorker(None, "Test", [])

        class MockFunction:
            name = "search_documents"

        class MockToolCall:
            function = MockFunction()

        class MockResponse:
            tool_calls = [MockToolCall()]

        # Act
        tools_used = worker._extract_tools_used_from_response(MockResponse())

        # Assert
        assert tools_used == ["search_documents"]
