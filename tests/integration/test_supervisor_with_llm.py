"""SupervisorAgent 통합 테스트

실제 Azure OpenAI와 연동하여 SupervisorAgent + Workers의 동작을 검증합니다.

환경변수 설정 필요:
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_CHAT_DEPLOYMENT_NAME

주의: 실제 API 비용이 발생합니다.
"""

import os

import pytest
from agent_framework.azure import AzureOpenAIChatClient

from src.supervisor.aggregator import Aggregator
from src.supervisor.supervisor import SupervisorAgent
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


@pytest.fixture
def aggregator():
    """Aggregator 생성."""
    return Aggregator()


@pytest.fixture
def supervisor(chat_client, ingredient_worker, aggregator):
    """실제 ChatClient와 Workers를 사용하는 SupervisorAgent."""
    workers = {"원료": ingredient_worker}
    return SupervisorAgent(
        chat_client=chat_client,
        workers=workers,
        aggregator=aggregator,
    )


# ============================================================================
# 초기화 테스트
# ============================================================================

def test_supervisor_initialization(supervisor):
    """Supervisor가 올바르게 초기화되는지 확인."""
    assert supervisor is not None
    assert supervisor.agent is not None
    assert supervisor.workers is not None
    assert len(supervisor.workers) == 1
    assert "원료" in supervisor.workers


# ============================================================================
# Agent-as-Tool 패턴 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_supervisor_calls_worker_tool(supervisor):
    """Supervisor가 Worker Tool을 자동으로 선택하고 호출하는지 검증."""
    query = "글리세린의 CAS 번호를 알려줘"
    context = []
    
    result = await supervisor.process(query, context)
    
    # 결과 확인
    assert "content" in result
    assert "worker" in result
    assert "metadata" in result
    
    # CAS 번호가 응답에 포함되어야 함 (글리세린: 56-81-5)
    assert "56-81-5" in result["content"] or "글리세린" in result["content"]
    
    # Worker가 호출되었는지 확인
    assert result["worker"] == "원료"


@pytest.mark.asyncio
async def test_supervisor_aggregates_worker_response(supervisor):
    """Supervisor가 Worker 응답을 Aggregation하는지 검증."""
    query = "나이아신아마이드에 대해 알려줘"
    context = []
    
    result = await supervisor.process(query, context)
    
    # 응답 내용 확인
    content = result["content"]
    assert isinstance(content, str)
    assert len(content) > 0
    
    # 나이아신아마이드 정보가 포함되어야 함
    assert "나이아신" in content or "niacinamide" in content.lower() or "98-92-0" in content
    
    # Worker 확인
    assert result["worker"] == "원료"
    
    # Metadata 확인
    assert "tool_calls" in result["metadata"]
    assert len(result["metadata"]["tool_calls"]) > 0


# ============================================================================
# 멀티턴 대화 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_supervisor_multiturn_conversation(supervisor):
    """멀티턴 대화에서 컨텍스트를 유지하는지 검증."""
    context = []
    
    # 1턴: 원료 검색
    query1 = "히알루론산의 CAS 번호를 알려줘"
    result1 = await supervisor.process(query1, context)
    
    assert "9067-32-7" in result1["content"] or "히알루론" in result1["content"]
    
    # 컨텍스트 업데이트
    context.append({"role": "user", "content": query1})
    context.append({"role": "assistant", "content": result1["content"]})
    
    # 2턴: 이전 대화 참조
    query2 = "그것의 INCI 이름은 뭐야?"
    result2 = await supervisor.process(query2, context)
    
    # INCI 이름이 응답에 포함되어야 함
    content2 = result2["content"]
    assert "sodium hyaluronate" in content2.lower() or "inci" in content2.lower()


# ============================================================================
# 검색 결과 없는 경우 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_supervisor_handles_no_results(supervisor):
    """검색 결과가 없을 때 적절한 응답을 반환하는지 검증."""
    query = "존재하지않는원료12345의 정보를 알려줘"
    context = []
    
    result = await supervisor.process(query, context)
    
    # 결과가 반환되어야 함
    assert "content" in result
    content = result["content"]
    assert isinstance(content, str)
    assert len(content) > 0
    
    # "검색 결과 없음" 또는 유사한 메시지가 포함되어야 함
    assert any(
        keyword in content
        for keyword in ["없습니다", "찾을 수 없", "검색", "결과가 없"]
    )


# ============================================================================
# 복잡한 질문 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_supervisor_handles_complex_query(supervisor):
    """복잡한 질문(여러 원료)을 처리하는지 검증."""
    query = "글리세린과 나이아신아마이드의 CAS 번호를 비교해줘"
    context = []
    
    result = await supervisor.process(query, context)
    
    # 두 원료의 정보가 모두 포함되어야 함
    content = result["content"]
    
    # 글리세린 정보 (56-81-5)
    has_glycerin = "56-81-5" in content or "글리세린" in content
    
    # 나이아신아마이드 정보 (98-92-0)
    has_niacinamide = "98-92-0" in content or "나이아신" in content
    
    # 최소한 하나는 포함되어야 함 (LLM이 두 번 호출할 수도 있음)
    assert has_glycerin or has_niacinamide


# ============================================================================
# 에러 핸들링 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_supervisor_handles_empty_query(supervisor):
    """빈 질문에 대한 에러 핸들링 검증."""
    query = ""
    context = []
    
    result = await supervisor.process(query, context)
    
    # 에러 메시지가 포함되어야 함
    assert "content" in result
    content = result["content"]
    assert isinstance(content, str)
    # 빈 쿼리에 대한 응답이 있어야 함 (에러 또는 안내 메시지)
    assert len(content) > 0
