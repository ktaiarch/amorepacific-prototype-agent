# 화장품 R&D 검색 시스템

Microsoft Agent Framework 기반 멀티 에이전트 검색 시스템입니다.

## 개요

화장품 연구개발(R&D)에 필요한 원료, 처방, 규제 정보를 검색할 수 있는 대화형 AI 시스템입니다. Agent-as-Tool 패턴과 ReAct 패턴을 활용하여 사용자 질의에 적합한 Worker를 자동 선택하고, Azure AI Search를 통해 정보를 검색합니다.

## 주요 기능

- **멀티턴 대화**: 이전 대화 컨텍스트를 유지하며 연속적인 질의 가능
- **자동 라우팅**: LLM이 질의를 분석하여 적절한 Worker 자동 선택
- **원료 검색**: 화장품 원료의 기본 정보, 스펙, 발주 상태 조회
- **세션 관리**: 사용자별 세션 생성 및 대화 히스토리 관리
- **웹 UI**: Streamlit 기반 사용자 친화적 인터페이스

## 아키텍처

```
User Interface (Streamlit)
         ↓
    Orchestrator (세션/컨텍스트 관리)
         ↓
  SupervisorAgent (Agent-as-Tool 패턴)
         ↓
  IngredientWorker (ReAct 패턴)
         ↓
   Azure AI Search
```

### 핵심 패턴

- **Agent-as-Tool**: Worker를 Tool로 래핑하여 ChatAgent가 자동 선택
- **ReAct**: Worker가 추론-행동-관찰을 반복하며 검색 수행
- **AgentThread**: Microsoft Agent Framework의 세션 관리 활용

## 시작하기

### 필수 요구사항

- Python 3.11+
- Azure OpenAI 계정
- Azure AI Search (선택사항, Mock 모드 지원)

### 설치

```bash
# 1. 저장소 클론
git clone <repository-url>
cd prototype

# 2. uv로 의존성 설치
uv sync

# 3. 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 Azure 정보 입력
```

### 환경변수 설정

`.env` 파일에 다음 항목을 설정합니다:

```bash
# Azure OpenAI (필수)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME=gpt-4o

# Azure AI Search (선택, Mock 모드 사용 시 불필요)
USE_MOCK_SEARCH=true
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=cosmetic-raw-materials
```

### 실행

#### Streamlit UI 실행

```bash
uv run streamlit run src/ui/app.py
```

브라우저에서 http://localhost:8501 접속

#### IngredientWorker 데모 실행

5가지 다양한 질의를 처리하는 데모 스크립트:

```bash
# Mock 모드로 실행 (Azure AI Search 불필요)
export USE_MOCK_SEARCH=true
uv run python examples/demo_ingredient_worker.py

# Azure AI Search 모드로 실행 (실제 데이터베이스 사용)
USE_MOCK_SEARCH=false uv run python examples/demo_ingredient_worker.py
```

데모에서 테스트하는 질의:

1. 간단한 원료명 검색: "글리세린 원료 찾아줘"
2. 영문명 + 함량 필터: "Cetearyl Alcohol 100%인 원료만"
3. 한글명 + 발주 상태: "나이아신아마이드 발주완료된 것만"
4. CAS 번호 검색: "CAS 번호가 56-81-5인 원료"
5. 복합 조건: "점도가 높은 보습 원료 추천"

출력 결과:

- 각 질의에 대한 응답
- 참조 문서 (원료 정보)
- 처리 시간 및 통계

**Azure AI Search 사용 시:**
- 실제 인덱스에서 검색 수행
- 하이브리드 검색 (키워드 + 시맨틱) 적용
- 필터 기능 (발주 상태 등) 활용

#### 프로그래밍 방식 사용

```python
from agent_framework.azure import AzureOpenAIResponsesClient
from src.orchestrator import Orchestrator

# Orchestrator 생성
chat_client = AzureOpenAIResponsesClient(...)
orchestrator = Orchestrator.create_default(chat_client)

# 쿼리 처리
result = await orchestrator.process_query(
    user_id="user123",
    query="글리세린 CAS 번호는?"
)

print(result["response"]["content"])
```

## 테스트

전체 테스트 실행:

```bash
uv run pytest
```

특정 테스트 실행:

```bash
# 유닛 테스트
uv run pytest tests/test_orchestrator.py

# 통합 테스트
uv run pytest tests/integration/

# E2E 테스트
uv run pytest tests/e2e/
```

테스트 커버리지:

```bash
uv run pytest --cov=src --cov-report=html
```

## 프로젝트 구조

```
prototype/
├── src/
│   ├── orchestrator/      # 전체 플로우 통합
│   ├── supervisor/        # Agent-as-Tool 패턴
│   ├── workers/           # 도메인별 Worker Agent
│   ├── ui/                # Streamlit 웹 UI
│   └── utils/             # 유틸리티
├── tests/                 # 테스트
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── design/                # 설계 문서
├── index/                 # Azure AI Search 인덱스 설정
└── data/                  # Mock 데이터
```

## 모듈 설명

### Orchestrator
전체 시스템의 진입점으로 세션 관리와 대화 컨텍스트를 유지합니다.

- `SessionManager`: AgentThread 기반 세션 관리 (TTL 30분)
- `ContextManager`: 대화 히스토리 관리 (최근 5턴)
- `Orchestrator`: Supervisor 호출 및 응답 처리

### SupervisorAgent
Agent-as-Tool 패턴으로 Worker를 자동 선택합니다.

- Worker를 Tool로 변환
- ChatAgent가 질의 분석 후 적절한 Tool 선택
- Aggregator로 응답 포맷팅

### Worker
도메인별 검색을 ReAct 패턴으로 수행합니다.

- `IngredientWorker`: 원료 검색 (현재 구현됨)
- `FormulaWorker`: 처방 검색 (향후)
- `RegulationWorker`: 규제 검색 (향후)

## Azure AI Search 설정

Mock 모드 대신 실제 Azure AI Search 사용:

```bash
# 1. 인덱스 생성 및 데이터 업로드
cd index
uv run python setup_cosmetic_index.py

# 2. 환경변수 변경
USE_MOCK_SEARCH=false
```

자세한 내용은 [`index/README.md`](index/README.md) 참조

## 📚 문서

### 설계 문서

상세한 설계 문서는 `design/` 디렉토리 참조:

- [설계 개요](design/README.md) - 전체 아키텍처 및 핵심 설계 결정
- [Orchestrator 설계](design/01-orchestrator-design.md) - 세션/컨텍스트 관리 및 UI
- [Supervisor 설계](design/02-supervisor-agent-design.md) - Agent-as-Tool 패턴
- [Worker 설계](design/03-worker-agent-design.md) - 도메인별 검색 Agent

### 모듈별 가이드

- [Streamlit UI 실행 가이드](src/ui/README.md) - UI 실행 방법 및 트러블슈팅
- [Azure AI Search 인덱스 설정](index/README.md) - 인덱스 생성 및 데이터 업로드

## 개발 가이드

### 새로운 Worker 추가

1. `src/workers/` 에 새 Worker 클래스 작성 (BaseWorker 상속)
2. 시스템 프롬프트 정의
3. `Orchestrator.create_default()`에 Worker 등록

```python
from src.workers import BaseWorker

class MyWorker(BaseWorker):
    def __init__(self, chat_client, tools):
        super().__init__(
            chat_client=chat_client,
            instructions="...",
            tools=tools
        )
    
    async def process(self, query, context):
        # 구현
        pass
```
