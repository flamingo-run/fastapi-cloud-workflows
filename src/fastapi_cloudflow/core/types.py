from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request


@dataclass
class WorkflowMeta:
    name: str | None = None
    step: str | None = None
    run_id: str | None = None


@dataclass
class Context:
    request: Request
    workflow: WorkflowMeta


@dataclass
class RetryPolicy:
    max_retries: int = 5
    initial_delay_s: float = 1.0
    max_delay_s: float = 30.0
    multiplier: float = 2.0
    predicate: str = "http.default_retry_predicate"

    @staticmethod
    def idempotent_http() -> RetryPolicy:
        return RetryPolicy(
            max_retries=5,
            initial_delay_s=1.0,
            max_delay_s=30.0,
            multiplier=2.0,
            predicate="http.default_retry_predicate",
        )
