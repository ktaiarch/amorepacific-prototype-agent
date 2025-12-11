# 프로토타입 → 완성품 전환 작업 목록

현재 프로토타입의 완성도를 높여 프로덕션 레벨로 전환하기 위한 작업 목록입니다.

---

## Phase 1: 핵심 기능 확장 (2-3주)

### 1.1 추가 Worker 구현

#### 1.1.1 FormulaWorker (처방 검색) 구현

- [ ] FormulaWorker 클래스 작성 (`src/workers/formula.py`)
  - BaseWorker 상속
  - 처방 검색 전문 시스템 프롬프트 작성
  - process() 메서드 구현
- [ ] 처방 데이터 Mock 준비 (`data/cosmetic_formulas.json`)
  - 샘플 처방 데이터 10-20개 작성
  - 필드: formula_id, name, ingredients, percentages, purpose, etc.
- [ ] Azure AI Search 처방 인덱스 스키마 설계
  - 인덱스명: cosmetic-formulas
  - 필드 정의: 처방명, 성분 리스트, 용도, 타입 등
- [ ] 처방 인덱스 설정 스크립트 작성 (`index/setup_formula_index.py`)
- [ ] FormulaWorker 유닛 테스트 (`tests/test_formula_worker.py`)
  - 초기화 테스트
  - 검색 기능 테스트
  - 응답 포맷 테스트
- [ ] FormulaWorker 통합 테스트 (`tests/integration/test_formula_worker_with_llm.py`)
  - 실제 LLM 연동 테스트
  - 처방 검색 시나리오 테스트

#### 1.1.2 RegulationWorker (규제 검색) 구현

- [ ] RegulationWorker 클래스 작성 (`src/workers/regulation.py`)
  - BaseWorker 상속
  - 규제 검색 전문 시스템 프롬프트 작성
  - process() 메서드 구현
- [ ] 규제 데이터 Mock 준비 (`data/cosmetic_regulations.json`)
  - 샘플 규제 데이터 10-20개 작성
  - 필드: regulation_id, country, category, content, effective_date, etc.
- [ ] Azure AI Search 규제 인덱스 스키마 설계
  - 인덱스명: cosmetic-regulations
  - 필드 정의: 국가, 카테고리, 규제 내용, 시행일 등
- [ ] 규제 인덱스 설정 스크립트 작성 (`index/setup_regulation_index.py`)
- [ ] RegulationWorker 유닛 테스트 (`tests/test_regulation_worker.py`)
- [ ] RegulationWorker 통합 테스트 (`tests/integration/test_regulation_worker_with_llm.py`)

#### 1.1.3 Worker 통합 및 등록

- [ ] Orchestrator에 FormulaWorker, RegulationWorker 등록
  - `Orchestrator.create_default()` 메서드 수정
  - workers 딕셔너리에 "처방", "규제" 추가
- [ ] Supervisor 시스템 프롬프트 업데이트 (`src/supervisor/prompts.py`)
  - 처방 검색 Tool 설명 추가
  - 규제 검색 Tool 설명 추가
- [ ] E2E 테스트 확장 (`tests/e2e/test_system_e2e.py`)
  - 처방 검색 시나리오 추가
  - 규제 검색 시나리오 추가
  - 멀티 도메인 검색 시나리오 (원료 + 처방)
- [ ] UI 샘플 질의 업데이트 (`src/ui/app.py`)
  - 처방 검색 샘플 추가
  - 규제 검색 샘플 추가
- [ ] 문서 업데이트
  - README.md: Worker 목록 업데이트
  - design/03-worker-agent-design.md: 처방/규제 Worker 설명 추가

---

## Phase 2: 프로덕션 준비 (2-3주)

### 2.1 에러 처리 및 복원력 강화

#### 2.1.1 재시도 로직 구현

- [ ] Azure OpenAI API 재시도 로직 추가
  - `src/utils/retry.py` 생성
  - exponential backoff 구현
  - 최대 재시도 횟수 설정 (기본값: 3)
- [ ] Azure AI Search 재시도 로직 추가
  - 검색 실패 시 재시도
  - 타임아웃 처리 개선
- [ ] Worker 타임아웃 설정 세분화
  - 환경변수로 Worker별 타임아웃 설정
  - `WORKER_TIMEOUT_SECONDS` 추가

#### 2.1.2 에러 메시지 및 로깅 개선

- [ ] 사용자 친화적 에러 메시지 작성
  - `src/utils/error_messages.py` 생성
  - 에러 코드별 메시지 정의
