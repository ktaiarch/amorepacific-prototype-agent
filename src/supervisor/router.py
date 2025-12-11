"""Supervisor Router - 쿼리를 분석하여 적절한 Worker로 라우팅."""

import json
from typing import Any

from agent_framework import ChatAgent

from ..utils.logger import get_logger
from .prompts import ROUTER_INSTRUCTIONS

logger = get_logger(__name__)


class Router:
    """쿼리를 분석하여 적절한 Worker로 라우팅하는 Router."""

    DEFAULT_WORKER = "원료"
    VALID_WORKERS = {"원료", "처방", "규제"}
    MAX_CONTEXT_MESSAGES = 3

    def __init__(self, chat_client):
        """Router를 초기화합니다.

        Args:
            chat_client: Agent Framework의 ChatClient
            
        Raises:
            ValueError: chat_client가 None인 경우
        """
        if chat_client is None:
            raise ValueError("chat_client는 필수입니다.")
            
        self.chat_client = chat_client
        self.agent = ChatAgent(
            chat_client=chat_client,
            instructions=ROUTER_INSTRUCTIONS,
        )
        logger.info("Router 초기화 완료")

    async def route(
        self, query: str, context: list[dict] | None = None
    ) -> dict[str, Any]:
        """쿼리를 분석하여 적절한 Worker를 선택합니다.

        Args:
            query: 사용자 질의
            context: 대화 컨텍스트 (선택사항)

        Returns:
            {
                "worker": str,        # "원료", "처방", "규제"
                "confidence": float,  # 0.0 ~ 1.0
                "reasoning": str      # 선택 이유
            }

        Example:
            >>> router = Router(chat_client)
            >>> result = await router.route("CAS 번호가 뭐야?")
            >>> print(result["worker"])  # "원료"
            >>> print(result["confidence"])  # 0.95
        """
        # 컨텍스트 포맷팅
        context_str = self._format_context(context)

        # 프롬프트 생성
        prompt = self._build_routing_prompt(query, context_str)

        # LLM 호출 및 파싱 (1회 재시도)
        try:
            result = await self._call_llm_and_parse(prompt)
            logger.info(
                f"라우팅 성공: {result['worker']} (신뢰도: {result['confidence']:.2f})"
            )
            return result
        except Exception as e:
            logger.warning(f"1차 라우팅 실패: {e}, 재시도 중...")
            try:
                # 재시도
                result = await self._call_llm_and_parse(prompt)
                logger.info(
                    f"재시도 라우팅 성공: {result['worker']} "
                    f"(신뢰도: {result['confidence']:.2f})"
                )
                return result
            except Exception as retry_error:
                logger.error(f"재시도 라우팅 실패: {retry_error}, 기본값 사용")
                return self._get_fallback_result()

    def _format_context(self, context: list[dict] | None) -> str:
        """컨텍스트를 문자열로 포맷팅합니다.

        최근 3개 메시지만 포함하여 토큰 절약.

        Args:
            context: 대화 컨텍스트

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        if not context:
            return "없음"

        lines = []
        # 최근 3개만 사용
        for msg in context[-self.MAX_CONTEXT_MESSAGES :]:
            role = "사용자" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _build_routing_prompt(self, query: str, context_str: str) -> str:
        """라우팅을 위한 프롬프트를 생성합니다.

        Args:
            query: 사용자 질의
            context_str: 포맷팅된 컨텍스트

        Returns:
            프롬프트 문자열
        """
        prompt = f"""
다음 사용자 질의를 분석하여 적절한 Worker를 선택하세요.

<대화 컨텍스트>
{context_str}
</대화 컨텍스트>

<사용자 질의>
{query}
</사용자 질의>

응답 형식 (JSON):
{{
  "worker": "원료" | "처방" | "규제",
  "confidence": 0.0 ~ 1.0,
  "reasoning": "선택 이유"
}}
"""
        return prompt.strip()

    async def _call_llm_and_parse(self, prompt: str) -> dict[str, Any]:
        """LLM을 호출하고 JSON 응답을 파싱합니다.

        Args:
            prompt: 라우팅 프롬프트

        Returns:
            파싱된 라우팅 결과

        Raises:
            ValueError: JSON 파싱 실패 또는 유효하지 않은 Worker
        """
        if self.agent is None:
            raise ValueError("Agent가 초기화되지 않았습니다 (테스트 모드)")

        # Agent.run() 호출 (설계서의 complete() 대신)
        response = await self.agent.run(prompt)

        # 응답 추출
        content = self._extract_content_from_response(response)

        # JSON 파싱
        result = self._parse_json_response(content)

        # 유효성 검증
        self._validate_routing_result(result)

        return result

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

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """JSON 문자열을 파싱합니다.

        Args:
            content: JSON 문자열

        Returns:
            파싱된 딕셔너리

        Raises:
            ValueError: JSON 파싱 실패
        """
        try:
            # JSON 블록 추출 (```json ... ``` 형식 처리)
            content = content.strip()
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}\n응답: {content}")
            raise ValueError(f"JSON 파싱 실패: {e}")

    def _validate_routing_result(self, result: dict[str, Any]) -> None:
        """라우팅 결과의 유효성을 검증합니다.

        Args:
            result: 파싱된 라우팅 결과

        Raises:
            ValueError: 유효하지 않은 결과
        """
        # 필수 필드 확인
        if "worker" not in result:
            raise ValueError("'worker' 필드가 없습니다")

        # Worker 이름 검증
        worker = result["worker"]
        if worker not in self.VALID_WORKERS:
            logger.warning(f"유효하지 않은 Worker: {worker}, 기본값 사용")
            result["worker"] = self.DEFAULT_WORKER

        # confidence 범위 검증
        if "confidence" in result:
            confidence = result["confidence"]
            if not (0.0 <= confidence <= 1.0):
                logger.warning(f"confidence 범위 초과: {confidence}, 0.5로 설정")
                result["confidence"] = 0.5

    def _get_fallback_result(self) -> dict[str, Any]:
        """파싱 실패 시 기본값 결과를 반환합니다.

        Returns:
            기본값 라우팅 결과
        """
        return {
            "worker": self.DEFAULT_WORKER,
            "confidence": 0.5,
            "reasoning": "라우팅 실패, 기본 Worker 선택",
        }
