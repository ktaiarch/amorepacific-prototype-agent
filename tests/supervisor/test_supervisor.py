"""SupervisorAgent 테스트 (Agent-as-Tool 패턴 - Mock 사용)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.supervisor.aggregator import Aggregator
from src.supervisor.supervisor import SupervisorAgent


# Fixtures
@pytest.fixture
def mock_chat_client():
    """Mock ChatClient."""
    return Mock()


@pytest.fixture
def aggregator():
    """Aggregator 인스턴스."""
    return Aggregator()


@pytest.fixture
def mock_workers():
    """Mock Worker 딕셔너리."""
    ingredient_worker = AsyncMock()
    ingredient_worker.process.return_value = {"content": "원료 검색 결과"}

    formula_worker = AsyncMock()
    formula_worker.process.return_value = {"content": "처방 검색 결과"}

    regulation_worker = AsyncMock()
    regulation_worker.process.return_value = {"content": "규제 검색 결과"}

    return {
        "원료": ingredient_worker,
        "처방": formula_worker,
        "규제": regulation_worker,
    }


def create_mock_tool_call(name: str, args: dict | None = None):
    """Mock tool_call 객체 생성 헬퍼."""
    mock_tc = Mock(spec=["name", "args"])
    mock_tc.name = name
    mock_tc.args = args or {}
    return mock_tc


class TestSupervisorInit:
    """SupervisorAgent 초기화 테스트."""

    def test_init_creates_supervisor_with_chat_client(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """chat_client로 SupervisorAgent를 초기화해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent") as MockChatAgent:
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            assert supervisor.chat_client == mock_chat_client
            assert supervisor.aggregator == aggregator
            assert supervisor.workers == mock_workers
            assert len(supervisor.worker_tools) == 3
            MockChatAgent.assert_called_once()

    def test_init_with_multiple_workers_creates_tools(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """여러 Worker로 초기화하면 Tool이 생성되어야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # 3개 Worker → 3개 Tool
            assert len(supervisor.worker_tools) == 3

    def test_init_with_empty_workers(self, mock_chat_client, aggregator):
        """빈 Worker 딕셔너리로도 초기화할 수 있어야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers={},
            )

            assert supervisor.workers == {}
            assert len(supervisor.worker_tools) == 0