- [ ] 구조화된 로깅 강화
  - 요청 ID 추가 (request_id)
  - 성능 메트릭 로깅 (응답 시간, 토큰 사용량)
- [ ] 에러 추적 시스템 연동 준비
  - Sentry/Application Insights 연동 준비
  - `src/utils/monitoring.py` 생성

#### 2.1.3 입력 검증 강화

- [ ] 쿼리 입력 검증 추가
  - 최대 길이 제한 (환경변수: MAX_QUERY_LENGTH)
  - 특수문자 필터링 (선택적)
- [ ] 세션 ID 검증 강화
  - UUID 형식 검증
  - 잘못된 세션 ID 처리 개선
- [ ] Pydantic 모델 검증 확장
  - 모든 API 입출력에 Pydantic 모델 적용
  - `src/orchestrator/models.py` 확장

---

### 2.2 Agent 품질 평가 (Azure AI Evaluation)

#### 2.2.1 평가 환경 설정

- [ ] Azure AI Evaluation SDK 설치
  - pyproject.toml에 `azure-ai-evaluation` 추가
  - Azure AI Foundry 프로젝트 생성
- [ ] 평가 데이터셋 준비
  - `data/evaluation/test_cases.jsonl` 생성
  - 원료/처방/규제 검색 시나리오 각 20개 이상
  - Ground truth 답변 준비
- [ ] Azure AI Foundry 연동 설정
  - 환경변수 추가: `AZURE_AI_PROJECT_NAME`, `AZURE_AI_FOUNDRY_ENDPOINT`
  - 인증 설정 (Azure Identity)

#### 2.2.2 평가 메트릭 구현

- [ ] 답변 품질 평가 구현 (`src/evaluation/quality_metrics.py`)
  - **Groundedness**: 검색 결과 기반 답변 여부
  - **Relevance**: 질문과 답변의 관련성
  - **Coherence**: 답변의 논리적 일관성
  - **Fluency**: 답변의 자연스러움
- [ ] 검색 품질 평가 구현 (`src/evaluation/retrieval_metrics.py`)
  - **Precision**: 검색 결과의 정확도
  - **Recall**: 관련 문서 검색률
  - **MRR (Mean Reciprocal Rank)**: 첫 관련 문서 순위
- [ ] 안전성 평가 구현 (`src/evaluation/safety_metrics.py`)
  - **Harmful content detection**: 유해 콘텐츠 감지
  - **Jailbreak detection**: Prompt injection 감지
- [ ] 커스텀 메트릭 구현
  - **Tool usage accuracy**: 적절한 Worker 선택률
  - **Response time**: 평균 응답 시간
  - **Token efficiency**: 토큰 사용 효율성

#### 2.2.3 평가 스크립트 작성

- [ ] 배치 평가 스크립트 (`scripts/evaluate_agents.py`)
  - 전체 테스트 케이스에 대한 평가 실행
  - Azure AI Foundry에 결과 업로드
  - 요약 리포트 생성
- [ ] 단일 쿼리 평가 도구 (`scripts/evaluate_query.py`)
  - 개별 쿼리 평가 및 디버깅
  - 메트릭별 상세 점수 출력
- [ ] 비교 평가 스크립트 (`scripts/compare_evaluations.py`)
  - 프롬프트/모델 변경 전후 비교
  - 통계적 유의성 검정

#### 2.2.4 평가 데이터셋 구축

- [ ] 원료 검색 평가 데이터 (`data/evaluation/ingredient_test_cases.jsonl`)
  - 기본 정보 검색 (한글명, 영문명, CAS 번호)
  - 스펙 조회 (점도, pH, 함량)
  - 발주 상태 확인
  - 컨텍스트 기반 질문 (멀티턴)
  - 엣지 케이스 (오타, 약어, 부분 일치)
- [ ] 처방 검색 평가 데이터 (`data/evaluation/formula_test_cases.jsonl`)
  - 처방 정보 검색
  - 성분 비교
  - 용도별 검색
- [ ] 규제 검색 평가 데이터 (`data/evaluation/regulation_test_cases.jsonl`)
  - 국가별 규제 조회
  - 성분 사용 제한 확인
  - 최신 규제 동향
- [ ] 일반 대화 평가 데이터 (`data/evaluation/general_test_cases.jsonl`)
  - 시스템 기능 설명
  - 사용 방법 안내
  - 범위 밖 질문 처리

#### 2.2.5 CI/CD 통합

