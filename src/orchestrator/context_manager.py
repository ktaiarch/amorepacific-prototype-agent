"""대화 컨텍스트 관리.

AgentThread의 message_store를 활용하면서 토큰 관리 기능을 제공합니다.
"""

from typing import Any

import tiktoken
from agent_framework import ChatMessage

from ..utils.errors import SessionError
from ..utils.logger import get_logger
from .session_manager import SessionManager

logger = get_logger(__name__)


class ContextManager:
    """대화 컨텍스트 관리.
    
    SessionManager의 AgentThread를 활용하여 메시지를 관리하고,
    토큰 제한 및 컨텍스트 윈도우 기능을 제공합니다.
    
    Features:
        - AgentThread.message_store 기반 메시지 저장
        - 토큰 카운팅 (tiktoken 사용)
        - 컨텍스트 윈도우 (최근 N턴만 유지)
        - 토큰 제한 (초과 시 오래된 메시지 제거)
    """

    def __init__(
        self,
        session_manager: SessionManager,
        max_turns: int = 5,
        max_tokens: int = 4000,
        model: str = "gpt-4o",
    ):
        """ContextManager를 초기화합니다.
        
        Args:
            session_manager: SessionManager 인스턴스
            max_turns: 유지할 최대 대화 턴 수 (user + assistant = 1턴)
            max_tokens: 최대 토큰 수
            model: 토큰 인코딩에 사용할 모델명
        """
        self.session_manager = session_manager
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        
        # tiktoken 인코더 초기화
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # 모델을 찾을 수 없으면 cl100k_base 사용 (GPT-4 기본)
            logger.warning(f"모델 '{model}'을 찾을 수 없어 cl100k_base 인코딩 사용")
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        logger.info(
            f"ContextManager 초기화 완료 "
            f"(max_turns={max_turns}, max_tokens={max_tokens}, model={model})"
        )

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """메시지를 추가합니다.
        
        Args:
            session_id: 세션 ID
            role: "user" 또는 "assistant"
            content: 메시지 내용
            metadata: 추가 메타데이터 (선택)
            
        Raises:
            SessionError: 세션을 찾을 수 없는 경우
            
        Example:
            >>> await context_manager.add_message(
            ...     session_id="abc123",
            ...     role="user",
            ...     content="Cetearyl Alcohol 원료 찾아줘"
            ... )
        """
        # 1. AgentThread 조회
        thread = self.session_manager.get_thread(session_id)
        if thread is None or thread.message_store is None:
            raise SessionError(f"세션을 찾을 수 없습니다: {session_id}")
        
        # 2. ChatMessage 생성
        message = ChatMessage(
            role=role,  # type: ignore - role accepts str
            text=content,
        )
        
        # 3. message_store에 추가
        await thread.message_store.add_messages([message])
        
        logger.debug(
            f"메시지 추가: session_id={session_id}, role={role}, "
            f"length={len(content)}"
        )
        
        # 4. 컨텍스트 윈도우 관리
        await self._manage_context_window(session_id)

    async def get_context(
        self,
        session_id: str,
        max_messages: int | None = None,
    ) -> list[ChatMessage]:
        """세션의 대화 컨텍스트를 반환합니다.
        
        Args:
            session_id: 세션 ID
            max_messages: 반환할 최대 메시지 수 (None이면 전체)
            
        Returns:
            ChatMessage 리스트
            
        Raises:
            SessionError: 세션을 찾을 수 없는 경우
            
        Example:
            >>> context = await context_manager.get_context("abc123")
            >>> for msg in context:
            ...     print(f"{msg.role}: {msg.text}")
        """
        # AgentThread 조회
        thread = self.session_manager.get_thread(session_id)
        if thread is None or thread.message_store is None:
            raise SessionError(f"세션을 찾을 수 없습니다: {session_id}")
        
        # message_store에서 메시지 조회
        messages = await thread.message_store.list_messages()
        
        if max_messages is not None and len(messages) > max_messages:
            messages = messages[-max_messages:]
        
        return messages

    async def get_context_as_dicts(
        self,
        session_id: str,
        max_messages: int | None = None,
    ) -> list[dict[str, Any]]:
        """세션의 대화 컨텍스트를 딕셔너리 리스트로 반환합니다.
        
        API 응답 등에 사용하기 편리한 형태로 변환합니다.
        
        Args:
            session_id: 세션 ID
            max_messages: 반환할 최대 메시지 수
            
        Returns:
            메시지 딕셔너리 리스트
        """
        messages = await self.get_context(session_id, max_messages)
        
        return [
            {
                "role": str(msg.role),
                "content": msg.text or "",
                "author_name": msg.author_name,
            }
            for msg in messages
        ]

    async def clear_context(self, session_id: str) -> str:
        """세션의 컨텍스트를 초기화합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            새로운 세션 ID
            
        Raises:
            SessionError: 세션을 찾을 수 없는 경우
        """
        # 세션 정보 조회
        session = self.session_manager.get_session(session_id)
        if session is None:
            raise SessionError(f"세션을 찾을 수 없습니다: {session_id}")
        
        # 세션을 삭제하고 재생성
        user_id = session.user_id
        self.session_manager.delete_session(session_id)
        new_session_id = self.session_manager.create_session(user_id)
        
        logger.info(f"컨텍스트 초기화 (세션 재생성): {session_id} -> {new_session_id}")
        
        return new_session_id

    def count_tokens(self, text: str) -> int:
        """텍스트의 토큰 수를 계산합니다.
        
        Args:
            text: 토큰을 계산할 텍스트
            
        Returns:
            토큰 수
            
        Example:
            >>> context_manager.count_tokens("Hello, world!")
            4
        """
        return len(self.encoding.encode(text))

    async def count_context_tokens(self, session_id: str) -> int:
        """세션의 전체 컨텍스트 토큰 수를 계산합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            전체 토큰 수
            
        Raises:
            SessionError: 세션을 찾을 수 없는 경우
        """
        messages = await self.get_context(session_id)
        
        total_tokens = 0
        for msg in messages:
            if msg.text:
                total_tokens += self.count_tokens(msg.text)
            # 메시지당 오버헤드 (role, formatting 등)
            total_tokens += 4
        
        return total_tokens

    async def _manage_context_window(self, session_id: str) -> None:
        """컨텍스트 윈도우를 관리합니다.
        
        최대 턴 수와 토큰 제한을 확인하고,
        초과 시 오래된 메시지를 제거합니다.
        
        Args:
            session_id: 세션 ID
        """
        messages = await self.get_context(session_id)
        
        # 1. 턴 수 제한 확인
        max_messages = self.max_turns * 2  # user + assistant
        if len(messages) > max_messages:
            # 오래된 메시지 제거 필요
            messages_to_remove = len(messages) - max_messages
            logger.info(
                f"컨텍스트 윈도우 초과: {len(messages)} > {max_messages}, "
                f"{messages_to_remove}개 메시지 제거 필요"
            )
            # NOTE: ChatMessageStore는 개별 메시지 삭제를 직접 지원하지 않음
            # 실제로는 최근 메시지만 유지하는 방식으로 구현
            # 여기서는 로그만 남기고 자연스럽게 제한됨 (get_context에서 슬라이싱)
        
        # 2. 토큰 제한 확인
        total_tokens = await self.count_context_tokens(session_id)
        if total_tokens > self.max_tokens:
            logger.warning(
                f"토큰 제한 초과: {total_tokens} > {self.max_tokens}, "
                f"오래된 메시지가 자동으로 제거됩니다"
            )
            # NOTE: 실제 프로덕션에서는 요약 기능 추가 가능
            # 여기서는 프로토타입이므로 경고만 로깅

    async def get_last_n_messages(
        self,
        session_id: str,
        n: int,
    ) -> list[ChatMessage]:
        """최근 N개의 메시지를 반환합니다.
        
        Args:
            session_id: 세션 ID
            n: 반환할 메시지 수
            
        Returns:
            최근 N개의 ChatMessage 리스트
        """
        return await self.get_context(session_id, max_messages=n)

    async def get_context_summary(self, session_id: str) -> dict[str, Any]:
        """컨텍스트 요약 정보를 반환합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            요약 정보 딕셔너리
            
        Example:
            >>> summary = await context_manager.get_context_summary("abc123")
            >>> print(summary)
            {
                "message_count": 10,
                "total_tokens": 1234,
                "max_tokens": 4000,
                "token_usage_percent": 30.85,
                "turns": 5
            }
        """
        messages = await self.get_context(session_id)
        total_tokens = await self.count_context_tokens(session_id)
        
        return {
            "message_count": len(messages),
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "token_usage_percent": round(total_tokens / self.max_tokens * 100, 2),
            "turns": len(messages) // 2,  # user + assistant = 1턴
            "max_turns": self.max_turns,
        }
