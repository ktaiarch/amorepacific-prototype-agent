"""세션 관리.

Agent Framework의 AgentThread를 활용하여 세션을 관리합니다.
"""

import uuid
from datetime import datetime, timedelta

from agent_framework import AgentThread, ChatMessageStore

from ..utils.logger import get_logger
from .models import Session

logger = get_logger(__name__)


class SessionManager:
    """세션 생성 및 관리.
    
    Agent Framework의 AgentThread를 래핑하여 세션을 관리합니다.
    - AgentThread: 스레드 및 메시지 저장소 관리
    - 메타데이터: user_id, 생성/업데이트 시각, TTL 등
    """

    def __init__(self, ttl_minutes: int | float = 30):
        """SessionManager를 초기화합니다.
        
        Args:
            ttl_minutes: 세션 유효 시간 (분)
        """
        self.threads: dict[str, AgentThread] = {}  # {session_id: AgentThread}
        self.metadata: dict[str, Session] = {}  # {session_id: Session}
        self.ttl = timedelta(minutes=ttl_minutes)
        
        logger.info(f"SessionManager 초기화 완료 (TTL: {ttl_minutes}분)")

    def create_session(self, user_id: str) -> str:
        """새 세션을 생성합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            session_id: 생성된 세션 ID
            
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session("user123")
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        # AgentThread 생성 (메시지 저장소만 설정)
        # NOTE: service_thread_id와 message_store는 동시 설정 불가
        # 로컬 관리이므로 message_store만 사용
        thread = AgentThread(message_store=ChatMessageStore())
        
        # 세션 메타데이터 생성
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now
        )
        
        self.threads[session_id] = thread
        self.metadata[session_id] = session
        
        logger.info(f"세션 생성 완료: session_id={session_id}, user_id={user_id}")
        
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        """세션 정보를 조회합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            세션 정보 또는 None (세션이 없거나 만료된 경우)
            
        Raises:
            SessionError: 세션 조회 중 오류 발생
        """
        if session_id not in self.metadata:
            logger.warning(f"세션을 찾을 수 없음: {session_id}")
            return None
        
        session = self.metadata[session_id]
        
        # TTL 확인
        if datetime.now() - session.updated_at > self.ttl:
            logger.info(f"세션 만료: {session_id}")
            self.delete_session(session_id)
            return None
        
        return session

    def get_thread(self, session_id: str) -> AgentThread | None:
        """AgentThread 인스턴스를 반환합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            AgentThread 인스턴스 또는 None
        """
        # 먼저 세션 유효성 확인
        if self.get_session(session_id) is None:
            return None
        
        return self.threads.get(session_id)

    def update_session(self, session_id: str) -> None:
        """세션 타임스탬프를 업데이트합니다.
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self.metadata:
            self.metadata[session_id].updated_at = datetime.now()
            logger.debug(f"세션 업데이트: {session_id}")

    def delete_session(self, session_id: str) -> None:
        """세션을 삭제합니다.
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self.threads:
            del self.threads[session_id]
        
        if session_id in self.metadata:
            del self.metadata[session_id]
        
        logger.info(f"세션 삭제: {session_id}")

    def cleanup_expired_sessions(self) -> int:
        """만료된 세션을 정리합니다.
        
        Returns:
            삭제된 세션 수
        """
        now = datetime.now()
        expired_sessions = [
            sid for sid, session in self.metadata.items()
            if now - session.updated_at > self.ttl
        ]
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"만료된 세션 {len(expired_sessions)}개 정리 완료")
        
        return len(expired_sessions)

    def get_all_sessions(self) -> list[Session]:
        """모든 활성 세션을 반환합니다.
        
        Returns:
            세션 리스트
        """
        # 먼저 만료된 세션 정리
        self.cleanup_expired_sessions()
        
        return list(self.metadata.values())

    def get_session_count(self) -> int:
        """활성 세션 수를 반환합니다.
        
        Returns:
            세션 개수
        """
        self.cleanup_expired_sessions()
        return len(self.metadata)
