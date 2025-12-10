"""Supervisor Agent 데이터 모델."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RoutingResult(BaseModel):
    """라우팅 결과 모델."""

    worker: str = Field(..., description="선택된 Worker (원료/처방/규제)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")
    reasoning: str = Field(..., description="선택 이유")


class WorkerResponse(BaseModel):
    """Worker 응답 모델."""

    content: str = Field(..., description="응답 내용")
    sources: list[dict[str, str]] = Field(
        default_factory=list, description="참고 문서 리스트"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시각")
    metadata: dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


class SupervisorResponse(BaseModel):
    """Supervisor 최종 응답 모델."""

    content: str = Field(..., description="최종 응답 내용")
    worker: str = Field(..., description="사용된 Worker 이름")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시각")
    metadata: dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")
