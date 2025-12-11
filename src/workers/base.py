"""Worker Agent 베이스 클래스

모든 Worker Agent의 공통 인터페이스와 ReAct 실행 로직을 제공합니다.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from agent_framework import ChatAgent

from ..utils.logger import get_logger

logger = get_logger(__name__)


class BaseWorker(ABC):
    """Worker Agent 베이스 클래스
    
    모든 도메인별 Worker (원료, 처방, 규제)가 상속하는 베이스 클래스입니다.
    Microsoft Agent Framework의 ChatAgent를 래핑하여 ReAct 패턴을 실행합니다.
    
    Attributes:
        agent: Microsoft Agent Framework의 ChatAgent 인스턴스
        instructions: Worker별 시스템 프롬프트
        tools: 사용 가능한 Tool 함수 목록
    
    Examples:
        >>> class IngredientWorker(BaseWorker):
        ...     async def process(self, query: str, context: list) -> dict:
        ...         result = await self._execute_react(query)
        ...         return {"content": result["content"], "sources": [...]}
    """

    def __init__(
        self,
        chat_client: Any,
        instructions: str,
        tools: list[Any],
    ):
        """Worker Agent를 초기화합니다.
        
        Args:
            chat_client: Azure OpenAI 클라이언트 (AzureOpenAIResponsesClient 등)
            instructions: Worker별 시스템 프롬프트
            tools: 사용 가능한 Tool 함수 목록
        
        Examples:
            >>> from agent_framework.azure import AzureOpenAIResponsesClient
            >>> from workers.tools import search_documents, search_with_filter
            >>> 
            >>> client = AzureOpenAIResponsesClient()
            >>> tools = [search_documents, search_with_filter]
            >>> worker = IngredientWorker(client, INSTRUCTIONS, tools)
        """
        self.chat_client = chat_client
        self.instructions = instructions
        self.tools = tools
        
        # Microsoft Agent Framework의 ChatAgent 초기화
        self.agent = ChatAgent(
            chat_client=chat_client,
            instructions=instructions,
            tools=tools,
        )
        
        logger.info(f"{self.__class__.__name__} 초기화 완료 (tools={len(tools)})")

    @abstractmethod
    async def process(
        self,
        query: str,
        context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """쿼리를 처리합니다.
        
        각 Worker가 반드시 구현해야 하는 메서드입니다.
        
        Args:
            query: 사용자 질의
            context: 대화 컨텍스트 (이전 메시지들)
        
        Returns:
            처리 결과
            {
                "content": str,           # 최종 응답 텍스트
                "sources": list[dict],    # 참조한 문서/데이터
                "timestamp": datetime,    # 응답 시각
                "metadata": dict          # 추가 메타데이터
            }
        
        Raises:
            NotImplementedError: 서브클래스에서 구현하지 않은 경우
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.process() must be implemented"
        )

    async def _execute_react(
        self,
        query: str,
        max_iterations: int = 5,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """ReAct 패턴으로 쿼리를 실행합니다.
        
        ChatAgent의 Tool 호출 기능을 사용하여 자율적으로 Tool을 선택하고
        반복적으로 실행합니다.
        
        Args:
            query: 질의
            max_iterations: 최대 반복 횟수 (현재 미사용, Agent Framework가 내부 관리)
            timeout: 타임아웃 (초)
        
        Returns:
            Agent 실행 결과
            {
                "content": str,
                "iterations": int,
                "tools_used": list[str],
                "metadata": dict
            }
        
        Raises:
            asyncio.TimeoutError: 타임아웃 초과 시
        
        Examples:
            >>> result = await worker._execute_react("글리세린 원료 찾아줘")
            >>> print(result["content"])
            '글리세린 원료를 찾았습니다...'
            >>> print(result["tools_used"])
            ['search_documents']
        """
        logger.info(f"ReAct 실행 시작: query='{query[:50]}...', max_iterations={max_iterations}")
        
        try:
            # Microsoft Agent Framework의 ChatAgent.run() 호출
            result = await asyncio.wait_for(
                self._run_agent(query, max_iterations),
                timeout=timeout,
            )
            
            logger.info(
                f"ReAct 실행 완료: iterations={result.get('iterations', 0)}, "
                f"tools_used={result.get('tools_used', [])}"
            )
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"응답 시간 초과 ({timeout}초)"
            logger.error(f"ReAct 실행 실패: {error_msg}")
            return {
                "content": f"죄송합니다. {error_msg}되었습니다.",
                "sources": [],
                "metadata": {"error": "timeout", "timeout_seconds": timeout},
            }
        except Exception as e:
            error_msg = f"ReAct 실행 중 오류: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "content": f"죄송합니다. 처리 중 오류가 발생했습니다: {e}",
                "sources": [],
                "metadata": {"error": str(e)},
            }

    async def _run_agent(
        self,
        query: str,
        max_iterations: int,
    ) -> dict[str, Any]:
        """Agent를 실행하고 결과를 반환합니다.
        
        Microsoft Agent Framework의 ChatAgent.run() 메서드를 호출합니다.
        
        Args:
            query: 질의
            max_iterations: 최대 반복 횟수
        
        Returns:
            Agent 실행 결과
            {
                "content": str,
                "iterations": int,
                "tools_used": list[str],
                "metadata": dict
            }
        
        Raises:
            Exception: Agent 실행 중 오류 발생 시
        """
        # Agent 실행
        try:
            # Microsoft Agent Framework의 ChatAgent.run() 호출
            # run() 메서드는 메시지를 처리하고 응답을 반환합니다
            response = await self.agent.run(query)
            
            # 응답 파싱
            content = self._extract_content_from_response(response)
            tools_used = self._extract_tools_used_from_response(response)
            
            logger.info(f"Agent 실행 완료: tools_used={tools_used}")
            
            return {
                "content": content,
                "iterations": 1,
                "tools_used": tools_used,
                "metadata": {
                    "response_type": type(response).__name__,
                },
            }
            
        except Exception as e:
            logger.error(f"Agent 실행 중 오류: {e}", exc_info=True)
            raise

    def _extract_content_from_response(self, response: Any) -> str:
        """Agent 응답에서 content를 추출합니다.
        
        Args:
            response: Agent Framework의 응답 객체
        
        Returns:
            응답 텍스트
        """
        # Agent Framework의 응답 구조에 따라 파싱
        # 일반적인 패턴:
        # - response.content
        # - response.messages[-1].content
        # - str(response)
        
        if hasattr(response, "content"):
            return str(response.content)
        elif hasattr(response, "messages") and len(response.messages) > 0:
            last_message = response.messages[-1]
            if hasattr(last_message, "content"):
                return str(last_message.content)
            elif hasattr(last_message, "text"):
                return str(last_message.text)
        
        # 기본값: 문자열 변환
        return str(response)

    def _extract_tools_used_from_response(self, response: Any) -> list[str]:
        """Agent 응답에서 사용된 Tool 목록을 추출합니다.
        
        Args:
            response: Agent Framework의 응답 객체
        
        Returns:
            사용된 Tool 이름 목록
        """
        tools_used = []
        
        # Agent Framework의 AgentRunResponse에서 Tool 추출
        # response.messages의 각 메시지의 contents를 확인
        if hasattr(response, "messages"):
            for message in response.messages:
                if hasattr(message, 'contents'):
                    for content in message.contents:
                        content_type = type(content).__name__
                        
                        # FunctionCallContent인 경우 함수 이름 추출
                        if content_type == "FunctionCallContent":
                            if hasattr(content, 'name'):
                                tools_used.append(content.name)
        
        # 중복 제거 (순서 유지)
        return list(dict.fromkeys(tools_used))
    def _extract_sources(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """Agent 실행 결과에서 출처 정보를 추출합니다.
        
        Tool 실행 결과에서 문서 정보를 파싱하여 출처 목록을 생성합니다.
        
        Args:
            result: Agent 실행 결과
        
        Returns:
            출처 정보 목록
            [
                {
                    "title": "문서 제목",
                    "id": "문서 ID",
                    "score": 0.95
                },
                ...
            ]
        
        Examples:
            >>> result = {"tool_results": [...]}
            >>> sources = worker._extract_sources(result)
            >>> print(sources[0]["title"])
            'RM001 - 세테아릴 알코올'
        """
        sources = []
        
        # Tool 실행 결과에서 문서 추출
        if "tool_results" in result:
            for tool_result in result.get("tool_results", []):
                if "documents" in tool_result:
                    # 최대 3개의 문서만 포함
                    for doc in tool_result["documents"][:3]:
                        sources.append(
                            {
                                "title": doc.get("title")
                                or doc.get("ingredient_name_ko")
                                or "Unknown",
                                "id": doc.get("id"),
                                "score": doc.get("@search.score") or doc.get("score"),
                            }
                        )
        
        logger.debug(f"출처 정보 추출: {len(sources)}개")
        return sources

    def get_status(self) -> dict[str, Any]:
        """Worker의 현재 상태를 반환합니다.
        
        디버깅 및 모니터링을 위한 상태 정보입니다.
        
        Returns:
            상태 정보
            {
                "worker_type": str,
                "tools_count": int,
                "instructions_length": int
            }
        """
        return {
            "worker_type": self.__class__.__name__,
            "tools_count": len(self.tools),
            "instructions_length": len(self.instructions),
            "timestamp": datetime.now().isoformat(),
        }