- [ ] GitHub Actions 워크플로우 추가 (`.github/workflows/evaluate.yml`)
  - PR 생성 시 자동 평가 실행
  - 메인 브랜치 머지 전 품질 기준 통과 확인
  - 평가 결과를 PR 코멘트로 추가
- [ ] 품질 게이트 설정
  - 최소 품질 기준 정의 (예: Groundedness > 0.8)
  - 기준 미달 시 배포 차단
- [ ] 정기 평가 스케줄
  - 매일 자정 전체 평가 실행
  - 주간 리포트 생성

#### 2.2.6 평가 결과 분석 및 개선

- [ ] Azure AI Foundry 대시보드 구축
  - 메트릭별 트렌드 시각화
  - 실패 케이스 분석
  - 모델/프롬프트 버전별 비교
- [ ] 평가 리포트 자동 생성 (`scripts/generate_evaluation_report.py`)
  - Markdown 리포트 생성
  - 메트릭 요약 테이블
  - 개선 권장사항
- [ ] 실패 케이스 분석 도구
  - 낮은 점수를 받은 케이스 추출
  - 원인 분석 및 개선 방향 제시

---

### 2.3 성능 최적화

#### 2.3.1 캐싱 구현

- [ ] LRU 캐시 적용
  - 검색 결과 캐싱 (TTL: 1시간)
  - `src/utils/cache.py` 생성
- [ ] 세션 캐시 최적화
  - 자주 사용되는 세션 메모리 캐시
  - 만료된 세션 자동 정리 스케줄러

#### 2.3.2 토큰 최적화

- [ ] 프롬프트 최적화
  - 시스템 프롬프트 간결화
  - 불필요한 컨텍스트 제거
- [ ] 토큰 사용량 모니터링
  - 요청별 토큰 사용량 로깅
  - 토큰 사용량 통계 추가

#### 2.3.3 비동기 처리 개선

- [ ] 병렬 검색 지원
  - 여러 Worker 동시 호출 옵션
  - `asyncio.gather()` 활용
- [ ] 스트리밍 응답 지원 검토
  - Streamlit UI에서 실시간 응답 표시
  - Agent Framework 스트리밍 API 활용

---

### 2.4 보안 강화

#### 2.4.1 인증 및 권한 관리

- [ ] 사용자 인증 시스템 추가
  - Azure AD 연동 준비
  - `src/utils/auth.py` 생성
- [ ] API 키 관리 개선
  - Azure Key Vault 연동 준비
  - 환경변수 암호화

#### 2.4.2 입력 보안

- [ ] SQL Injection 방지
  - Azure AI Search 필터 쿼리 검증
- [ ] Prompt Injection 방지
  - 사용자 입력 이스케이프
  - 시스템 프롬프트 보호
- [ ] Rate Limiting 구현
  - 사용자별 요청 제한
  - `src/utils/rate_limiter.py` 생성

#### 2.4.3 데이터 보호

- [ ] 민감 정보 마스킹
  - 로그에서 API 키, 개인정보 마스킹
  - `src/utils/logger.py` 개선
- [ ] HTTPS 강제 (배포 시)
- [ ] CORS 설정 (필요 시)

---

### 2.5 테스트 및 품질 보증

#### 2.5.1 테스트 커버리지 확대

- [ ] 현재 테스트 커버리지 측정
  - `pytest --cov=src --cov-report=term-missing`
  - 목표: 80% 이상
- [ ] 누락된 테스트 추가
  - 엣지 케이스 테스트
  - 에러 시나리오 테스트
- [ ] 부하 테스트 추가
  - `tests/load/test_performance.py` 생성
  - locust 또는 pytest-benchmark 사용

#### 2.5.2 CI/CD 파이프라인 구축

- [ ] GitHub Actions 워크플로우 작성 (`.github/workflows/`)
  - `ci.yml`: 테스트 자동 실행
  - `lint.yml`: Black, isort, mypy 실행
  - `security.yml`: 보안 스캔 (bandit, safety)
- [ ] Pre-commit 훅 설정
  - `.pre-commit-config.yaml` 생성
  - 커밋 전 포매팅, 린트 자동 실행
- [ ] 코드 품질 도구 통합
  - mypy: 타입 체크
  - pylint: 코드 품질 검사
  - pytest-cov: 커버리지 측정

#### 2.5.3 문서 자동화

- [ ] Docstring 커버리지 확인
  - interrogate 도구 사용
  - 모든 public 함수/클래스에 docstring 추가
- [ ] API 문서 자동 생성
  - Sphinx 설정
  - `docs/` 디렉토리 생성
