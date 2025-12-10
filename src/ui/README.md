# Streamlit UI 실행 가이드

## 🚀 빠른 시작

### 1. 환경변수 설정

`.env` 파일을 생성하고 Azure OpenAI 설정을 추가하세요:

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 실제 값으로 변경:
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 엔드포인트
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API 키
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`: 배포 모델명 (예: gpt-4o)

### 2. Streamlit 앱 실행

```bash
# 프로젝트 루트에서 실행
uv run streamlit run src/ui/app.py
```

### 3. 브라우저에서 접속

자동으로 브라우저가 열리며, `http://localhost:8501`로 접속됩니다.

---

## 📋 주요 기능

### 💬 채팅 인터페이스
- 사용자 입력 및 AI 응답
- 대화 히스토리 자동 저장
- 세션 기반 컨텍스트 관리

### 📌 샘플 질의
사이드바에서 샘플 질의를 클릭하면 자동으로 입력됩니다:
- "비타민C의 CAS 번호는?"
- "비타민C의 원료 스펙을 알려줘"
- "비타민C의 발주 상태는?"

### 🐛 디버깅 정보
디버깅 모드를 켜면 다음 정보를 확인할 수 있습니다:
- 사용된 Worker (원료/처방/규제)
- 응답 시간
- 타임스탬프

### 🆕 새 대화
사이드바의 "새 대화" 버튼으로 세션을 초기화할 수 있습니다.

---

## 🔧 커스터마이징

### 설정 변경

`.env` 파일에서 다음 설정을 변경할 수 있습니다:

```bash
# 세션 유효 시간 (분)
SESSION_TTL_MINUTES=30

# 최대 대화 턴 수
MAX_TURNS=5

# 최대 토큰 수
MAX_TOKENS=4000
```

### UI 스타일링

`src/ui/app.py`에서 Streamlit 테마 설정을 변경할 수 있습니다:

```python
st.set_page_config(
    page_title="화장품 R&D Assistant",
    page_icon="🧪",
    layout="wide",  # "centered" 또는 "wide"
    initial_sidebar_state="expanded",  # "expanded" 또는 "collapsed"
)
```

---

## 🐞 트러블슈팅

### 환경변수 오류
```
❌ 환경변수가 설정되지 않았습니다: AZURE_OPENAI_ENDPOINT, ...
```

**해결방법:** `.env` 파일을 확인하고 필수 환경변수를 설정하세요.

### Import 오류
```
ModuleNotFoundError: No module named 'src'
```

**해결방법:** 프로젝트 루트 디렉토리에서 실행하세요:
```bash
cd /Users/namhokim/Work/amorepacific/prototype
uv run streamlit run src/ui/app.py
```

### Orchestrator 초기화 실패
```
❌ Orchestrator 초기화 실패: ...
```

**해결방법:** Azure OpenAI 설정이 올바른지 확인하세요.

---

## 📚 참고

- **Streamlit 문서:** https://docs.streamlit.io/
- **Azure OpenAI:** https://azure.microsoft.com/products/ai-services/openai-service
