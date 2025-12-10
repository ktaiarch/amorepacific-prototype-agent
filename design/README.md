# 설계 문서

Microsoft Agent Framework 기반 화장품 R&D 검색 시스템 설계 문서입니다.

## 📁 문서 구조

### 01-orchestrator-design.md
전체 시스템 진입점 및 세션/컨텍스트 관리

- Orchestrator: 전체 플로우 통합
- SessionManager: 세션 생성/관리 (AgentThread 기반)
- ContextManager: 대화 컨텍스트 관리
- Streamlit UI

### 02-supervisor-agent-design.md
Agent-as-Tool 패턴으로 Worker 자동 선택

- SupervisorAgent: ChatAgent + Worker Tools
- Aggregator: 응답 포맷팅
- Worker Tool 래핑

### 03-worker-agent-design.md
도메인별 검색 Agent 구현

- BaseWorker: Worker 공통 기능
- IngredientWorker: 원료 검색 (ReAct 패턴)
- Azure AI Search Tools

## 🎯 핵심 설계 결정

### Agent-as-Tool 패턴
LLM이 직접 적절한 Worker를 Tool로 선택하도록 구현했습니다. 별도의 Router 없이 ChatAgent가 자동으로 라우팅합니다.

### AgentThread 기반 세션
Microsoft Agent Framework의 AgentThread를 활용하여 세션과 메시지 히스토리를 통합 관리합니다.

### ReAct 패턴
Worker Agent는 ReAct 패턴으로 자율적으로 Tool을 선택하고 반복 검색을 수행합니다.

## 시스템 아키텍처

```
User
  ↓
Streamlit UI
  ↓
Orchestrator (세션/컨텍스트 관리)
  ↓
SupervisorAgent (Agent-as-Tool)
  ├─→ IngredientWorker (원료 검색)
  ├─→ FormulaWorker (처방 검색) *향후
  └─→ RegulationWorker (규제 검색) *향후
       ↓
  Azure AI Search
```

## �️ 모듈 구성

```
src/
├── orchestrator/
│   ├── orchestrator.py         # 전체 플로우 통합
│   ├── session_manager.py      # AgentThread 세션 관리
│   ├── context_manager.py      # 대화 컨텍스트 관리
│   └── models.py               # 데이터 모델
│
├── supervisor/
│   ├── supervisor.py           # SupervisorAgent (Agent-as-Tool)
│   ├── worker_tools.py         # Worker를 Tool로 변환
│   ├── aggregator.py           # 응답 포맷팅
│   └── prompts.py              # 시스템 프롬프트
│
├── workers/
│   ├── base.py                 # BaseWorker
│   ├── ingredient.py           # IngredientWorker
│   └── tools/
│       ├── search_tools.py     # Azure AI Search Tools
│       └── models.py           # Tool 모델
│
├── ui/
│   └── app.py                  # Streamlit 웹 UI
│
└── utils/
    ├── logger.py               # 로깅
    ├── config.py               # 환경변수
    └── errors.py               # 예외 클래스
```
- [ ] Streamlit 웹 UI 구현
- [ ] 대화 히스토리 표시
- [ ] 응답 포맷팅 개선

**Day 8-9: 테스트 및 문서화**
- [ ] 단위 테스트 작성
- [ ] 통합 테스트
- [ ] README 및 개발 가이드 작성

**Day 10: 데모**
- [ ] 기본 시나리오 3개 검증
- [ ] 최종 데모
- [ ] 회고 보고서 작성

## 🧪 검증 시나리오

### 필수 시나리오 (Must Have)

1. **원료 검색**: "Cetearyl Alcohol 원료 찾아줘"
   - Orchestrator → Supervisor → 원료 Worker → Azure AI Search
   - 원료명, CAS No., 발주 상태 응답

2. **필터 검색**: "발주완료된 원료 목록 보여줘"
   - search_with_filter Tool 사용
   - 발주 상태 필터링

3. **특정 정보 조회**: "글리세린의 CAS 번호는?"
   - 특정 필드 추출
   - 간결한 응답

### 확장 시나리오 (Nice to Have)

4. **멀티턴 대화**: "방금 검색한 원료 상세 정보 알려줘"
   - 대화 컨텍스트 활용

5. **에러 핸들링**: "존재하지 않는 원료 검색"
   - 적절한 에러 메시지

## 📚 참고 자료

### uv (Python 패키지 관리)
- [공식 문서](https://docs.astral.sh/uv/)
- [빠른 시작 가이드](https://docs.astral.sh/uv/getting-started/)
- 설치: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- 프로젝트 초기화: `uv init`
- 패키지 설치: `uv add <package>`
- 실행: `uv run python src/main.py`

### Microsoft Agent Framework
- [공식 문서](https://learn.microsoft.com/en-us/azure/ai-services/agents/)
- [GitHub 예제](https://github.com/microsoft/semantic-kernel)

### Azure AI Search
- [Python SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/search-documents-readme)
- [OData 필터 문법](https://learn.microsoft.com/en-us/azure/search/search-query-odata-filter)

### Streamlit
- [공식 문서](https://docs.streamlit.io/)
- [Chat UI 예제](https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps)

---

**문서 버전**: 1.0  
**작성일**: 2025-12-08  
**작성자**: KT 프로젝트 팀