- [ ] CHANGELOG.md 작성
  - 버전별 변경사항 기록

---

## Phase 3: 배포 및 운영 (1-2주)

### 3.1 컨테이너화

#### 3.1.1 Docker 설정

- [ ] Dockerfile 작성
  - 멀티 스테이지 빌드
  - 최적화된 이미지 크기
- [ ] docker-compose.yml 작성
  - 개발 환경 설정
  - 프로덕션 환경 설정 분리
- [ ] .dockerignore 작성
  - 불필요한 파일 제외

#### 3.1.2 Azure 배포 준비

- [ ] Azure Container Apps 배포 스크립트
  - `deploy/azure/deploy.sh` 작성
- [ ] 환경변수 관리
  - Azure Key Vault 연동
  - 환경별 설정 분리 (dev, staging, prod)
- [ ] Health check 엔드포인트 추가
  - `/health` 엔드포인트 구현
  - Liveness/Readiness probe 설정

---

### 3.2 모니터링 및 관찰성

#### 3.2.1 로깅 시스템 구축

- [ ] Azure Application Insights 연동
  - `src/utils/telemetry.py` 생성
  - 커스텀 메트릭 추가
- [ ] 로그 레벨별 필터링
  - 환경변수: LOG_LEVEL
  - 프로덕션: INFO, 개발: DEBUG
- [ ] 로그 집계 시스템 연동
  - Azure Log Analytics 연동

#### 3.2.2 성능 모니터링

- [ ] 메트릭 수집
  - 응답 시간
  - 토큰 사용량
  - 에러율
  - 사용자 수
- [ ] 대시보드 구축
  - Azure Monitor 대시보드
  - 주요 KPI 시각화
- [ ] 알림 설정
  - 에러율 임계값 알림
  - 응답 시간 지연 알림

#### 3.2.3 사용자 분석

- [ ] 사용 패턴 분석
  - 검색 키워드 통계
  - Worker 사용 빈도
  - 세션 길이 분석
- [ ] 피드백 수집 시스템
  - UI에 피드백 버튼 추가
  - 피드백 데이터 저장

---

### 3.3 운영 도구

#### 3.3.1 관리자 도구

- [ ] 세션 관리 CLI
  - `scripts/manage_sessions.py` 작성
  - 세션 조회/삭제 명령
- [ ] 데이터 마이그레이션 스크립트
  - `scripts/migrate_data.py` 작성
  - 인덱스 스키마 변경 시 사용
- [ ] 백업 스크립트
  - Azure AI Search 데이터 백업
  - 세션 데이터 백업 (향후 DB 도입 시)

#### 3.3.2 문제 해결 도구

- [ ] 디버깅 모드 강화
  - 상세 로그 출력 옵션
  - 요청/응답 덤프 기능
- [ ] 트러블슈팅 가이드 작성
  - `docs/troubleshooting.md`
  - 자주 발생하는 문제 및 해결 방법

---

## Phase 4: 고급 기능 (선택사항, 2-3주)

### 4.1 UI/UX 개선

#### 4.1.1 Streamlit UI 고도화

- [ ] 파일 업로드 기능
  - 엑셀 파일로 원료 리스트 업로드
  - 일괄 검색 기능
- [ ] 검색 히스토리
  - 이전 검색 기록 표시
  - 즐겨찾기 기능
- [ ] 결과 내보내기
  - CSV/Excel 다운로드
  - PDF 리포트 생성
- [ ] 다국어 지원
  - i18n 설정
  - 한국어/영어 전환

#### 4.1.2 시각화 기능

- [ ] 검색 결과 차트
  - 원료 비교 차트
  - 트렌드 분석 차트
- [ ] 인터랙티브 그래프
  - Plotly 연동
  - 성분 관계도

---

### 4.2 고급 검색 기능

#### 4.2.1 하이브리드 검색

- [ ] 벡터 + 키워드 하이브리드 검색
  - Azure AI Search 하이브리드 검색 활용
  - 검색 품질 개선
- [ ] 시맨틱 검색
  - Azure AI Search 시맨틱 랭커 활용
- [ ] 필터링 고도화
  - 복합 필터 조건
  - 날짜 범위 필터

#### 4.2.2 멀티홉 검색

- [ ] 연쇄 검색 지원
  - 여러 Worker 순차 호출
  - 중간 결과를 다음 검색에 활용
- [ ] 교차 참조 검색
  - 원료 → 처방 → 규제 연결
  - 관계형 검색

---

