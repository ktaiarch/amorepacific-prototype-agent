"""ContextManager 테스트.

ContextManager의 사용법을 보여주고 동작을 검증합니다.
"""

import pytest

from src.orchestrator.context_manager import ContextManager
from src.orchestrator.session_manager import SessionManager


class TestContextManager:
    """ContextManager 테스트 클래스."""

    @pytest.fixture
    def session_manager(self):
        """SessionManager fixture."""
        return SessionManager(ttl_minutes=30)

    @pytest.fixture
    def context_manager(self, session_manager):
        """ContextManager fixture."""
        return ContextManager(
            session_manager=session_manager,
            max_turns=5,
            max_tokens=4000,
        )

    @pytest.fixture
    def session_id(self, session_manager):
        """세션 ID fixture."""
        return session_manager.create_session("test_user")

    @pytest.mark.asyncio
    async def test_add_message(self, context_manager, session_id):
        """메시지 추가 테스트.
        
        사용법:
            await context_manager.add_message(
                session_id=session_id,
                role="user",
                content="Hello, world!"
            )
        """
        # Arrange
        role = "user"
        content = "Cetearyl Alcohol 원료 찾아줘"

        # Act
        await context_manager.add_message(
            session_id=session_id, role=role, content=content
        )

        # Assert
        context = await context_manager.get_context(session_id)
        assert len(context) == 1
        assert str(context[0].role) == "user"
        assert context[0].text == content

    @pytest.mark.asyncio
    async def test_get_context(self, context_manager, session_id):
        """컨텍스트 조회 테스트.
        
        사용법:
            context = await context_manager.get_context(session_id)
            for msg in context:
                print(f"{msg.role}: {msg.text}")
        """
        # Arrange
        await context_manager.add_message(session_id, "user", "첫 번째 질문")
        await context_manager.add_message(session_id, "assistant", "첫 번째 응답")
        await context_manager.add_message(session_id, "user", "두 번째 질문")

        # Act
        context = await context_manager.get_context(session_id)

        # Assert
        assert len(context) == 3
        assert context[0].text == "첫 번째 질문"
        assert context[1].text == "첫 번째 응답"
        assert context[2].text == "두 번째 질문"

    @pytest.mark.asyncio
    async def test_get_context_with_max_messages(self, context_manager, session_id):
        """최대 메시지 수 제한 테스트.
        
        사용법:
            # 최근 2개 메시지만 조회
            context = await context_manager.get_context(session_id, max_messages=2)
        """
        # Arrange
        for i in range(5):
            await context_manager.add_message(session_id, "user", f"메시지 {i}")

        # Act
        context = await context_manager.get_context(session_id, max_messages=2)

        # Assert
        assert len(context) == 2
        assert context[0].text == "메시지 3"
        assert context[1].text == "메시지 4"

    @pytest.mark.asyncio
    async def test_get_context_as_dicts(self, context_manager, session_id):
        """딕셔너리 형태로 컨텍스트 조회 테스트.
        
        사용법:
            context_dicts = await context_manager.get_context_as_dicts(session_id)
            for msg_dict in context_dicts:
                print(msg_dict["role"], msg_dict["content"])
        """
        # Arrange
        await context_manager.add_message(session_id, "user", "안녕하세요")
        await context_manager.add_message(session_id, "assistant", "반갑습니다")

        # Act
        context_dicts = await context_manager.get_context_as_dicts(session_id)

        # Assert
        assert len(context_dicts) == 2
        assert context_dicts[0]["role"] == "user"
        assert context_dicts[0]["content"] == "안녕하세요"
        assert context_dicts[1]["role"] == "assistant"
        assert context_dicts[1]["content"] == "반갑습니다"

    @pytest.mark.asyncio
    async def test_clear_context(self, context_manager, session_manager, session_id):
        """컨텍스트 초기화 테스트.
        
        사용법:
            new_session_id = await context_manager.clear_context(session_id)
        """
        # Arrange
        await context_manager.add_message(session_id, "user", "테스트 메시지")
        context_before = await context_manager.get_context(session_id)
        assert len(context_before) == 1

        # Act
        new_session_id = await context_manager.clear_context(session_id)

        # Assert
        # 기존 세션은 삭제됨
        assert session_manager.get_session(session_id) is None

        # 새 세션은 존재하고 비어있음
        assert session_manager.get_session(new_session_id) is not None
        new_context = await context_manager.get_context(new_session_id)
        assert len(new_context) == 0

    def test_count_tokens(self, context_manager):
        """토큰 카운팅 테스트.
        
        사용법:
            token_count = context_manager.count_tokens("Hello, world!")
        """
        # Arrange
        text = "Hello, world!"

        # Act
        token_count = context_manager.count_tokens(text)

        # Assert
        assert isinstance(token_count, int)
        assert token_count > 0

    @pytest.mark.asyncio
    async def test_count_context_tokens(self, context_manager, session_id):
        """컨텍스트 전체 토큰 수 계산 테스트.
        
        사용법:
            total_tokens = await context_manager.count_context_tokens(session_id)
        """
        # Arrange
        await context_manager.add_message(session_id, "user", "안녕하세요")
        await context_manager.add_message(session_id, "assistant", "반갑습니다")

        # Act
        total_tokens = await context_manager.count_context_tokens(session_id)

        # Assert
        assert isinstance(total_tokens, int)
        assert total_tokens > 0

    @pytest.mark.asyncio
    async def test_get_last_n_messages(self, context_manager, session_id):
        """최근 N개 메시지 조회 테스트.
        
        사용법:
            recent_messages = await context_manager.get_last_n_messages(
                session_id, n=3
            )
        """
        # Arrange
        for i in range(5):
            await context_manager.add_message(session_id, "user", f"메시지 {i}")

        # Act
        recent_messages = await context_manager.get_last_n_messages(session_id, n=3)

        # Assert
        assert len(recent_messages) == 3
        assert recent_messages[0].text == "메시지 2"
        assert recent_messages[2].text == "메시지 4"

    @pytest.mark.asyncio
    async def test_get_context_summary(self, context_manager, session_id):
        """컨텍스트 요약 정보 조회 테스트.
        
        사용법:
            summary = await context_manager.get_context_summary(session_id)
            print(f"메시지 수: {summary['message_count']}")
            print(f"토큰 사용률: {summary['token_usage_percent']}%")
        """
        # Arrange
        await context_manager.add_message(session_id, "user", "질문")
        await context_manager.add_message(session_id, "assistant", "응답")

        # Act
        summary = await context_manager.get_context_summary(session_id)

        # Assert
        assert summary["message_count"] == 2
        assert summary["turns"] == 1  # user + assistant = 1턴
        assert summary["max_turns"] == 5
        assert summary["total_tokens"] > 0
        assert summary["max_tokens"] == 4000
        assert 0 <= summary["token_usage_percent"] <= 100


