# 프로젝트 할 일 목록

## 1. 프로젝트 구조 생성

- [x] src/ 하위 디렉토리 생성 (orchestrator, supervisor, workers, ui, utils)
- **파일**: 디렉토리 구조

## 2. 의존성 패키지 추가

- [x] uv를 사용하여 필요한 패키지 설치
- **파일**: `pyproject.toml`

## 3. Utils 모듈 구현

- [x] errors.py - 예외 클래스 (AgentError, ConfigError, PluginError)
- [x] logger.py - 구조화된 로깅
- [x] config.py - 설정 관리 (환경변수)
- **파일**: `src/utils/errors.py`, `src/utils/logger.py`, `src/utils/config.py`

## 4. Orchestrator Models 구현

- [x] Session 모델 (세션 메타데이터)
- [x] QueryRequest/Response 모델
- [x] ChatMessage 활용 (Agent Framework 네이티브)
- **파일**: `src/orchestrator/models.py`

## 5. SessionManager 구현

- [x] AgentThread 래핑
- [x] 세션 생성/조회/삭제/업데이트
- [x] TTL 관리 (기본 30분)
- [x] Thread 관리 (message_store 활용)
- **파일**: `src/orchestrator/session_manager.py`

## 6. SessionManager 테스트

- [x] 세션 생성/조회/삭제 테스트
- [x] TTL 만료 테스트
- [x] Thread 통합 테스트
- [x] 사용법 문서화 (docstring)
- **파일**: `tests/test_session_manager.py`

## 7. ContextManager 구현

- [x] AgentThread.message_store 활용
- [x] 토큰 카운팅 (tiktoken)
- [x] 대화 컨텍스트 관리 (max_turns)
- [x] 토큰 제한 검증
- [x] Wrapper 패턴 (SessionManager 통합)
- **파일**: `src/orchestrator/context_manager.py`

## 8. ContextManager 테스트

- [x] 메시지 추가/조회 테스트
- [x] 토큰 카운팅 테스트
- [x] 컨텍스트 윈도우 테스트
- [x] 통합 시나리오 테스트
- **파일**: `tests/test_context_manager.py`

## 9. Worker Tools 구현

- [x] MockSearchClient (프로토타입용)
- [x] search_documents (기본 검색)
- [x] search_with_filter (필터 검색)
- [x] initialize_search_clients (환경변수 기반 전환)
- [x] Mock + 실제 Azure 전환 가능 설계
- **파일**: `src/workers/tools/search_tools.py`, `src/workers/tools/models.py`

## 10. Worker Tools 테스트

- [x] 검색 기능 테스트 (한글/영문)
- [x] 필터 기능 테스트
- [x] Mock 데이터 검증
- [x] 실제 사용 시나리오 테스트
- **파일**: `tests/test_search_tools.py`

## 11. BaseWorker 구현

- [x] Worker 추상 클래스
- [x] ReAct 패턴 실행 로직 (_execute_react)
- [x] Agent Framework 통합 (_run_agent)
- [x] 응답 파싱 (content, tools_used 추출)
- [x] 타임아웃 처리
- [x] 테스트 모드 지원 (chat_client=None)
- **파일**: `src/workers/base.py`

## 12. IngredientWorker 구현

- [x] BaseWorker 상속
- [x] 원료 검색 전문 시스템 프롬프트
- [x] ChatAgent + ReAct 패턴
- [x] 응답 포맷팅 (_format_ingredient_response)
- [x] Tool 통합 (search_documents, search_with_filter)
- **파일**: `src/workers/ingredient.py`

## 13. IngredientWorker 테스트

- [x] 초기화 테스트
- [x] 검색 기능 테스트
- [x] 응답 포맷팅 테스트
- [x] 통합 시나리오 테스트 (한글/영문 검색, 필터, 컨텍스트)
- [x] 엣지 케이스 테스트 (빈 쿼리, 긴 쿼리, 특수문자)
- **파일**: `tests/test_ingredient_worker.py`

