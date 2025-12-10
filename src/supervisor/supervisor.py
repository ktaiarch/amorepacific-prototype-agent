"""Supervisor Agent - Agent-as-Tool 패턴으로 Worker 자동 라우팅."""

from datetime import datetime
from typing import Any

from agent_framework import ChatAgent

from ..utils.logger import get_logger
from .aggregator import Aggregator
from .prompts import SUPERVISOR_INSTRUCTIONS
from .worker_tools import create_worker_tools

logger = get_logger(__name__)


class SupervisorAgent:
    """Worker Agent를 Tool로 사용하는 Supervisor (Agent-as-Tool 패턴)."""

    def __init__(
        self,
        chat_client,
        aggregator: Aggregator,
        workers: dict[str, Any],
    ):
        """SupervisorAgent를 초기화합니다 (Agent-as-Tool 패턴).

        Args:
            chat_client: Agent Framework ChatClient
            aggregator: Aggregator 인스턴스
            workers: Worker 딕셔너리 ({"원료": IngredientWorker, ...})

        Example:
            >>> from agent_framework.azure import AzureOpenAIResponsesClient
            >>> from src.supervisor import Aggregator
            >>> from src.workers import IngredientWorker
            >>>
            >>> chat_client = AzureOpenAIResponsesClient()
            >>> aggregator = Aggregator()
            >>> workers = {"원료": IngredientWorker(chat_client)}
            >>>
            >>> supervisor = SupervisorAgent(chat_client, aggregator, workers)
        """
        self.chat_client = chat_client
        self.aggregator = aggregator
        self.workers = workers

        # Worker를 Tool로 변환
        self.worker_tools = create_worker_tools(workers)

        # Agent-as-Tool 패턴: ChatAgent 생성
        self.agent = ChatAgent(
            chat_client=chat_client,
            instructions=SUPERVISOR_INSTRUCTIONS,
            tools=self.worker_tools,
        )
        
        logger.info(
            f"SupervisorAgent 초기화: "
            f"workers={list(workers.keys())}, "
            f"tools={len(self.worker_tools)}개"
        )

    async def process(
        self,
        query: str,
        context: list[dict] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """사용자 쿼리를 처리합니다 (Agent가 자동으로 적절한 Worker Tool 선택).

        Args:
            query: 사용자 질의
            context: 대화 컨텍스트 (선택사항)
            session_id: 세션 ID (선택사항, 로깅용)

        Returns:
            {
                "content": str,           # 최종 응답
                "worker": str,            # 사용된 Worker (tool_calls에서 추출)
                "timestamp": datetime,    # 응답 시각
                "metadata": dict          # 추가 정보 (tool_calls 등)
            }

        Example:
            >>> result = await supervisor.process(
            ...     query="비타민C CAS 번호는?",
            ...     context=[{"role": "user", "content": "안녕"}],
            ...     session_id="session-123"
            ... )
            >>> print(result["worker"])  # "원료" (Agent가 자동 선택)
            >>> print(result["content"])  # 포맷팅된 응답
        """
        logger.info(f"쿼리 처리 시작: query={query}, session_id={session_id}")

        try:
            # Agent-as-Tool 패턴: Agent가 자동으로 적절한 Tool(Worker) 선택 및 호출
            logger.info("Agent 실행 시작 (Tool 자동 선택)")
            response = await self.agent.run(query)

            logger.info("Agent 실행 완료")

            # 응답에서 content 추출
            content = self._extract_content_from_response(response)

            # 어떤 Tool(Worker)이 호출되었는지 추출
            worker_name = self._extract_worker_name_from_response(response)

            # 응답 포맷팅 (Aggregator 사용)
            formatted_content = self.aggregator.format_response(
                worker_name=worker_name,
                worker_response={"content": content},
                query=query,
            )

            # 최종 응답 생성
            result = {
                "content": formatted_content,
                "worker": worker_name,
                "timestamp": datetime.now(),
                "metadata": {
                    "tool_calls": self._extract_tool_calls(response),
                    "agent_response": str(response)[:200],  # 디버깅용
                },
            }

            logger.info(f"쿼리 처리 완료: worker={worker_name}")
            return result

        except Exception as e:
            logger.error(f"쿼리 처리 실패: {e}", exc_info=True)
            return self._error_response(str(e))

    def _extract_content_from_response(self, response) -> str:
        """Agent 응답에서 content를 추출합니다.

        Args:
            response: Agent 응답 객체

        Returns:
            응답 content 문자열
        """
        # response.content 속성 우선
        if hasattr(response, "content") and response.content:
            return str(response.content)

        # response.messages[-1].content 대체
        if hasattr(response, "messages") and response.messages:
            last_message = response.messages[-1]
            if hasattr(last_message, "content"):
                return str(last_message.content)

        # 기본값
        return str(response)

    def _extract_worker_name_from_response(self, response) -> str:
        """Agent 응답에서 사용된 Worker 이름을 추출합니다.

        Tool 호출 정보를 분석하여 어떤 Worker가 사용되었는지 파악합니다.

        Args:
            response: Agent 응답 객체

        Returns:
            Worker 이름 ("원료", "처방", "규제", "일반")
        """
        tool_calls = self._extract_tool_calls(response)

        if not tool_calls:
            logger.info("Tool 호출 없음, 일반 대화로 처리")
            return "일반"

        # 첫 번째 Tool 호출에서 Worker 이름 추출
        first_tool = tool_calls[0]
        tool_name = first_tool.get("name", "")

        # Tool 이름으로 Worker 매핑
        if "ingredient" in tool_name.lower():
            return "원료"
        elif "formula" in tool_name.lower():
            return "처방"
        elif "regulation" in tool_name.lower():
            return "규제"
        else:
            logger.warning(f"알 수 없는 Tool: {tool_name}, 일반 대화로 처리")
            return "일반"

    def _extract_tool_calls(self, response) -> list[dict]:
        """Agent 응답에서 Tool 호출 정보를 추출합니다.

        Args:
            response: Agent 응답 객체

        Returns:
            Tool 호출 리스트 [{"name": "search_ingredient", "args": {...}}, ...]
        """
        tool_calls = []

        # response.messages[].contents[]에서 FunctionCallContent 찾기
        if hasattr(response, "messages") and response.messages:
            for msg in response.messages:
                if not hasattr(msg, "contents") or not msg.contents:
                    continue
                    
                for content in msg.contents:
                    # FunctionCallContent인지 확인
                    if type(content).__name__ == "FunctionCallContent":
                        tool_calls.append(
                            {
                                "name": getattr(content, "name", "unknown"),
                                "args": getattr(content, "arguments", {}),
                            }
                        )

        return tool_calls

    def _error_response(self, error_msg: str) -> dict[str, Any]:
        """에러 응답을 생성합니다.

        Args:
            error_msg: 에러 메시지

        Returns:
            에러 응답 딕셔너리
        """
        return {
            "content": f"죄송합니다. 처리 중 오류가 발생했습니다: {error_msg}",
            "worker": "error",
            "timestamp": datetime.now(),
            "metadata": {"error": error_msg},
        }