@pytest.mark.asyncio
class TestProcessMethod:
    """process 메서드 테스트."""

    async def test_process_calls_agent_run(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """process()가 agent.run()을 호출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent") as MockChatAgent:
            # Mock Agent
            mock_agent = AsyncMock()

            # Agent Framework 스타일 response
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_ingredient"
            mock_function_call.arguments = {"query": "비타민C"}

            mock_assistant_msg = Mock()
            mock_assistant_msg.role = "assistant"
            mock_assistant_msg.contents = [mock_function_call]

            mock_final_msg = Mock()
            mock_final_msg.role = "assistant"
            mock_final_msg.content = "원료 검색 완료"
            mock_final_msg.contents = []  # 빈 리스트 (TextContent가 들어갈 수 있지만 생략)

            mock_response = Mock()
            mock_response.content = "원료 검색 완료"
            mock_response.messages = [mock_assistant_msg, mock_final_msg]

            mock_agent.run.return_value = mock_response
            MockChatAgent.return_value = mock_agent

            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Act
            result = await supervisor.process("비타민C 검색")

            # Assert
            mock_agent.run.assert_called_once_with("비타민C 검색")
            assert result["worker"] == "원료"
            assert "content" in result

    async def test_process_extracts_worker_from_tool_calls(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """Tool 호출 정보에서 Worker를 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent") as MockChatAgent:
            # Mock Agent - 처방 Tool 호출
            mock_agent = AsyncMock()

            # Agent Framework 스타일
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_formula"
            mock_function_call.arguments = {"query": "포뮬라"}

            mock_assistant_msg = Mock()
            mock_assistant_msg.role = "assistant"
            mock_assistant_msg.contents = [mock_function_call]

            mock_response = Mock()
            mock_response.content = "처방 검색 완료"
            mock_response.messages = [mock_assistant_msg]

            mock_agent.run.return_value = mock_response
            MockChatAgent.return_value = mock_agent

            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Act
            result = await supervisor.process("포뮬라 구성")

            # Assert
            assert result["worker"] == "처방"

    async def test_process_handles_regulation_worker(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """규제 Worker 호출을 처리해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent") as MockChatAgent:
            # Mock Agent - 규제 Tool 호출
            mock_agent = AsyncMock()

            # Agent Framework 스타일
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_regulation"
            mock_function_call.arguments = {"query": "금지 성분"}

            mock_assistant_msg = Mock()
            mock_assistant_msg.role = "assistant"
            mock_assistant_msg.contents = [mock_function_call]

            mock_response = Mock()
            mock_response.content = "규제 검색 완료"
            mock_response.messages = [mock_assistant_msg]

            mock_agent.run.return_value = mock_response
            MockChatAgent.return_value = mock_agent

            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Act
            result = await supervisor.process("금지 성분 확인")

            # Assert
            assert result["worker"] == "규제"

    async def test_process_formats_response_with_aggregator(
        self, mock_chat_client, mock_workers
    ):
        """Aggregator로 응답을 포맷팅해야 합니다."""
        # Mock Aggregator
        aggregator = Mock()
        aggregator.format_response = Mock(return_value="포맷팅된 응답")

        with patch("src.supervisor.supervisor.ChatAgent") as MockChatAgent:
            # Mock Agent
            mock_agent = AsyncMock()

            mock_response = Mock()
            mock_response.content = "원본 응답"
            mock_response.tool_calls = [create_mock_tool_call("search_ingredient_tool")]
            mock_response.messages = []

            mock_agent.run.return_value = mock_response
            MockChatAgent.return_value = mock_agent

            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Act
            result = await supervisor.process("쿼리")

            # Assert
            aggregator.format_response.assert_called_once()
            assert result["content"] == "포맷팅된 응답"

    async def test_process_includes_metadata(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """결과에 메타데이터가 포함되어야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent") as MockChatAgent:
            # Mock Agent
            mock_agent = AsyncMock()

            mock_response = Mock()
            mock_response.content = "응답"
            mock_response.tool_calls = [create_mock_tool_call("search_ingredient_tool")]
            mock_response.messages = []

            mock_agent.run.return_value = mock_response
            MockChatAgent.return_value = mock_agent

            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Act
            result = await supervisor.process("쿼리")

            # Assert
            assert "timestamp" in result
            assert "metadata" in result
            assert "tool_calls" in result["metadata"]

    async def test_process_handles_error(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """에러 발생 시 에러 응답을 반환해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent") as MockChatAgent:
            # Mock Agent - 에러 발생
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = Exception("API 에러")
            MockChatAgent.return_value = mock_agent

            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Act
            result = await supervisor.process("쿼리")

            # Assert
            assert result["worker"] == "error"
            assert "오류가 발생했습니다" in result["content"]
            assert "metadata" in result
            assert "error" in result["metadata"]


class TestExtractContentFromResponse:
    """_extract_content_from_response 테스트."""

    def test_extracts_content_from_response_attribute(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """response.content 속성에서 내용을 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            mock_response = Mock()
            mock_response.content = "응답 내용"

            # Act
            content = supervisor._extract_content_from_response(mock_response)

            # Assert
            assert content == "응답 내용"

    def test_extracts_content_from_messages(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """response.messages[-1].content에서 내용을 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            mock_message = Mock()
            mock_message.content = "메시지 내용"

            mock_response = Mock()
            mock_response.content = None
            mock_response.messages = [mock_message]

            # Act
            content = supervisor._extract_content_from_response(mock_response)

            # Assert
            assert content == "메시지 내용"

    def test_returns_string_representation_as_fallback(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """대체로 문자열 표현을 반환해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            mock_response = Mock()
            mock_response.content = None
            mock_response.messages = None
            mock_response.__str__ = Mock(return_value="Fallback")

            # Act
            content = supervisor._extract_content_from_response(mock_response)

            # Assert
            assert "Fallback" in content


class TestExtractWorkerNameFromResponse:
    """_extract_worker_name_from_response 테스트."""

    def test_extracts_ingredient_worker_from_tool_name(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """ingredient tool에서 '원료' Worker를 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Agent Framework 스타일
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_ingredient"
            mock_function_call.arguments = {}

            mock_message = Mock()
            mock_message.role = "assistant"
            mock_message.contents = [mock_function_call]

            mock_response = Mock()
            mock_response.messages = [mock_message]

            # Act
            worker = supervisor._extract_worker_name_from_response(mock_response)

            # Assert
            assert worker == "원료"

    def test_extracts_formula_worker_from_tool_name(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """formula tool에서 '처방' Worker를 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Agent Framework 스타일
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_formula"
            mock_function_call.arguments = {}

            mock_message = Mock()
            mock_message.role = "assistant"
            mock_message.contents = [mock_function_call]

            mock_response = Mock()
            mock_response.messages = [mock_message]

            # Act
            worker = supervisor._extract_worker_name_from_response(mock_response)

            # Assert
            assert worker == "처방"

    def test_extracts_regulation_worker_from_tool_name(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """regulation tool에서 '규제' Worker를 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Agent Framework 스타일
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_regulation"
            mock_function_call.arguments = {}

            mock_message = Mock()
            mock_message.role = "assistant"
            mock_message.contents = [mock_function_call]

            mock_response = Mock()
            mock_response.messages = [mock_message]

            # Act
            worker = supervisor._extract_worker_name_from_response(mock_response)

            # Assert
            assert worker == "규제"

    def test_returns_unknown_for_no_tool_calls(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """Tool 호출이 없으면 '일반'을 반환해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            mock_response = Mock()
            mock_response.tool_calls = []
            mock_response.messages = []

            # Act
            worker = supervisor._extract_worker_name_from_response(mock_response)

            # Assert
            assert worker == "일반"

    def test_returns_unknown_for_unrecognized_tool(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """인식할 수 없는 Tool이면 '일반'을 반환해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            mock_response = Mock()
            mock_response.tool_calls = [create_mock_tool_call("unknown_tool")]
            mock_response.messages = []

            # Act
            worker = supervisor._extract_worker_name_from_response(mock_response)

            # Assert
            assert worker == "일반"


class TestExtractToolCalls:
    """_extract_tool_calls 테스트."""

    def test_extracts_tool_calls_from_response_attribute(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """response.tool_calls에서 Tool 호출을 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Agent Framework 스타일: contents 안에 FunctionCallContent
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_ingredient"
            mock_function_call.arguments = {"query": "비타민C"}

            mock_message = Mock()
            mock_message.role = "assistant"
            mock_message.contents = [mock_function_call]

            mock_response = Mock()
            mock_response.messages = [mock_message]

            # Act
            tool_calls = supervisor._extract_tool_calls(mock_response)

            # Assert
            assert len(tool_calls) == 1
            assert tool_calls[0]["name"] == "search_ingredient"
            assert tool_calls[0]["args"] == {"query": "비타민C"}

    def test_extracts_tool_calls_from_messages(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """response.messages[].contents[]에서 FunctionCallContent를 추출해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            # Agent Framework 스타일
            mock_function_call = Mock()
            mock_function_call.__class__.__name__ = "FunctionCallContent"
            mock_function_call.name = "search_formula"
            mock_function_call.arguments = {"query": "포뮬라"}

            mock_message = Mock()
            mock_message.role = "assistant"
            mock_message.contents = [mock_function_call]

            mock_response = Mock()
            mock_response.messages = [mock_message]

            # Act
            tool_calls = supervisor._extract_tool_calls(mock_response)

            # Assert
            assert len(tool_calls) == 1
            assert tool_calls[0]["name"] == "search_formula"

    def test_returns_empty_list_for_no_tool_calls(
        self, mock_chat_client, aggregator, mock_workers
    ):
        """Tool 호출이 없으면 빈 리스트를 반환해야 합니다."""
        with patch("src.supervisor.supervisor.ChatAgent"):
            supervisor = SupervisorAgent(
                chat_client=mock_chat_client,
                aggregator=aggregator,
                workers=mock_workers,
            )

            mock_response = Mock()
            mock_response.tool_calls = None
            mock_response.messages = []

            # Act
            tool_calls = supervisor._extract_tool_calls(mock_response)

            # Assert
            assert tool_calls == []
