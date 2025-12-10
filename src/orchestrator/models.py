"""Orchestrator 데이터 모델.

세션, 쿼리 요청/응답 등의 데이터 구조를 정의합니다.
Agent Framework의 ChatMessage를 직접 활용합니다.
"""

from datetime import datetime
from typing import Any

from agent_framework import ChatMessage
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Session(BaseModel):
    """세션 정보.
    
    세션 관리를 위한 메타데이터를 포함합니다.
    대화 메시지는 Agent Framework의 ChatMessage를 사용합니다.
    """

    model_config = ConfigDict()

    session_id: str = Field(..., description="세션 고유 ID")
    user_id: str = Field(..., description="사용자 ID")
    created_at: datetime = Field(default_factory=datetime.now, description="세션 생성 시각")
    updated_at: datetime = Field(default_factory=datetime.now, description="마지막 업데이트 시각")
    # 대화 컨텍스트는 ContextManager에서 별도 관리

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """datetime을 ISO 형식으로 직렬화."""
        return value.isoformat()

class QueryRequest(BaseModel):
    """쿼리 요청."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user123",
                "query": "Cetearyl Alcohol 원료 찾아줘",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )

    user_id: str = Field(..., description="사용자 ID")
    query: str = Field(..., description="사용자 질의")
    session_id: str | None = Field(default=None, description="세션 ID (없으면 새로 생성)")


class QueryResponse(BaseModel):
    """쿼리 응답.
    
    API 레벨 응답 모델입니다.
    내부적으로는 Agent Framework의 ChatMessage를 사용하지만,
    API 응답 시 직렬화를 위해 간단한 형식으로 변환합니다.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "response": "Cetearyl Alcohol 원료를 찾았습니다...",
                "context": [
                    {"role": "user", "text": "Cetearyl Alcohol 원료 찾아줘"},
                    {"role": "assistant", "text": "Cetearyl Alcohol 원료를 찾았습니다..."}
                ],
                "metadata": {
                    "worker_used": "원료",
                    "timestamp": "2025-12-09T09:00:00",
                },
            }
        }
    )

    session_id: str = Field(..., description="세션 ID")
    response: str = Field(..., description="Assistant 응답")
    context: list[dict[str, Any]] = Field(
        default_factory=list, 
        description="대화 컨텍스트 (ChatMessage를 dict로 변환)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")

    @field_serializer("metadata")
    def serialize_metadata(self, value: dict[str, Any]) -> dict[str, Any]:
        """메타데이터 직렬화 (datetime 처리)."""
        result = {}
        for k, v in value.items():
            if isinstance(v, datetime):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result


def chat_message_to_dict(message: ChatMessage) -> dict[str, Any]:
    """ChatMessage를 딕셔너리로 변환합니다.
    
    API 응답에서 사용하기 위한 헬퍼 함수입니다.
    
    Args:
        message: Agent Framework의 ChatMessage
        
    Returns:
        딕셔너리 형태의 메시지
    """
    return {
        "role": str(message.role),
        "text": message.text or "",
        "author_name": message.author_name,
    }
