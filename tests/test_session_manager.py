"""SessionManager 테스트.

SessionManager의 사용법을 보여주고 동작을 검증합니다.
"""

import time
from datetime import datetime, timedelta

import pytest

from src.orchestrator.session_manager import SessionManager


class TestSessionManager:
    """SessionManager 테스트 클래스."""

    def test_create_session(self):
        """세션 생성 테스트.
        
        사용법:
            manager = SessionManager()
            session_id = manager.create_session("user123")
        """
        # Arrange
        manager = SessionManager()
        user_id = "user123"

        # Act
        session_id = manager.create_session(user_id)

        # Assert
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID 형식

    def test_get_session(self):
        """세션 조회 테스트.
        
        사용법:
            session = manager.get_session(session_id)
            if session:
                print(session.user_id, session.created_at)
        """
        # Arrange
        manager = SessionManager()
        user_id = "user456"
        session_id = manager.create_session(user_id)

        # Act
        session = manager.get_session(session_id)

        # Assert
        assert session is not None
        assert session.session_id == session_id
        assert session.user_id == user_id
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_get_nonexistent_session(self):
        """존재하지 않는 세션 조회 테스트."""
        # Arrange
        manager = SessionManager()

        # Act
        session = manager.get_session("nonexistent-id")

        # Assert
        assert session is None

    def test_get_thread(self):
        """AgentThread 조회 테스트.

        사용법:
            thread = manager.get_thread(session_id)
            if thread:
                # AgentThread 사용
                message_store = thread.message_store
        """
        # Arrange
        manager = SessionManager()
        session_id = manager.create_session("user789")

        # Act
        thread = manager.get_thread(session_id)

        # Assert
        assert thread is not None
        # NOTE: message_store 모드에서는 service_thread_id가 None
        assert thread.service_thread_id is None
        assert thread.message_store is not None
        assert thread.message_store is not None

    def test_update_session(self):
        """세션 업데이트 테스트.
        
        사용법:
            manager.update_session(session_id)  # updated_at 갱신
        """
        # Arrange
        manager = SessionManager()
        session_id = manager.create_session("user_update")
        original_session = manager.get_session(session_id)
        original_updated_at = original_session.updated_at

        # 약간의 시간 경과 시뮬레이션
        time.sleep(0.01)

        # Act
        manager.update_session(session_id)
        updated_session = manager.get_session(session_id)

        # Assert
        assert updated_session.updated_at > original_updated_at

    def test_delete_session(self):
        """세션 삭제 테스트.
        
        사용법:
            manager.delete_session(session_id)
        """
        # Arrange
        manager = SessionManager()
        session_id = manager.create_session("user_delete")

        # Act
        manager.delete_session(session_id)

        # Assert
        assert manager.get_session(session_id) is None
        assert manager.get_thread(session_id) is None

    def test_session_ttl(self):
        """세션 TTL 테스트.
        
        사용법:
            manager = SessionManager(ttl_minutes=1)  # 1분 TTL
        """
        # Arrange - TTL을 매우 짧게 설정 (테스트용)
        manager = SessionManager(ttl_minutes=0.0001)  # 0.006초
        session_id = manager.create_session("user_ttl")

        # 세션이 생성되었는지 확인
        assert manager.get_session(session_id) is not None

        # 짧은 대기
        time.sleep(0.01)

        # Act - TTL 만료 후 조회
        expired_session = manager.get_session(session_id)

        # Assert
        assert expired_session is None

    def test_cleanup_expired_sessions(self):
        """만료된 세션 정리 테스트.
        
        사용법:
            removed_count = manager.cleanup_expired_sessions()
        """
        # Arrange
        manager = SessionManager(ttl_minutes=0.0001)
        session_id1 = manager.create_session("user1")
        session_id2 = manager.create_session("user2")

        # 만료 대기
        time.sleep(0.01)

        # Act
        removed_count = manager.cleanup_expired_sessions()

        # Assert
        assert removed_count == 2
        assert manager.get_session(session_id1) is None
        assert manager.get_session(session_id2) is None

    def test_get_all_sessions(self):
        """모든 활성 세션 조회 테스트.
        
        사용법:
            sessions = manager.get_all_sessions()
            for session in sessions:
                print(session.user_id)
        """
        # Arrange
        manager = SessionManager()
        user_ids = ["user1", "user2", "user3"]
        for user_id in user_ids:
            manager.create_session(user_id)

        # Act
        sessions = manager.get_all_sessions()

        # Assert
        assert len(sessions) == 3
        retrieved_user_ids = {s.user_id for s in sessions}
        assert retrieved_user_ids == set(user_ids)

    def test_get_session_count(self):
        """세션 개수 조회 테스트.
        
        사용법:
            count = manager.get_session_count()
        """
        # Arrange
        manager = SessionManager()
        manager.create_session("user1")
        manager.create_session("user2")

        # Act
        count = manager.get_session_count()

        # Assert
        assert count == 2

    def test_multiple_sessions_same_user(self):
        """동일 사용자의 여러 세션 테스트.
        
        한 사용자가 여러 세션을 가질 수 있습니다.
        """
        # Arrange
        manager = SessionManager()
        user_id = "same_user"

        # Act - 동일 사용자로 여러 세션 생성
        session_id1 = manager.create_session(user_id)
        session_id2 = manager.create_session(user_id)

        # Assert
        assert session_id1 != session_id2
        assert manager.get_session(session_id1) is not None
        assert manager.get_session(session_id2) is not None
        assert manager.get_session_count() == 2