### 4.3 데이터 관리

#### 4.3.1 데이터베이스 도입

- [ ] 세션 데이터 영속화
  - Azure Cosmos DB 또는 PostgreSQL 연동
  - SessionManager 개선
- [ ] 검색 히스토리 저장
  - 사용자별 히스토리 관리
  - 통계 분석용 데이터 수집
- [ ] 마이그레이션 스크립트
  - In-memory → DB 전환 스크립트

#### 4.3.2 데이터 파이프라인

- [ ] 원료 데이터 자동 업데이트
  - 정기적 데이터 동기화
  - Azure Data Factory 연동
- [ ] 데이터 검증
  - 데이터 품질 체크
  - 중복 제거

---

## Phase 5: 문서화 및 배포 (1주)

### 5.1 최종 문서화

#### 5.1.1 사용자 가이드

- [ ] 사용자 매뉴얼 작성 (`docs/user-guide.md`)
  - 화면별 설명
  - 주요 기능 사용법
  - FAQ
- [ ] 비디오 튜토리얼 제작 (선택)
  - 스크린 레코딩
  - 나레이션 추가

#### 5.1.2 개발자 가이드

- [ ] 아키텍처 문서 보완 (`docs/architecture.md`)
  - 상세 다이어그램
  - 데이터 플로우
  - 의사결정 기록 (ADR)
- [ ] API 레퍼런스 문서 (`docs/api-reference.md`)
  - 모든 public API 문서화
  - 예제 코드 추가
- [ ] 기여 가이드 (`CONTRIBUTING.md`)
  - 코드 기여 방법
  - 코딩 규칙
  - PR 프로세스

#### 5.1.3 운영 문서

- [ ] 배포 가이드 (`docs/deployment.md`)
  - 환경 설정
  - 배포 프로세스
  - 롤백 절차
- [ ] 운영 매뉴얼 (`docs/operations.md`)
  - 모니터링 방법
  - 알림 대응
  - 장애 대응

---

### 5.2 프로덕션 배포

#### 5.2.1 배포 전 체크리스트

- [ ] 모든 테스트 통과 확인
- [ ] 보안 스캔 완료
- [ ] 성능 테스트 완료
- [ ] 문서 최신화 확인
- [ ] 롤백 계획 수립

#### 5.2.2 스테이징 배포

- [ ] 스테이징 환경 구축
- [ ] 스테이징 테스트
- [ ] 사용자 수용 테스트 (UAT)

#### 5.2.3 프로덕션 배포

- [ ] 프로덕션 배포 실행
- [ ] Smoke test 수행
- [ ] 모니터링 확인
- [ ] 사용자 공지

---

## Phase 6: 운영 및 개선 (지속)

### 6.1 모니터링 및 유지보수

- [ ] 일일 모니터링
- [ ] 주간 성능 리포트
- [ ] 월간 사용 통계 분석
- [ ] 정기 보안 패치

### 6.2 사용자 피드백 반영

- [ ] 피드백 수집 및 분류
- [ ] 개선 우선순위 결정
- [ ] 기능 개선 로드맵 수립

### 6.3 기술 부채 관리

- [ ] 코드 리팩토링
- [ ] 의존성 업데이트
- [ ] 성능 최적화 지속

---

## 우선순위 요약

### 🔴 High Priority (필수)

- Phase 1: 핵심 기능 확장 (Worker 추가)
- Phase 2.1: 에러 처리 및 복원력
- Phase 2.4: 테스트 및 CI/CD
- Phase 3.1: 컨테이너화
- Phase 3.2: 모니터링

### 🟡 Medium Priority (권장)

- Phase 2.2: 성능 최적화
- Phase 2.3: 보안 강화
- Phase 3.3: 운영 도구
- Phase 5: 문서화 및 배포

### 🟢 Low Priority (선택)

- Phase 4: 고급 기능
- Phase 6: 지속적 개선

---

## 예상 일정

- **Phase 1**: 2-3주 (핵심 Worker 추가)
- **Phase 2**: 2-3주 (프로덕션 준비)
- **Phase 3**: 1-2주 (배포 및 운영)
- **Phase 4**: 2-3주 (고급 기능, 선택)
- **Phase 5**: 1주 (최종 문서화 및 배포)

**총 예상 기간**: 8-12주 (2-3개월)

---

## 참고 문서

- [프로젝트 계획](plan.md)
- [프로젝트 README](README.md)
- [설계 문서](design/README.md)
- [코딩 규칙](.github/copilot-instructions.md)
