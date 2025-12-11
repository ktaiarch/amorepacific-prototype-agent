"""Orchestrator 테스트 (TDD)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.orchestrator.context_manager import ContextManager
from src.orchestrator.orchestrator import Orchestrator
from src.orchestrator.session_manager import SessionManager
from src.supervisor.supervisor import SupervisorAgent


# Fixtures
@pytest.fixture
def mock_chat_client():
    """Mock ChatClient."""
    return Mock()


@pytest.fixture
def session_manager():
    """SessionManager 인스턴스 (실제 사용)."""
    return SessionManager(ttl_minutes=30)


@pytest.fixture
def context_manager(session_manager):
    """ContextManager 인스턴스 (실제 사용)."""
    return ContextManager(
        session_manager=session_manager,
        max_turns=5,
        max_tokens=4000,
    )


@pytest.fixture
def mock_supervisor():
    """Mock SupervisorAgent."""
    supervisor = AsyncMock(spec=SupervisorAgent)
    supervisor.process.return_value = {
        "content": "비타민C는 아스코르브산입니다.",
        "worker": "원료",
        "timestamp": Mock(),
        "metadata": {},
    }
    return supervisor


@pytest.fixture
def orchestrator(session_manager, context_manager, mock_supervisor):
    """Orchestrator 인스턴스 (Mock Supervisor 사용)."""
    return Orchestrator(
        session_manager=session_manager,
        context_manager=context_manager,
        supervisor=mock_supervisor,
    )


class TestOrchestratorInit:
    """Orchestrator 초기화 테스트."""

    def test_init_creates_orchestrator(
        self, session_manager, context_manager, mock_supervisor
    ):
        """Orchestrator를 초기화해야 합니다."""
        orchestrator = Orchestrator(
            session_manager=session_manager,
            context_manager=context_manager,
            supervisor=mock_supervisor,
        )

        assert orchestrator.session_manager == session_manager
        assert orchestrator.context_manager == context_manager
        assert orchestrator.supervisor == mock_supervisor

    def test_init_with_default_components(self, mock_chat_client):
        """기본 컴포넌트로 Orchestrator를 생성할 수 있어야 합니다."""
        # SessionManager, ContextManager, Supervisor를 자동 생성하는 팩토리 메서드
        with patch("src.supervisor.supervisor.SupervisorAgent"), \
             patch("src.workers.ingredient.IngredientWorker"):
            
            orchestrator = Orchestrator.create_default(chat_client=mock_chat_client)

            # Supervisor가 생성되었는지 확인
            assert orchestrator is not None
            assert orchestrator.supervisor is not None


@pytest.mark.asyncio
class TestProcessQuery:
    """process_query 메서드 테스트."""

    async def test_process_query_creates_new_session(self, orchestrator):
        """새 사용자는 세션을 자동으로 생성해야 합니다."""
        user_id = "user123"
        query = "비타민C CAS 번호는?"

        # Act
        result = await orchestrator.process_query(user_id=user_id, query=query)

        # Assert
        assert "session_id" in result
        assert "response" in result
        assert result["response"]["content"] == "비타민C는 아스코르브산입니다."

        # 세션이 생성되었는지 확인
        session = orchestrator.session_manager.get_session(result["session_id"])
        assert session is not None
        assert session.user_id == user_id

    async def test_process_query_with_existing_session(self, orchestrator):
        """기존 세션이 있으면 재사용해야 합니다."""
        user_id = "user123"
        session_id = orchestrator.session_manager.create_session(user_id)

        # Act
        result = await orchestrator.process_query(
            user_id=user_id, query="쿼리", session_id=session_id
        )

        # Assert
        assert result["session_id"] == session_id

    async def test_process_query_adds_user_message_to_context(self, orchestrator):
        """사용자 메시지를 컨텍스트에 추가해야 합니다."""
        user_id = "user123"
        query = "비타민C CAS 번호는?"

        # Act
        result = await orchestrator.process_query(user_id=user_id, query=query)

        # Assert
        session_id = result["session_id"]
        messages = await orchestrator.context_manager.get_context(session_id)

        # user 메시지와 assistant 메시지가 추가되었는지 확인
        assert len(messages) >= 2
        assert str(messages[-2].role) == "user"
        assert messages[-2].text == query
        assert str(messages[-1].role) == "assistant"

    async def test_process_query_calls_supervisor(self, orchestrator, mock_supervisor):
        """Supervisor를 호출해야 합니다."""
        user_id = "user123"
        query = "비타민C CAS 번호는?"

        # Act
        await orchestrator.process_query(user_id=user_id, query=query)

        # Assert
        mock_supervisor.process.assert_called_once()
        call_args = mock_supervisor.process.call_args
        assert call_args[1]["query"] == query
        assert "context" in call_args[1]
        assert "session_id" in call_args[1]

    async def test_process_query_returns_formatted_response(self, orchestrator):
        """포맷팅된 응답을 반환해야 합니다."""
        user_id = "user123"
        query = "비타민C CAS 번호는?"

        # Act
        result = await orchestrator.process_query(user_id=user_id, query=query)

        # Assert
        assert "session_id" in result
        assert "response" in result
        assert "content" in result["response"]
        assert "worker" in result["response"]
        assert "timestamp" in result["response"]

    async def test_process_query_with_context(self, orchestrator, mock_supervisor):
        """대화 컨텍스트를 Supervisor에 전달해야 합니다."""
        user_id = "user123"
        session_id = orchestrator.session_manager.create_session(user_id)

        # 이전 대화 추가
        await orchestrator.context_manager.add_message(
            session_id, "user", "이전 질문"
        )
        await orchestrator.context_manager.add_message(
            session_id, "assistant", "이전 답변"
        )

        # Act
        await orchestrator.process_query(
            user_id=user_id, query="후속 질문", session_id=session_id
        )

        # Assert
        call_args = mock_supervisor.process.call_args
        context = call_args[1]["context"]
        assert len(context) >= 2  # 이전 대화가 포함되어야 함


@pytest.mark.asyncio
class TestClearSession:
    """clear_session 메서드 테스트."""

    async def test_clear_session_removes_session(self, orchestrator):
        """세션을 삭제해야 합니다."""
        user_id = "user123"
        session_id = orchestrator.session_manager.create_session(user_id)

        # Act
        orchestrator.clear_session(session_id)

        # Assert
        session = orchestrator.session_manager.get_session(session_id)
        assert session is None

    async def test_clear_session_clears_context(self, orchestrator):
        """컨텍스트를 삭제해야 합니다."""
        user_id = "user123"
        session_id = orchestrator.session_manager.create_session(user_id)

        # 메시지 추가
        await orchestrator.context_manager.add_message(
            session_id, "user", "메시지"
        )

        # Act
        orchestrator.clear_session(session_id)

        # Assert
        # 세션이 삭제되면 메시지 조회 시 에러 발생
        with pytest.raises(Exception):  # SessionError 예상
            await orchestrator.context_manager.get_messages(session_id)

    async def test_clear_session_returns_success(self, orchestrator):
        """성공 여부를 반환해야 합니다."""
        user_id = "user123"
        session_id = orchestrator.session_manager.create_session(user_id)

        # Act
        result = orchestrator.clear_session(session_id)

        # Assert
        assert result is True  # delete_session은 None을 반환하므로 수정 필요

    async def test_clear_nonexistent_session_returns_false(self, orchestrator):
        """존재하지 않는 세션 삭제 시 False를 반환해야 합니다."""
        # Act
        result = orchestrator.clear_session("nonexistent-session-id")

        # Assert
        assert result is False


@pytest.mark.asyncio
class TestMultiturnConversation:
    """멀티턴 대화 테스트."""

    async def test_multiturn_conversation_maintains_context(
        self, orchestrator, mock_supervisor
    ):
        """여러 턴의 대화에서 컨텍스트를 유지해야 합니다."""
        user_id = "user123"

        # 첫 번째 턴
        result1 = await orchestrator.process_query(
            user_id=user_id, query="비타민C는 뭐야?"
        )
        session_id = result1["session_id"]

        # 두 번째 턴
        mock_supervisor.process.return_value = {
            "content": "CAS 번호는 50-81-7입니다.",
            "worker": "원료",
            "timestamp": Mock(),
            "metadata": {},
        }
        result2 = await orchestrator.process_query(
            user_id=user_id, query="CAS 번호는?", session_id=session_id
        )

        # Assert
        assert result2["session_id"] == session_id

        # 컨텍스트 확인
        messages = await orchestrator.context_manager.get_context(session_id)
        assert len(messages) >= 4  # user1, assistant1, user2, assistant2

    async def test_multiturn_conversation_worker_switching(
        self, orchestrator, mock_supervisor
    ):
        """대화 중 Worker가 전환될 수 있어야 합니다."""
        user_id = "user123"

        # 원료 질문
        result1 = await orchestrator.process_query(
            user_id=user_id, query="비타민C는 뭐야?"
        )
        session_id = result1["session_id"]
        assert result1["response"]["worker"] == "원료"

        # 규제 질문
        mock_supervisor.process.return_value = {
            "content": "EU에서는 허용됩니다.",
            "worker": "규제",
            "timestamp": Mock(),
            "metadata": {},
        }
        result2 = await orchestrator.process_query(
            user_id=user_id, query="EU에서 사용 가능해?", session_id=session_id
        )

        # Assert
        assert result2["response"]["worker"] == "규제"
        assert result2["session_id"] == session_id


@pytest.mark.asyncio
class TestErrorHandling:
    """에러 처리 테스트."""

    async def test_process_query_handles_supervisor_error(self, orchestrator):
        """Supervisor 에러를 처리해야 합니다."""
        orchestrator.supervisor.process.side_effect = Exception("Supervisor 에러")

        user_id = "user123"
        query = "비타민C는?"

        # Act
        result = await orchestrator.process_query(user_id=user_id, query=query)

        # Assert
        assert "error" in result or "response" in result
        # 에러가 발생해도 세션은 생성되어야 함
        assert "session_id" in result

    async def test_process_query_handles_context_error(
        self, session_manager, mock_supervisor
    ):
        """ContextManager 에러를 처리해야 합니다."""
        # Mock ContextManager가 에러를 발생시킴
        mock_context_manager = AsyncMock(spec=ContextManager)
        mock_context_manager.add_message.side_effect = Exception("Context 에러")

        orchestrator = Orchestrator(
            session_manager=session_manager,
            context_manager=mock_context_manager,
            supervisor=mock_supervisor,
        )

        user_id = "user123"
        query = "비타민C는?"

        # Act & Assert
        # 에러가 발생하거나 적절히 처리되어야 함
        result = await orchestrator.process_query(user_id=user_id, query=query)
        assert result is not None

    async def test_process_query_with_invalid_session_creates_new(
        self, orchestrator
    ):
        """잘못된 세션 ID로 요청 시 새 세션을 생성해야 합니다."""
        user_id = "user123"
        invalid_session_id = "invalid-session-id"

        # Act
        result = await orchestrator.process_query(
            user_id=user_id, query="쿼리", session_id=invalid_session_id
        )

        # Assert
        # 새 세션이 생성되어야 함
        assert result["session_id"] != invalid_session_id
        session = orchestrator.session_manager.get_session(result["session_id"])
        assert session is not None


class TestFactoryMethod:
    """create_default 팩토리 메서드 테스트."""

    def test_create_default_with_chat_client(self, mock_chat_client):
        """ChatClient로 기본 Orchestrator를 생성할 수 있어야 합니다."""
        with patch("src.supervisor.supervisor.SupervisorAgent"), \
             patch("src.workers.ingredient.IngredientWorker"):
            
            orchestrator = Orchestrator.create_default(
                chat_client=mock_chat_client
            )

            assert orchestrator is not None
            assert orchestrator.session_manager is not None
            assert orchestrator.context_manager is not None
            assert orchestrator.supervisor is not None

    def test_create_default_with_custom_config(self, mock_chat_client):
        """커스텀 설정으로 Orchestrator를 생성할 수 있어야 합니다."""
        with patch("src.supervisor.supervisor.SupervisorAgent"), \
             patch("src.workers.ingredient.IngredientWorker"):
            
            orchestrator = Orchestrator.create_default(
                chat_client=mock_chat_client,
                ttl_minutes=60,
                max_turns=10,
                max_tokens=8000,
            )

            # 커스텀 설정이 적용되었는지 확인
            assert orchestrator.context_manager.max_turns == 10
            assert orchestrator.context_manager.max_tokens == 8000