## 14. ~~Supervisor Router 구현~~ (제거됨 - Agent-as-Tool 패턴으로 변경)

- [x] ~~LLM 기반 도메인 분류~~
- [x] ~~원료/처방/규제 라우팅~~
- [x] ~~컨텍스트 기반 의도 파악~~
- [x] ~~JSON 응답 파싱 (재시도 로직 포함)~~
- **삭제됨**: Router는 Agent-as-Tool 패턴으로 대체됨 (Agent가 자동 Tool 선택)

## 15. Supervisor Aggregator 구현

- [x] Worker 응답 통합
- [x] 템플릿 기반 포맷팅
- [x] 출처 정보 추가 (최대 3개)
- [x] 디버깅 정보 포함 (Worker 이름)
- [x] 엣지 케이스 처리 (None title, 빈 sources 등)
- **파일**: `src/supervisor/aggregator.py`
- **테스트**: `tests/test_aggregator.py` - 25개 통과

## 16. SupervisorAgent 구현 (Agent-as-Tool 패턴)

- [x] Worker를 Tool로 변환 (`create_worker_tools`)
- [x] ChatAgent에 Worker Tool 등록
- [x] Agent가 자동으로 적절한 Tool(Worker) 선택
- [x] Tool 호출 정보 추출 (`_extract_tool_calls`)
- [x] Worker 이름 추출 (`_extract_worker_name_from_response`)
- [x] 에러 핸들링
- [x] ~~테스트 모드 지원 (chat_client=None)~~ → **프로덕션 코드 단순화 (DI 패턴)**
- [x] **코드 품질 개선**: 테스트 로직 분리, SRP 준수, 38줄 감소
- **파일**: `src/supervisor/supervisor.py`, `src/supervisor/worker_tools.py`
- **테스트**: `tests/test_supervisor.py` - 20개 통과 (Mock 기반 단위 테스트)

## 17. ~~SupervisorAgent 테스트~~ (16번에 통합 완료)

- [x] Agent-as-Tool 패턴 테스트
- [x] Worker Tool 자동 선택 테스트
- [x] 응답 추출 메서드 테스트
- [x] Mock 기반 단위 테스트 (ChatAgent patch)
- [x] `create_mock_tool_call` 헬퍼 함수
- **파일**: `tests/test_supervisor.py` - 20개 통과

## 18. Orchestrator 구현

- [x] SessionManager + ContextManager + Supervisor 통합
- [x] process_query() 메서드 (세션 관리, 컨텍스트 추가, Supervisor 호출)
- [x] clear_session() 메서드
- [x] create_default() 팩토리 메서드
- [x] 에러 핸들링
- **파일**: `src/orchestrator/orchestrator.py`
- **테스트**: `tests/test_orchestrator.py` - 19개 통과 (TDD)

## 19. Orchestrator 테스트

- [x] 초기화 테스트 (2개)
- [x] process_query 테스트 (6개)
- [x] clear_session 테스트 (4개)
- [x] 멀티턴 대화 테스트 (2개)
- [x] 에러 핸들링 테스트 (3개)
- [x] 팩토리 메서드 테스트 (2개)
- **파일**: `tests/test_orchestrator.py` - 19개 통과

## 20. Streamlit UI 구현

- [x] 채팅 인터페이스 (사용자-AI 대화)
- [x] 세션 관리 UI (새 대화 버튼, 세션 정보 표시)
- [x] 대화 히스토리 표시 (메시지 렌더링)
- [x] 샘플 질의 버튼 (3개 샘플, pending_query 패턴)
- [x] 디버깅 정보 표시 (Worker, 응답 시간, 타임스탬프 - 기본 켜짐)
- [x] Orchestrator 연동 (비동기 처리)
- [x] 환경변수 설정 (.env.example, README.md)
- [x] 사이드바 UI (새 대화, 샘플 질의, 설정)
- **파일**: `src/ui/app.py` (257줄), `src/ui/README.md`, `.env.example`

