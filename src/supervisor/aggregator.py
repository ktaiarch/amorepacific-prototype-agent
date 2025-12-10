"""Supervisor Aggregator - Worker 응답 통합 및 포맷팅."""

from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Aggregator:
    """Worker 응답을 통합하고 사용자 친화적으로 포맷팅하는 Aggregator."""

    MAX_SOURCES = 3  # 최대 출처 개수

    def format_response(
        self,
        worker_name: str,
        worker_response: dict[str, Any],
        query: str | None = None,
    ) -> str:
        """Worker 응답을 사용자 친화적으로 포맷팅합니다.

        Args:
            worker_name: Worker 이름 (예: "원료", "처방", "규제")
            worker_response: Worker 응답 딕셔너리
            query: 원본 질의 (선택사항, 로깅용)

        Returns:
            포맷팅된 응답 문자열

        Example:
            >>> aggregator = Aggregator()
            >>> response = {
            ...     "content": "비타민C는 강력한 항산화제입니다.",
            ...     "sources": [{"title": "원료DB", "url": "http://..."}]
            ... }
            >>> result = aggregator.format_response("원료", response)
            >>> print(result)
            비타민C는 강력한 항산화제입니다.

            📚 **참고 문서**:
            1. 원료DB ([링크](http://...))

            _🤖 원료 Agent가 응답했습니다._
        """
        content = worker_response.get("content", "")
        sources = worker_response.get("sources", [])

        # 기본 응답
        formatted = content

        # 출처 정보 추가
        if sources:
            formatted += "\n\n📚 **참고 문서**:\n"
            for i, source in enumerate(sources[: self.MAX_SOURCES], 1):
                title = source.get("title") or "Unknown"
                formatted += f"{i}. {title}"

                # URL이 있으면 링크 추가
                if source.get("url"):
                    url = source["url"]
                    formatted += f" ([링크]({url}))"

                formatted += "\n"

        # Worker 정보 추가 (일반 대화가 아닌 경우만)
        if worker_name != "일반":
            formatted += f"\n\n_🤖 {worker_name} Agent가 응답했습니다._"

        logger.info(f"응답 포맷팅 완료: worker={worker_name}, query={query}")

        return formatted

    def combine_multiple_responses(
        self, responses: list[dict[str, Any]]
    ) -> str:
        """여러 Worker의 응답을 통합합니다.

        향후 멀티홉 쿼리 지원 시 사용.

        Args:
            responses: Worker 응답 리스트

        Returns:
            통합된 응답 문자열

        Note:
            현재 프로토타입에서는 단일 Worker만 호출하므로 미구현.
            향후 확장 시 구현 예정.
        """
        # TODO: 멀티홉 쿼리 지원 시 구현
        logger.warning("combine_multiple_responses는 아직 구현되지 않았습니다.")
        return ""