class TestContextManagerIntegration:
    """ContextManager 통합 시나리오 테스트."""

    @pytest.mark.asyncio
    async def test_typical_conversation_flow(self):
        """일반적인 대화 플로우.
        
        실제 사용 시나리오:
        1. 세션 및 컨텍스트 매니저 생성
        2. 사용자 메시지 추가
        3. Assistant 응답 추가
        4. 대화 계속
        5. 컨텍스트 조회
        """
        # Arrange
        session_manager = SessionManager()
        context_manager = ContextManager(session_manager, max_turns=3)
        session_id = session_manager.create_session("user123")

        # Act - 대화 진행
        await context_manager.add_message(session_id, "user", "Cetearyl Alcohol 원료 찾아줘")
        await context_manager.add_message(
            session_id, "assistant", "Cetearyl Alcohol 원료를 찾았습니다..."
        )
        await context_manager.add_message(session_id, "user", "CAS 번호는?")
        await context_manager.add_message(session_id, "assistant", "67762-27-0입니다.")

        # Assert
        context = await context_manager.get_context(session_id)
        assert len(context) == 4

        summary = await context_manager.get_context_summary(session_id)
        assert summary["turns"] == 2
        assert summary["message_count"] == 4

    @pytest.mark.asyncio
    async def test_context_window_management(self):
        """컨텍스트 윈도우 관리 테스트.
        
        최대 턴 수를 초과하는 경우 자동 관리되는지 확인합니다.
        """
        # Arrange
        session_manager = SessionManager()
        context_manager = ContextManager(
            session_manager, max_turns=2, max_tokens=4000
        )
        session_id = session_manager.create_session("user123")

        # Act - max_turns(2) 초과하도록 메시지 추가
        for i in range(6):  # 3턴 추가 (max_turns=2 초과)
            await context_manager.add_message(session_id, "user", f"질문 {i}")
            await context_manager.add_message(session_id, "assistant", f"응답 {i}")

        # Assert
        context = await context_manager.get_context(session_id)
        # 6턴 = 12개 메시지 (각 턴마다 user + assistant)
        assert len(context) == 12

        # max_messages로 제한 조회 (2턴 = 4개 메시지)
        limited_context = await context_manager.get_context(
            session_id, max_messages=4
        )
        assert len(limited_context) == 4

    @pytest.mark.asyncio
    async def test_token_counting_integration(self):
        """토큰 카운팅 통합 테스트.
        
        실제 사용 시나리오에서 토큰 카운팅이 정상 작동하는지 확인합니다.
        """
        # Arrange
        session_manager = SessionManager()
        context_manager = ContextManager(session_manager)
        session_id = session_manager.create_session("user123")

        # Act
        await context_manager.add_message(
            session_id,
            "user",
            "This is a test message with multiple words to count tokens.",
        )
        await context_manager.add_message(
            session_id, "assistant", "This is the assistant's response."
        )

        # Assert
        total_tokens = await context_manager.count_context_tokens(session_id)
        assert total_tokens > 0

        summary = await context_manager.get_context_summary(session_id)
        assert summary["total_tokens"] == total_tokens
        assert summary["token_usage_percent"] < 100


if __name__ == "__main__":
    # 테스트 실행: pytest tests/test_context_manager.py -v
    pytest.main([__file__, "-v"])