## 21. Streamlit UI 테스트

- [x] 앱 실행 (http://localhost:8501)
- [x] 디버깅 정보 포맷 개선 (metric → text)
- [x] 샘플 질의 버튼 수정 (pending_query 패턴)
- [x] 디버깅 토글 기본값 변경 (켜짐)
- [ ] 전체 기능 통합 테스트
- **상태**: 실행 중, 기본 기능 동작 확인됨

## 22. Worker 통합 테스트 (Azure OpenAI 연동) ✅

- [x] IngredientWorker 실제 Azure OpenAI 연동 테스트
- [x] Mock 데이터를 cosmetic_raw_materials.json에서 로드 (45개 전체)
- [x] 실제 검색 쿼리 시나리오 테스트 (한글/영문)
- [x] ReAct 패턴 동작 검증 (Tool 호출 로그 확인, CAS 번호 응답 검증)
- [x] 컨텍스트 활용 테스트 (이전 대화 참조, 멀티턴)
- **완료**: Worker가 실제 LLM과 연동하여 올바르게 작동함을 검증
- **파일**: `tests/integration/test_worker_with_llm.py` (6개 통과, 17.87초)
- **Mock 데이터**: `src/workers/tools/search_tools.py` (JSON 파일 자동 로드)
- **결과**: ✅ 모든 테스트 통과 (188개 전체)
- **개선**:
  - MockSearchClient가 data/cosmetic_raw_materials.json 자동 로드
  - 45개 전체 원료 데이터로 테스트 (RM001~RM045)
  - 응답 내용 기반 검증 강화 (CAS 번호, INCI 이름 등)
  - 로그로 Tool 호출 확인 (search_documents 호출됨)
  
## 23. Supervisor 통합 테스트 (Worker Tool 호출) ✅

- [x] SupervisorAgent + 실제 IngredientWorker 통합 테스트
- [x] Agent-as-Tool 패턴 실제 동작 검증 (LLM이 Tool 자동 선택)
- [x] Worker Tool 자동 선택 검증 (원료 질문 → search_ingredient 호출)
- [x] 응답 Aggregation 검증 (Worker 응답 → 최종 사용자 응답)
- [x] 멀티턴 대화에서 컨텍스트 유지 검증
- [x] 검색 결과 없을 때 적절한 응답 검증
- [x] 복잡한 질문 처리 검증 (여러 원료 비교)
- [x] 빈 쿼리 에러 핸들링 검증
- **완료**: 7개 통합 테스트 모두 통과, 총 195개 테스트 통과
- **핵심 수정사항**:
  - `_extract_tool_calls` 메서드: Agent Framework의 FunctionCallContent 기반으로 수정
  - workers 딕셔너리 키: 영문 → 한글 ("ingredient_worker" → "원료")
  - 유닛 테스트 Mock 구조: Agent Framework 스타일로 변경
- **파일**: 
  - `tests/integration/test_supervisor_with_llm.py` (7개 테스트)
  - `src/supervisor/supervisor.py` (_extract_tool_calls 개선)
  - `tests/test_supervisor.py` (Mock 구조 수정, 20개 유닛 테스트)

## 24. 전체 시스템 E2E 테스트 ✅

- [x] Orchestrator → Supervisor → Worker 전체 플로우 테스트
- [x] 단일 쿼리 시나리오 (원료 검색, 새 세션 생성)
- [x] 멀티턴 대화 시나리오 (이전 대화 참조, 컨텍스트 유지)
- [x] 세션 관리 및 재사용 검증
- [x] 잘못된 세션 ID 처리 (새 세션 생성)
- [x] 컨텍스트 윈도우 제한 검증
- [x] 에러 발생 시 복구 시나리오
- [x] 빈 쿼리 처리
- [x] 실제 사용 케이스: 원료 조사 시나리오 (3턴 대화)
- [x] 여러 사용자의 세션 분리 검증
- **완료**: 12개 E2E 테스트 모두 통과, 전체 207개 테스트 통과
- **테스트 시나리오**:
  1. ✅ 단일 쿼리 → 새 세션 생성 → 응답 반환
  2. ✅ 컨텍스트 저장 및 조회
  3. ✅ 멀티턴 대화 (히알루론산 → 영문명 질문)
  4. ✅ 여러 Worker 호출 (글리세린 → 나이아신아마이드)
  5. ✅ 세션 생성/조회/삭제
  6. ✅ 세션 재사용 (같은 session_id)
  7. ✅ 잘못된 세션 ID → 새 세션 생성
  8. ✅ 컨텍스트 윈도우 제한 (max_turns=3)
  9. ✅ 검색 결과 없는 경우
  10. ✅ 빈 쿼리 처리
  11. ✅ 실제 사용 케이스 (3턴 원료 조사)
  12. ✅ 여러 사용자 세션 분리
- **파일**: 
  - `tests/e2e/test_system_e2e.py` (12개 E2E 테스트)
  - `src/orchestrator/orchestrator.py` (이미 구현됨, 수정 없음)

## 25. Azure AI Search 연동 ✅

- [x] Azure AI Search 인덱스 스키마 설계 (cosmetic-raw-materials)
- [x] setup_cosmetic_index.py 환경변수 기반으로 수정
- [x] search_tools.py 필드명 통일 (korean_name, english_name)
- [x] initialize_search_clients에서 config.py 자동 로드
- [x] USE_MOCK_SEARCH 환경변수로 Mock/Real 전환
- [x] .env.example 환경변수 문서화
- [x] index/README.md 작성 (설정 방법, 실행 방법)
- [x] 기존 테스트 검증 (188개 통과)
- **완료**: Mock → 실제 Azure AI Search 전환 가능
- **파일**: 
  - `src/workers/tools/search_tools.py` (필드명 통일, config 통합)
  - `index/setup_cosmetic_index.py` (환경변수 기반)
  - `index/README.md` (문서화)
  - `.env.example` (USE_MOCK_SEARCH 추가)
  - `src/utils/config.py` (extra='ignore' 추가)

## 26. 문서화 ✅

- [x] 작업 진행된 내용을 기반으로 design/*.md 설계문서 최신화
- [x] README.md 작성
  - 프로젝트 개요 및 주요 기능
  - 아키텍처 다이어그램
  - 설치 및 실행 방법
  - 환경변수 설정 가이드
  - 테스트 실행 방법
  - 각 모듈 별 문서 연결
- **완료**: 실제 구현 기반으로 문서 재작성 (핵심 내용만 간결하게)
- **파일**:
  - `README.md` (프로젝트 루트, 새로 생성)
  - `design/README.md` (설계 개요, 업데이트)
  - `design/01-orchestrator-design.md` (재작성)
  - `design/02-supervisor-agent-design.md` (재작성)
  - `design/03-worker-agent-design.md` (재작성)
- **주요 변경사항**:
  - Router 제거 → Agent-as-Tool 패턴 반영
  - AgentThread 기반 세션 관리 반영
  - 소스코드 예제 최소화 (시그니처만)
  - 테스트 케이스 내용 제외
  - 실제 구현된 API 구조 반영

## 27. 추가 Worker 구현 (선택사항)

- [ ] FormulationWorker (처방 검색) 구현
- [ ] RegulationWorker (규제 검색) 구현
- [ ] Worker 별 통합 테스트
- [ ] Supervisor에 Worker 등록
- **목적**: 원료 외 다른 도메인 지원
- **예상 파일**: `src/workers/formulation.py`, `src/workers/regulation.py`

---
