"""원료 검색 Worker Agent

화장품 원료의 기본 정보, 스펙, 발주 상태를 검색합니다.
"""

from datetime import datetime
from typing import Any

from .base import BaseWorker
from ..utils.logger import get_logger

logger = get_logger(__name__)

INGREDIENT_INSTRUCTIONS = """당신은 화장품 원료 검색 전문 에이전트입니다.

[담당 업무]
- 원료 기본 정보 검색 (성분, 한글명, 영문명, CAS No.)
- 원료 스펙 조회 (점도, pH, 함량 등)
- 발주 상태 확인 (발주완료, 검토중, 중단)

[검색 전략]
1. 먼저 search_documents로 키워드 검색을 시도합니다
2. 필터 조건이 필요하면 search_with_filter를 사용합니다
3. 검색 결과가 없으면 다른 검색어로 재시도합니다
4. 여러 결과가 있으면 가장 관련성 높은 결과를 우선합니다

[응답 규칙]
- 검색 결과가 없으면 "검색 결과가 없습니다"라고 명확히 알립니다
- 원료코드, 원료명, CAS 번호, 발주 상태를 포함합니다
- 출처(문서명 또는 ID)를 반드시 명시합니다
"""


class IngredientWorker(BaseWorker):
    """원료 검색 Worker Agent
    
    화장품 R&D에서 필요한 원료 정보를 검색하고 제공합니다.
    Azure AI Search를 통해 원료 데이터베이스를 조회합니다.
    
    Attributes:
        agent: Microsoft Agent Framework의 ChatAgent (BaseWorker에서 상속)
        instructions: 원료 검색 전문 시스템 프롬프트
        tools: search_documents, search_with_filter 등
    
    Examples:
        >>> from agent_framework.azure import AzureOpenAIResponsesClient
        >>> from workers.tools import search_documents, search_with_filter, get_search_client_manager
        >>> 
        >>> # 1. Search Client 초기화
        >>> manager = get_search_client_manager()
        >>> manager.initialize()
        >>> 
        >>> # 2. Worker 생성
        >>> client = AzureOpenAIResponsesClient()
        >>> tools = [search_documents, search_with_filter]
        >>> worker = IngredientWorker(client, tools)
        >>> 
        >>> # 3. 검색
        >>> result = await worker.process("글리세린 원료 찾아줘")
        >>> print(result["content"])
        >>> print(result["sources"])
    """

    def __init__(self, chat_client: Any, tools: list[Any]):
        """원료 검색 Worker를 초기화합니다.
        
        Args:
            chat_client: Azure OpenAI 클라이언트
            tools: 검색 Tool 함수 목록 (search_documents, search_with_filter)
        
        Examples:
            >>> from workers.tools import search_documents, search_with_filter
            >>> tools = [search_documents, search_with_filter]
            >>> worker = IngredientWorker(chat_client, tools)
        """
        super().__init__(
            chat_client=chat_client,
            instructions=INGREDIENT_INSTRUCTIONS,
            tools=tools,
        )
        logger.info("IngredientWorker 초기화 완료")

    async def process(
        self,
        query: str,
        context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """원료 검색 쿼리를 처리합니다.
        
        사용자 질의를 받아 Azure AI Search에서 원료를 검색하고,
        ReAct 패턴으로 자율적으로 Tool을 선택하여 실행합니다.
        
        Args:
            query: 사용자 질의
                예: "글리세린 원료 찾아줘"
                    "Cetearyl Alcohol 100% 발주완료된 것만"
            context: 대화 컨텍스트 (이전 메시지들, 선택사항)
        
        Returns:
            검색 결과
            {
                "content": str,           # 최종 응답 텍스트
                "sources": list[dict],    # 참조한 원료 문서
                "timestamp": datetime,    # 응답 시각
                "metadata": dict          # 반복 횟수, 사용된 Tool 등
            }
        
        Examples:
            >>> result = await worker.process("나이아신아마이드 원료 찾아줘")
            >>> print(result["content"])
            '나이아신아마이드(Niacinamide) 원료를 찾았습니다...'
            >>> print(result["sources"][0])
            {'title': '나이아신아마이드', 'id': 'RM005', 'score': 5.2}
        """
        logger.info(f"원료 검색 시작: query='{query[:50]}...'")
        
        # ReAct 패턴으로 실행
        result = await self._execute_react(query, max_iterations=5, timeout=30)
        
        # 응답 포맷팅
        response = {
            "content": result.get("content", ""),
            "sources": self._extract_sources(result),
            "timestamp": datetime.now(),
            "metadata": {
                "iterations": result.get("iterations", 1),
                "tools_used": result.get("tools_used", []),
                "worker_type": "ingredient",
            },
        }
        
        logger.info(
            f"원료 검색 완료: sources={len(response['sources'])}, "
            f"iterations={response['metadata']['iterations']}"
        )
        
        return response

    def _format_ingredient_response(
        self,
        documents: list[dict[str, Any]],
    ) -> str:
        """검색된 원료 문서를 사용자 친화적인 응답으로 포맷팅합니다.
        
        Args:
            documents: Azure AI Search 결과 문서 목록
        
        Returns:
            포맷팅된 응답 텍스트
        
        Examples:
            >>> docs = [
            ...     {
            ...         "ingredient_name_ko": "글리세린",
            ...         "ingredient_name_en": "Glycerin",
            ...         "cas_no": "56-81-5",
            ...         "order_status": "발주완료"
            ...     }
            ... ]
            >>> response = worker._format_ingredient_response(docs)
            >>> print(response)
            '글리세린(Glycerin) 원료를 찾았습니다...'
        """
        if not documents:
            return "검색 결과가 없습니다."
        
        # 여러 원료 발견 시
        if len(documents) > 1:
            lines = [f"총 {len(documents)}개의 원료를 찾았습니다:\n"]
            for i, doc in enumerate(documents[:5], 1):  # 최대 5개만
                name_ko = doc.get("ingredient_name_ko", "알 수 없음")
                name_en = doc.get("ingredient_name_en", "")
                cas_no = doc.get("cas_no", "")
                status = doc.get("order_status", "")
                
                line = f"{i}. {name_ko}"
                if name_en:
                    line += f" ({name_en})"
                if cas_no:
                    line += f" - CAS: {cas_no}"
                if status:
                    line += f" - {status}"
                lines.append(line)
            
            return "\n".join(lines)
        
        # 단일 원료 발견 시
        doc = documents[0]
        name_ko = doc.get("ingredient_name_ko", "알 수 없음")
        name_en = doc.get("ingredient_name_en", "")
        cas_no = doc.get("cas_no", "")
        status = doc.get("order_status", "")
        
        response = f"{name_ko}"
        if name_en:
            response += f"({name_en})"
        response += " 원료를 찾았습니다.\n"
        
        if cas_no:
            response += f"- CAS 번호: {cas_no}\n"
        if status:
            response += f"- 발주 상태: {status}\n"
        
        return response