class TestSessionManagerIntegration:
    """SessionManager 통합 시나리오 테스트."""

    def test_typical_chat_session_flow(self):
        """일반적인 채팅 세션 플로우.
        
        실제 사용 시나리오:
        1. 세션 생성
        2. 여러 번 업데이트
        3. 세션 조회
        4. 세션 종료
        """
        # Arrange
        manager = SessionManager(ttl_minutes=30)
        user_id = "chat_user"

        # 1. 세션 생성
        session_id = manager.create_session(user_id)
        assert session_id is not None

        # 2. 여러 번의 대화 (세션 업데이트)
        for _ in range(5):
            manager.update_session(session_id)
            session = manager.get_session(session_id)
            assert session is not None

        # 3. AgentThread 사용
        thread = manager.get_thread(session_id)
        assert thread is not None
        assert thread.message_store is not None

        # 4. 세션 종료
        manager.delete_session(session_id)
        assert manager.get_session(session_id) is None

    def test_concurrent_sessions(self):
        """여러 사용자의 동시 세션.
        
        실제 사용 시나리오: 다중 사용자 환경
        """
        # Arrange
        manager = SessionManager()
        users = {
            "user1": None,
            "user2": None,
            "user3": None,
        }

        # Act - 각 사용자의 세션 생성
        for user_id in users.keys():
            users[user_id] = manager.create_session(user_id)

        # Assert - 모든 세션이 독립적으로 존재
        assert manager.get_session_count() == 3
        
        for user_id, session_id in users.items():
            session = manager.get_session(session_id)
            assert session is not None
            assert session.user_id == user_id

            thread = manager.get_thread(session_id)
            assert thread is not None
            # NOTE: message_store 모드에서는 service_thread_id가 None
            assert thread.service_thread_id is None
            assert thread.message_store is not None

    def test_session_cleanup_keeps_active_sessions(self):
        """정리 시 활성 세션은 유지.
        
        만료된 세션만 정리하고 활성 세션은 유지합니다.
        """
        # Arrange
        manager = SessionManager(ttl_minutes=1)  # 1분 TTL
        
        # 만료될 세션 생성 (짧은 TTL)
        old_manager = SessionManager(ttl_minutes=0.0001)
        expired_id = old_manager.create_session("expired_user")
        
        # 활성 세션 생성 (긴 TTL)
        active_id = manager.create_session("active_user")
        
        time.sleep(0.01)  # 만료 대기

        # Act
        old_manager.cleanup_expired_sessions()

        # Assert
        assert old_manager.get_session(expired_id) is None  # 만료됨
        assert manager.get_session(active_id) is not None   # 유지됨


if __name__ == "__main__":
    # 테스트 실행: pytest tests/test_session_manager.py -v
    pytest.main([__file__, "-v"])
