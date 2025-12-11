"""Worker Tool 함수 - Agent-as-Tool 패턴."""

from typing import Annotated, Any

from pydantic import Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


async def search_ingredient_tool(
    query: Annotated[str, Field(description="원료 관련 검색 질의")],
    ingredient_worker: Any = None,
) -> str:
    """원료 정보를 검색합니다.

    사용 시점:
    - 원료 이름, CAS 번호, 성분 정보 검색
    - 원료 스펙, 발주 상태 확인
    - INCI 명명법, 화학 구조 정보

    Args:
        query: 원료 관련 검색 질의
        ingredient_worker: IngredientWorker 인스턴스 (주입)

    Returns:
        원료 검색 결과 문자열
        
    Raises:
        ValueError: ingredient_worker가 주입되지 않은 경우
    """
    logger.info(f"원료 검색 Tool 호출: query={query}")

    if ingredient_worker is None:
        error_msg = "IngredientWorker가 주입되지 않았습니다."
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        response = await ingredient_worker.process(query, context=None)
        return response.get("content", "원료 정보를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"원료 검색 실패: {e}", exc_info=True)
        return f"원료 검색 중 오류 발생: {str(e)}"


async def search_formula_tool(
    query: Annotated[str, Field(description="처방 관련 검색 질의")],
    formula_worker: Any = None,
) -> str:
    """처방 정보를 검색합니다.

    사용 시점:
    - 처방 구성, 원료 함량 확인
    - 제품 포뮬라 검색
    - 처방 이력, 제형 정보

    Args:
        query: 처방 관련 검색 질의
        formula_worker: FormulaWorker 인스턴스 (주입)

    Returns:
        처방 검색 결과 문자열
        
    Raises:
        ValueError: formula_worker가 주입되지 않은 경우
    """
    logger.info(f"처방 검색 Tool 호출: query={query}")

    if formula_worker is None:
        error_msg = "FormulaWorker가 주입되지 않았습니다."
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        response = await formula_worker.process(query, context=None)
        return response.get("content", "처방 정보를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"처방 검색 실패: {e}", exc_info=True)
        return f"처방 검색 중 오류 발생: {str(e)}"


async def search_regulation_tool(
    query: Annotated[str, Field(description="규제 관련 검색 질의")],
    regulation_worker: Any = None,
) -> str:
    """규제 정보를 검색합니다.

    사용 시점:
    - 국가별 허용/금지 성분 확인
    - 함량 제한, 사용 제한 검색
    - 인증 요건, 라벨링 규정

    Args:
        query: 규제 관련 검색 질의
        regulation_worker: RegulationWorker 인스턴스 (주입)

    Returns:
        규제 검색 결과 문자열
        
    Raises:
        ValueError: regulation_worker가 주입되지 않은 경우
    """
    logger.info(f"규제 검색 Tool 호출: query={query}")

    if regulation_worker is None:
        error_msg = "RegulationWorker가 주입되지 않았습니다."
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        response = await regulation_worker.process(query, context=None)
        return response.get("content", "규제 정보를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"규제 검색 실패: {e}", exc_info=True)
        return f"규제 검색 중 오류 발생: {str(e)}"


def create_worker_tools(workers: dict[str, Any]) -> list:
    """Worker 딕셔너리로부터 Tool 함수 리스트를 생성합니다.

    Args:
        workers: {"원료": IngredientWorker, "처방": FormulaWorker, ...}

    Returns:
        Tool 함수 리스트
    """
    tools = []

    # 원료 Worker → Tool
    if "원료" in workers:
        ingredient_worker = workers["원료"]

        async def search_ingredient(
            query: Annotated[str, Field(description="원료 관련 검색 질의")]
        ) -> str:
            return await search_ingredient_tool(query, ingredient_worker)

        tools.append(search_ingredient)

    # 처방 Worker → Tool
    if "처방" in workers:
        formula_worker = workers["처방"]

        async def search_formula(
            query: Annotated[str, Field(description="처방 관련 검색 질의")]
        ) -> str:
            return await search_formula_tool(query, formula_worker)

        tools.append(search_formula)

    # 규제 Worker → Tool
    if "규제" in workers:
        regulation_worker = workers["규제"]

        async def search_regulation(
            query: Annotated[str, Field(description="규제 관련 검색 질의")]
        ) -> str:
            return await search_regulation_tool(query, regulation_worker)

        tools.append(search_regulation)

    logger.info(f"Worker Tools 생성 완료: {len(tools)}개")
    return tools
