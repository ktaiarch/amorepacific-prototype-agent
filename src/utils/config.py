"""애플리케이션 설정 관리.

환경 변수를 로드하고 Azure 클라이언트를 초기화합니다.
"""

from typing import Any

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigError
from .logger import get_logger

logger = get_logger(__name__)

# .env 파일 로드
load_dotenv()


class AzureOpenAISettings(BaseSettings):
    """Azure OpenAI 설정."""

    model_config = SettingsConfigDict(env_prefix="AZURE_OPENAI_")

    endpoint: str = Field(default="", description="Azure OpenAI 엔드포인트")
    api_key: str | None = Field(default=None, description="Azure OpenAI API 키")
    deployment_name: str = Field(
        default="gpt-4o", description="배포된 모델 이름"
    )
    api_version: str = Field(
        default="2024-10-21", description="API 버전"
    )


class AzureSearchSettings(BaseSettings):
    """Azure AI Search 설정."""

    model_config = SettingsConfigDict(env_prefix="AZURE_SEARCH_")

    endpoint: str = Field(default="", description="Azure AI Search 엔드포인트")
    api_key: str | None = Field(default=None, description="Azure AI Search API 키")
    index_name: str = Field(
        default="cosmetic-raw-materials", description="검색 인덱스 이름"
    )


class SessionSettings(BaseSettings):
    """세션 관리 설정."""

    model_config = SettingsConfigDict(env_prefix="SESSION_")

    ttl_minutes: int = Field(default=30, description="세션 유효 시간 (분)")
    max_context_turns: int = Field(
        default=5, description="유지할 최대 대화 턴 수"
    )


class StreamlitSettings(BaseSettings):
    """Streamlit 설정."""

    model_config = SettingsConfigDict(env_prefix="STREAMLIT_")

    server_port: int = Field(default=8501, description="서버 포트")
    server_address: str = Field(default="localhost", description="서버 주소")


class AppConfig(BaseSettings):
    """애플리케이션 전체 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 알 수 없는 환경변수 무시
    )

    # 하위 설정
    azure_openai: AzureOpenAISettings = Field(
        default_factory=lambda: AzureOpenAISettings()
    )
    azure_search: AzureSearchSettings = Field(
        default_factory=lambda: AzureSearchSettings()
    )
    session: SessionSettings = Field(default_factory=lambda: SessionSettings())
    streamlit: StreamlitSettings = Field(default_factory=lambda: StreamlitSettings())

    # 기타 설정
    debug: bool = Field(default=False, description="디버그 모드")
    log_level: str = Field(default="INFO", description="로그 레벨")


# 전역 설정 인스턴스
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """애플리케이션 설정을 반환합니다.

    싱글톤 패턴으로 설정 인스턴스를 관리합니다.

    Returns:
        AppConfig 인스턴스

    Raises:
        ConfigError: 필수 환경 변수가 누락된 경우

    Example:
        >>> config = get_config()
        >>> print(config.azure_openai.endpoint)
    """
    global _config

    if _config is None:
        try:
            _config = AppConfig()
            logger.info("애플리케이션 설정 로드 완료")
        except Exception as e:
            raise ConfigError(f"설정 로드 실패: {e}") from e

    return _config


def get_azure_credential() -> DefaultAzureCredential:
    """Azure 인증 자격 증명을 반환합니다.

    환경에 따라 적절한 인증 방식을 자동으로 선택합니다:
    - 로컬: Azure CLI 인증
    - Azure: Managed Identity

    Returns:
        DefaultAzureCredential 인스턴스
    """
    return DefaultAzureCredential()


def get_azure_openai_client() -> Any:
    """Azure OpenAI 클라이언트를 반환합니다.

    Returns:
        AzureOpenAI 클라이언트 인스턴스

    Raises:
        ConfigError: 클라이언트 초기화 실패
    """
    from azure.ai.inference import ChatCompletionsClient
    from azure.core.credentials import AzureKeyCredential

    config = get_config()
    settings = config.azure_openai

    try:
        if settings.api_key:
            # API 키 방식
            client = ChatCompletionsClient(
                endpoint=settings.endpoint,
                credential=AzureKeyCredential(settings.api_key),
            )
            logger.info("Azure OpenAI 클라이언트 초기화 완료 (API 키)")
        else:
            # DefaultAzureCredential 방식
            client = ChatCompletionsClient(
                endpoint=settings.endpoint,
                credential=get_azure_credential(),
            )
            logger.info(
                "Azure OpenAI 클라이언트 초기화 완료 (DefaultAzureCredential)"
            )

        return client

    except Exception as e:
        raise ConfigError(f"Azure OpenAI 클라이언트 초기화 실패: {e}") from e


def get_azure_search_client(index_name: str | None = None) -> Any:
    """Azure AI Search 클라이언트를 반환합니다.

    Args:
        index_name: 검색 인덱스 이름 (기본값: 설정 파일의 값 사용)

    Returns:
        SearchClient 인스턴스

    Raises:
        ConfigError: 클라이언트 초기화 실패
    """
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    config = get_config()
    settings = config.azure_search

    index = index_name or settings.index_name

    try:
        if settings.api_key:
            # API 키 방식
            client = SearchClient(
                endpoint=settings.endpoint,
                index_name=index,
                credential=AzureKeyCredential(settings.api_key),
            )
            logger.info(
                f"Azure AI Search 클라이언트 초기화 완료 (API 키, index={index})"
            )
        else:
            # DefaultAzureCredential 방식
            client = SearchClient(
                endpoint=settings.endpoint,
                index_name=index,
                credential=get_azure_credential(),
            )
            logger.info(
                f"Azure AI Search 클라이언트 초기화 완료 (DefaultAzureCredential, index={index})"
            )

        return client

    except Exception as e:
        raise ConfigError(f"Azure AI Search 클라이언트 초기화 실패: {e}") from e
