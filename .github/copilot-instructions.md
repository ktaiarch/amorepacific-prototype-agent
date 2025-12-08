# GitHub Copilot 커스텀 코딩 규칙

이 파일은 GitHub Copilot이 이 프로젝트에서 코드를 생성할 때 따라야 하는 규칙을 정의합니다.

## 🎯 Microsoft Agent Framework 준수

**이 프로젝트는 Microsoft Agent Framework의 공식 SDK와 패턴을 따릅니다.**

- **공식 리포지토리**: https://github.com/microsoft/agent-framework/tree/main/python
- **참조 샘플**: https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started
- **공식 SDK 사용**: `agent-framework` 패키지 및 관련 통합 패키지
- **패턴 준수**: 공식 샘플의 Agent 생성, 도구 사용, 워크플로우 패턴을 따름

### 주요 원칙

1. **공식 SDK 사용**: AutoGen이 아닌 `agent-framework` 패키지 사용
2. **샘플 기반 구현**: 공식 getting_started 샘플의 구조와 패턴 따르기
3. **비동기 우선**: async/await 패턴 사용
4. **표준 API**: ChatAgent, OpenAIChatClient, AzureOpenAIChatClient 등 공식 API 사용

## 일반 원칙

- 코드의 가독성과 유지보수성을 최우선으로 합니다.
- SOLID 원칙을 따릅니다.
- DRY (Don't Repeat Yourself) 원칙을 준수합니다.
- 명확하고 의미 있는 이름을 사용합니다.

## Python 코드 스타일

### 코드 포매팅
- **Black** 포매터 사용 (line length: 88)
- **isort**로 import 정렬
- 최대 줄 길이: 88자

### Microsoft Agent Framework 패턴

```python
# ✅ 좋은 예 - 공식 SDK 사용
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

agent = ChatAgent(
    chat_client=OpenAIChatClient(),
    instructions="You are a helpful assistant.",
    tools=[get_weather],
)
result = await agent.run("What's the weather in Seattle?")

# ❌ 나쁜 예 - AutoGen 직접 사용
from autogen import AssistantAgent
agent = AssistantAgent(name="assistant")
```

### 타입 힌팅
- 모든 함수와 메서드에 타입 힌트 필수
- Python 3.11+ 타입 힌트 문법 사용 (`list[str]`)
- `Optional` 대신 `| None` 사용
- 복잡한 타입은 `TypeAlias` 또는 `TypedDict` 사용
- 도구 함수는 `Annotated`와 `Field` 사용

```python
# ✅ 좋은 예 - Agent Framework 스타일
from typing import Annotated
from pydantic import Field

def get_weather(
    location: Annotated[str, Field(description="The location to get the weather for.")],
) -> str:
    """Get the weather for a given location."""
    return f"The weather in {location} is sunny."

# ❌ 나쁜 예
def process_message(message, metadata=None):
    ...
```

### Docstring
- **Google 스타일** docstring 사용
- 모든 public 클래스, 함수, 메서드에 docstring 작성
- Args, Returns, Raises 섹션 포함
- 예제 코드 포함 (복잡한 기능의 경우)

```python
def calculate_tokens(text: str, model: str = "gpt-4") -> int:
    """텍스트의 토큰 수를 계산합니다.
    
    Args:
        text: 토큰을 계산할 텍스트
        model: 사용할 모델명 (토큰 계산 방식이 모델마다 다름)
        
    Returns:
        계산된 토큰 수
        
    Raises:
        ValueError: 지원하지 않는 모델인 경우
        
    Example:
        >>> calculate_tokens("Hello, world!", "gpt-4")
        4
    """
    ...
```

## 네이밍 컨벤션

### 변수와 함수
- **snake_case** 사용
- 의미를 명확히 전달하는 이름
- 축약어 피하기 (일반적인 경우 제외: `url`, `id`, `api` 등)

```python
# ✅ 좋은 예
user_message = "Hello"
def process_user_input(input_text: str) -> str:
    ...

# ❌ 나쁜 예
msg = "Hello"
def proc_usr_inp(txt):
    ...
```

### 클래스
- **PascalCase** 사용
- 명사 사용
- 의도를 명확히 나타내는 이름

```python
# ✅ 좋은 예
class MessageProcessor:
    ...

class ResponseGenerator:
    ...

# ❌ 나쁜 예
class processor:
    ...

class Gen:
    ...
```

### 상수
- **UPPER_SNAKE_CASE** 사용
- 모듈 레벨에서 정의

```python
# ✅ 좋은 예
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.openai.com"
```

### Private 멤버
- 앞에 언더스코어 `_` 사용
- 진짜 private은 double 언더스코어 `__` (name mangling)

```python
class Agent:
    def __init__(self):
        self._internal_state = {}  # protected
        self.__secret = "key"      # private (name mangling)
    
    def _internal_method(self):    # protected
        ...
```

## 에러 핸들링

### 예외 처리
- 구체적인 예외 타입 사용
- `except Exception` 또는 bare `except` 피하기
- 예외 메시지는 명확하고 실행 가능한 정보 포함
- 예외 체이닝 활용 (`raise ... from ...`)

```python
# ✅ 좋은 예
def load_config(filepath: str) -> dict:
    """설정 파일을 로드합니다."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"설정 파일을 찾을 수 없습니다: {filepath}") from e
    except json.JSONDecodeError as e:
        raise ConfigError(f"설정 파일 형식이 올바르지 않습니다: {filepath}") from e

# ❌ 나쁜 예
def load_config(filepath):
    try:
        with open(filepath) as f:
            return json.load(f)
    except Exception:
        return {}
```

### 커스텀 예외
- 의미 있는 예외 클래스 정의
- 프로젝트 루트 예외 클래스 상속

```python
class AgentError(Exception):
    """Agent 관련 모든 예외의 베이스 클래스."""
    pass

class ConfigError(AgentError):
    """설정 관련 예외."""
    pass

class PluginError(AgentError):
    """플러그인 관련 예외."""
    pass
```

## 로깅

### 로그 레벨
- `DEBUG`: 디버깅 정보
- `INFO`: 일반 정보 (주요 이벤트)
- `WARNING`: 경고 (잠재적 문제)
- `ERROR`: 에러 (기능 실패)
- `CRITICAL`: 치명적 에러 (시스템 중단)

### 로깅 패턴
- 구조화된 로그 사용 (JSON)
- 컨텍스트 정보 포함 (user_id, session_id 등)
- 민감 정보 마스킹 (API 키, 비밀번호 등)

```python
# ✅ 좋은 예
logger.info(
    "메시지 처리 완료",
    extra={
        "session_id": session_id,
        "user_id": user_id,
        "message_length": len(message),
        "duration_ms": duration * 1000,
    }
)

# ❌ 나쁜 예
logger.info(f"Message processed: {message}")  # 민감 정보 노출
```

## 코드 구조

### 함수와 메서드
- 한 가지 일만 수행 (Single Responsibility)
- 함수 길이: 최대 50줄 권장
- 파라미터 개수: 최대 5개 권장 (초과 시 객체로 묶기)
- Early return 패턴 사용

```python
# ✅ 좋은 예
def validate_message(message: str) -> bool:
    """메시지를 검증합니다."""
    if not message:
        logger.warning("빈 메시지입니다")
        return False
    
    if len(message) > MAX_LENGTH:
        logger.warning(f"메시지가 너무 깁니다: {len(message)} > {MAX_LENGTH}")
        return False
    
    return True

# ❌ 나쁜 예
def validate_message(message):
    result = True
    if message:
        if len(message) <= MAX_LENGTH:
            result = True
        else:
            result = False
    else:
        result = False
    return result
```

### 클래스 설계
- 작고 집중된 클래스
- 의존성 주입 사용
- 인터페이스와 구현 분리 (추상 클래스 활용)

```python
# ✅ 좋은 예
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    """저장소 인터페이스."""
    
    @abstractmethod
    def save(self, key: str, value: dict) -> None:
        """데이터를 저장합니다."""
        pass
    
    @abstractmethod
    def load(self, key: str) -> dict:
        """데이터를 로드합니다."""
        pass

class JSONStorage(StorageBackend):
    """JSON 파일 기반 저장소."""
    
    def save(self, key: str, value: dict) -> None:
        ...
    
    def load(self, key: str) -> dict:
        ...

class StateManager:
    """상태 관리자."""
    
    def __init__(self, storage: StorageBackend):
        """의존성 주입으로 저장소 받기."""
        self.storage = storage
```

## 테스트

### 테스트 작성
- 모든 public 함수와 메서드에 테스트 작성
- AAA 패턴 (Arrange, Act, Assert)
- 의미 있는 테스트 이름 (`test_<기능>_<조건>_<예상결과>`)

```python
def test_message_processor_validates_empty_message_returns_false():
    """빈 메시지 검증 시 False를 반환해야 합니다."""
    # Arrange
    processor = MessageProcessor()
    message = ""
    
    # Act
    result = processor.validate(message)
    
    # Assert
    assert result is False
```

### Mock 사용
- 외부 의존성은 mock
- `pytest-mock` 또는 `unittest.mock` 사용

```python
def test_response_generator_handles_api_error(mocker):
    """API 에러 발생 시 적절히 처리해야 합니다."""
    # Arrange
    mock_api = mocker.patch("openai.ChatCompletion.create")
    mock_api.side_effect = APIError("API 에러")
    generator = ResponseGenerator(config)
    
    # Act & Assert
    with pytest.raises(ResponseGenerationError):
        generator.generate(messages)
```

## 보안

### API 키와 비밀 정보
- 환경 변수로 관리
- 코드에 하드코딩 금지
- 로그에 출력 금지

```python
# ✅ 좋은 예
import os
from pydantic import SecretStr

api_key = SecretStr(os.getenv("OPENAI_API_KEY"))

# ❌ 나쁜 예
api_key = "sk-1234567890abcdef"  # 절대 금지!
```

### 입력 검증
- 모든 외부 입력 검증
- Pydantic 모델 활용
- SQL Injection, Command Injection 방지

```python
from pydantic import BaseModel, field_validator

class UserInput(BaseModel):
    message: str
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or len(v) > 4000:
            raise ValueError("메시지 길이는 1-4000자여야 합니다")
        return v.strip()
```

## 성능

### 최적화 원칙
- 먼저 작동하게, 그 다음 최적화
- 프로파일링 후 병목 지점 개선
- 캐싱 활용 (functools.lru_cache)

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_tokens(text: str, model: str) -> int:
    """토큰 수 계산 (결과 캐싱)."""
    ...
```

### 비동기 처리
- I/O 바운드 작업은 비동기로
- `async`/`await` 사용
- `httpx`나 `aiohttp` 사용

```python
import httpx

async def fetch_data(url: str) -> dict:
    """비동기로 데이터를 가져옵니다."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
```

## 의존성 관리

### 패키지 선택
- 잘 유지보수되는 패키지 사용
- 최신 stable 버전 사용
- 의존성 최소화

### 버전 관리
- pyproject.toml에 명시
- 호환 버전 범위 지정
- uv.lock으로 정확한 버전 고정

```toml
[project]
dependencies = [
    "pydantic>=2.0.0,<3.0.0",
    "httpx>=0.25.0",
    "python-dotenv>=1.0.0",
]
```

## Git 커밋 메시지

### 커밋 메시지 형식
- Conventional Commits 스타일
- 한글 또는 영어 (일관성 유지)

```
<타입>: <제목>

<본문>

<푸터>
```

### 타입
- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포매팅
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

### 예시
```
feat: 웹 검색 플러그인 추가

DuckDuckGo를 사용한 웹 검색 플러그인 구현
- BasePlugin 상속
- Function calling 스키마 포함
- 결과 캐싱 지원

Closes #42
```

## 주석

### 주석 작성 원칙
- 코드가 **무엇을** 하는지는 코드로 설명
- **왜** 그렇게 했는지는 주석으로 설명
- TODO, FIXME, HACK 등 태그 사용

```python
# ✅ 좋은 예
# NOTE: OpenAI API는 최대 4096 토큰까지만 지원하므로
# 초과하는 경우 컨텍스트를 요약해야 함
if token_count > 4096:
    context = summarize_context(context)

# TODO: 추후 streaming 응답 지원 추가 (#123)
# FIXME: 동시 요청 시 race condition 발생 가능 (#456)

# ❌ 나쁜 예
# 토큰 수 체크
if token_count > 4096:
    context = summarize_context(context)  # 컨텍스트 요약
```

---

## 이 규칙을 적용하는 방법

### Copilot Chat에서 참조
프롬프트에 다음과 같이 작성하면 이 규칙을 따릅니다:

```
프로젝트의 코딩 규칙을 따라서 MessageProcessor 클래스를 만들어줘.
```

### 코드 리뷰 요청
```
이 코드가 프로젝트의 코딩 규칙을 따르는지 리뷰해줘.
[코드]
```

### 리팩토링 요청
```
이 코드를 프로젝트의 코딩 규칙에 맞게 리팩토링해줘.
특히 타입 힌트와 docstring을 추가해야 해.
[코드]
```