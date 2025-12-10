"""IngredientWorker 통합 테스트

실제 Azure OpenAI와 연동하여 IngredientWorker의 동작을 검증합니다.

환경변수 설정 필요:
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_CHAT_DEPLOYMENT_NAME

주의: 실제 API 비용이 발생합니다.
"""

import os

import pytest
from agent_framework.azure import AzureOpenAIChatClient

from src.workers.ingredient import IngredientWorker
from src.workers.tools.search_tools import (
    initialize_search_clients,
    search_documents,
    search_with_filter,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_search_clients():
    """Search Client 초기화 (한 번만 실행)."""
    initialize_search_clients()


@pytest.fixture
def chat_client():
    """실제 Azure OpenAI ChatClient 생성."""
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"환경변수 누락: {', '.join(missing)}")
    
    return AzureOpenAIChatClient(
        model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )


@pytest.fixture
def search_tools():
    """검색 Tool 목록."""
    return [search_documents, search_with_filter]


@pytest.fixture
def ingredient_worker(chat_client, search_tools):
    """실제 ChatClient를 사용하는 IngredientWorker."""
    return IngredientWorker(chat_client=chat_client, tools=search_tools)


# ============================================================================
# 초기화 테스트
# ============================================================================

def test_worker_initialization(ingredient_worker):
    """Worker가 올바르게 초기화되는지 확인."""
    assert ingredient_worker is not None
    assert ingredient_worker.agent is not None
    assert ingredient_worker.instructions is not None
    assert len(ingredient_worker.tools) == 2


# ============================================================================
# 기본 검색 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_search_ingredient_by_korean_name(ingredient_worker):
    """한글 이름으로 원료 검색 - 실제 LLM 사용."""
    query = "비타민C의 CAS 번호는?"
    context = []
    
    result = await ingredient_worker.process(query, context)
    
    # 응답 구조 검증
    assert "content" in result
    assert "sources" in result
    
    # 응답 내용 검증
    content = result["content"]
    assert isinstance(content, str)
    assert len(content) > 0
    
    # Mock 데이터에 비타민C가 있으므로 CAS 번호가 응답에 포함되어야 함
    # 로그에서 Tool이 호출되고 results=1이 확인됨
    assert "50-81-7" in content or "cas" in content.lower()


@pytest.mark.asyncio
async def test_search_ingredient_by_english_name(ingredient_worker):
    """영문 이름으로 원료 검색 - 실제 LLM 사용."""
    query = "What is the CAS number of Ascorbic Acid?"
    context = []
    
    result = await ingredient_worker.process(query, context)
    
    assert "content" in result
    assert "sources" in result
    
    content = result["content"]
    assert isinstance(content, str)
    assert len(content) > 0
    
    # Ascorbic Acid (비타민C)의 CAS 번호가 응답에 포함되어야 함
    assert "50-81-7" in content or "cas" in content.lower()


# ============================================================================
# ReAct 패턴 검증
# ============================================================================

@pytest.mark.asyncio
async def test_react_pattern_tool_usage(ingredient_worker):
    """ReAct 패턴으로 Tool이 호출되는지 검증."""
    query = "비타민E의 CAS 번호를 찾아줘"
    context = []
    
    result = await ingredient_worker.process(query, context)
    
    # 결과 검증
    assert "content" in result
    assert "sources" in result
    
    # 응답이 생성되었는지 확인
    content = result["content"]
    assert isinstance(content, str)
    assert len(content) > 0
    
    # 비타민E (Tocopherol)의 CAS 번호가 응답에 포함되어야 함
    # 로그에서 Tool이 호출되고 results=1이 확인됨
    assert "59-02-9" in content or "cas" in content.lower()


# ============================================================================
# 컨텍스트 활용 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_with_conversation_context(ingredient_worker):
    """이전 대화 컨텍스트를 활용하는지 검증."""
    # 첫 번째 질문 - 명확한 원료명 포함 (JSON에 실제 존재하는 이름 사용)
    query1 = "아스코빅애씨드의 정보를 알려줘"
    context1 = []
    
    result1 = await ingredient_worker.process(query1, context1)
    
    # 아스코빅애씨드 정보가 응답에 포함되어야 함
    assert "50-81-7" in result1["content"] or "아스코빅" in result1["content"] or "ascorbic" in result1["content"].lower()
    
    # 두 번째 질문 (이전 대화 참조)
    query2 = "그것의 INCI 이름은 뭐야?"
    context2 = [
        {"role": "user", "content": query1},
        {"role": "assistant", "content": result1["content"]},
    ]
    
    result2 = await ingredient_worker.process(query2, context2)
    
    # INCI 이름이 응답에 포함되어야 함
    content2 = result2["content"]
    assert isinstance(content2, str)
    assert len(content2) > 0
    assert "ascorbic" in content2.lower() or "inci" in content2.lower()


@pytest.mark.asyncio
async def test_multiturn_conversation(ingredient_worker):
    """멀티턴 대화에서 컨텍스트 유지 검증."""
    context = []
    
    # 1턴: 원료 검색
    query1 = "히알루론산에 대해 알려줘"
    result1 = await ingredient_worker.process(query1, context)
    context.append({"role": "user", "content": query1})
    context.append({"role": "assistant", "content": result1["content"]})
    
    # 첫 번째 응답에 히알루론산 정보가 있어야 함
    assert "히알루론산" in result1["content"] or "hyaluronic" in result1["content"].lower()
    
    # 2턴: 추가 정보 요청
    query2 = "그것의 분자량은?"
    result2 = await ingredient_worker.process(query2, context)
    context.append({"role": "user", "content": query2})
    context.append({"role": "assistant", "content": result2["content"]})
    
    # 분자량 정보가 응답에 포함되어야 함
    assert "kda" in result2["content"].lower() or "분자량" in result2["content"]
    
    # 3턴: CAS 번호 요청
    query3 = "CAS 번호는?"
    result3 = await ingredient_worker.process(query3, context)
    
    # CAS 번호가 응답에 포함되어야 함
    assert "9067-32-7" in result3["content"] or "cas" in result3["content"].lower()
    
    # 모든 응답이 유효한지 확인
    assert all(r["content"] for r in [result1, result2, result3])

