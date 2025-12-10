"""Orchestrator - 전체 시스템 진입점."""

from typing import Any

from ..utils.logger import get_logger
from .context_manager import ContextManager
from .session_manager import SessionManager

logger = get_logger(__name__)


class Orchestrator:
    """전체 시스템 진입점.
    
    SessionManager, ContextManager, SupervisorAgent를 통합하여
    사용자 쿼리 처리를 orchestrate합니다.
    
    플로우:
        1. 세션 관리 (SessionManager)
        2. 컨텍스트 추가 (ContextManager)
        3. Supervisor 호출 (적절한 Worker 선택)
        4. 응답 저장 및 반환
    """

    def __init__(
        self,
        session_manager: SessionManager,
        context_manager: ContextManager,
        supervisor: Any,  # SupervisorAgent (순환 import 방지)
    ):
        """Orchestrator를 초기화합니다.
        
        Args:
            session_manager: SessionManager 인스턴스
            context_manager: ContextManager 인스턴스
            supervisor: SupervisorAgent 인스턴스
        """
        self.session_manager = session_manager
        self.context_manager = context_manager
        self.supervisor = supervisor
        
        logger.info("Orchestrator 초기화 완료")

    async def process_query(
        self,
        user_id: str,
        query: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """사용자 쿼리를 처리합니다.
        
        Args:
            user_id: 사용자 ID
            query: 사용자 질의
            session_id: 세션 ID (없으면 새로 생성)
            
        Returns:
            {
                "session_id": str,
                "response": {
                    "content": str,
                    "worker": str,
                    "timestamp": datetime,
                    "metadata": dict
                }
            }
            
        Example:
            >>> orchestrator = Orchestrator.create_default(chat_client)
            >>> result = await orchestrator.process_query(
            ...     user_id="user123",
            ...     query="비타민C CAS 번호는?"
            ... )
            >>> print(result["response"]["content"])
        """
        try:
            # 1. 세션 관리
            if session_id is None:
                # 새 세션 생성
                session_id = self.session_manager.create_session(user_id)
                logger.info(f"새 세션 생성: session_id={session_id}")
            else:
                # 기존 세션 확인
                session = self.session_manager.get_session(session_id)
                if session is None:
                    # 세션이 없으면 새로 생성
                    logger.warning(f"세션을 찾을 수 없음: {session_id}, 새 세션 생성")
                    session_id = self.session_manager.create_session(user_id)
                else:
                    # 세션 업데이트
                    self.session_manager.update_session(session_id)

            # 2. 사용자 메시지를 컨텍스트에 추가
            await self.context_manager.add_message(session_id, "user", query)
            
            # 3. 대화 컨텍스트 조회
            messages = await self.context_manager.get_context(session_id)
            
            # ChatMessage를 dict로 변환 (text 속성 사용)
            context = [
                {"role": msg.role, "content": msg.text or ""}
                for msg in messages
            ]
            
            # 4. Supervisor 호출
            logger.info(f"Supervisor 호출: session_id={session_id}, query={query}")
            response = await self.supervisor.process(
                query=query,
                context=context,
                session_id=session_id,
            )
            
            # 5. Assistant 응답을 컨텍스트에 추가
            await self.context_manager.add_message(
                session_id,
                "assistant",
                response["content"],
                metadata={
                    "worker": response.get("worker"),
                    "timestamp": str(response.get("timestamp")),
                },
            )
            
            # 6. 결과 반환
            logger.info(f"쿼리 처리 완료: session_id={session_id}, worker={response.get('worker')}")
            return {
                "session_id": session_id,
                "response": response,
            }
            
        except Exception as e:
            logger.error(f"쿼리 처리 실패: {e}", exc_info=True)
            
            # 에러 응답 반환
            return {
                "session_id": session_id if session_id else "error",
                "response": {
                    "content": f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}",
                    "worker": "error",
                    "timestamp": None,
                    "metadata": {"error": str(e)},
                },
            }

    def clear_session(self, session_id: str) -> bool:
        """세션을 삭제합니다.
        
        Args:
            session_id: 삭제할 세션 ID
            
        Returns:
            성공 여부
            
        Example:
            >>> orchestrator.clear_session("session-123")
            True
        """
        try:
            # 세션 존재 여부 확인
            session = self.session_manager.get_session(session_id)
            if session is None:
                logger.warning(f"세션을 찾을 수 없음: {session_id}")
                return False
            
            # 세션 삭제
            self.session_manager.delete_session(session_id)
            logger.info(f"세션 삭제 완료: session_id={session_id}")
            return True
            
        except Exception as e:
            logger.error(f"세션 삭제 실패: {e}", exc_info=True)
            return False

    @classmethod
    def create_default(
        cls,
        chat_client: Any,
        ttl_minutes: int = 30,
        max_turns: int = 5,
        max_tokens: int = 4000,
    ) -> "Orchestrator":
        """기본 설정으로 Orchestrator를 생성합니다.
        
        Args:
            chat_client: Agent Framework ChatClient
            ttl_minutes: 세션 TTL (분)
            max_turns: 최대 대화 턴
            max_tokens: 최대 토큰 수
            
        Returns:
            Orchestrator 인스턴스
            
        Example:
            >>> from agent_framework.azure import AzureOpenAIResponsesClient
            >>> chat_client = AzureOpenAIResponsesClient()
            >>> orchestrator = Orchestrator.create_default(chat_client)
        """
        from ..supervisor.aggregator import Aggregator
        from ..supervisor.supervisor import SupervisorAgent
        from ..workers.ingredient import IngredientWorker
        from ..workers.tools.search_tools import (
            initialize_search_clients,
            search_documents,
            search_with_filter,
        )
        
        # Search tools 초기화
        initialize_search_clients()
        
        # 컴포넌트 생성
        session_manager = SessionManager(ttl_minutes=ttl_minutes)
        context_manager = ContextManager(
            session_manager=session_manager,
            max_turns=max_turns,
            max_tokens=max_tokens,
        )
        
        # Worker 생성
        search_tools = [search_documents, search_with_filter]
        workers = {
            "원료": IngredientWorker(chat_client, tools=search_tools),
            # TODO: 추후 FormulaWorker, RegulationWorker 추가
        }
        
        # Supervisor 생성
        aggregator = Aggregator()
        supervisor = SupervisorAgent(
            chat_client=chat_client,
            aggregator=aggregator,
            workers=workers,
        )
        
        logger.info("기본 Orchestrator 생성 완료")
        
        return cls(
            session_manager=session_manager,
            context_manager=context_manager,
            supervisor=supervisor,
        )
