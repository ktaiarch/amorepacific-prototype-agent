"""커스텀 예외 클래스 정의.

프로젝트 전반에서 사용되는 예외 계층 구조를 제공합니다.
"""


class AgentError(Exception):
    """Agent 관련 모든 예외의 베이스 클래스."""

    pass


class ConfigError(AgentError):
    """설정 관련 예외.

    환경 변수 누락, 잘못된 설정값 등의 경우 발생합니다.
    """

    pass


class PluginError(AgentError):
    """플러그인 관련 예외.

    Tool 실행 실패, Worker Agent 오류 등의 경우 발생합니다.
    """

    pass


class SessionError(AgentError):
    """세션 관리 관련 예외.

    세션 생성 실패, 만료된 세션 접근 등의 경우 발생합니다.
    """

    pass


class RouterError(AgentError):
    """라우팅 관련 예외.

    Worker 선택 실패, 잘못된 라우팅 결과 등의 경우 발생합니다.
    """

    pass


class WorkerError(AgentError):
    """Worker Agent 실행 관련 예외.

    Worker 실행 실패, 타임아웃 등의 경우 발생합니다.
    """

    pass


class SearchError(PluginError):
    """검색 관련 예외.

    Azure AI Search 연동 실패, 쿼리 오류 등의 경우 발생합니다.
    """

    pass
