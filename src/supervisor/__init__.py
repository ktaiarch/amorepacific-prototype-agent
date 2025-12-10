"""Supervisor Agent 모듈.

Agent-as-Tool 패턴으로 Worker 자동 라우팅을 담당합니다.
"""

from .aggregator import Aggregator
from .models import RoutingResult, SupervisorResponse, WorkerResponse
from .prompts import ROUTER_INSTRUCTIONS, SUPERVISOR_INSTRUCTIONS
from .supervisor import SupervisorAgent
from .worker_tools import (
    create_worker_tools,
    search_formula_tool,
    search_ingredient_tool,
    search_regulation_tool,
)

__all__ = [
    "SupervisorAgent",
    "Aggregator",
    "RoutingResult",
    "WorkerResponse",
    "SupervisorResponse",
    "ROUTER_INSTRUCTIONS",
    "SUPERVISOR_INSTRUCTIONS",
    "create_worker_tools",
    "search_ingredient_tool",
    "search_formula_tool",
    "search_regulation_tool",
]
