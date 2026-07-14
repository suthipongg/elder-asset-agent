import time
import logging
from typing import Any, Callable

from tools import (
    get_user,
    list_accounts,
    get_positions,
    search,
    get_risk_profile,
    check,
    create_case,
)

logger = logging.getLogger(__name__)


TOOL_REGISTRY: dict[str, Callable] = {
    "profile.get_user": get_user,
    "accounts.list_accounts": list_accounts,
    "portfolio.get_positions": get_positions,
    "transactions.search": search,
    "kyc.get_risk_profile": get_risk_profile,
    "compliance.check": check,
    "support.create_case": create_case,
}

# Default budget: max tool calls per solve() invocation
DEFAULT_BUDGET = 10

# Retry config
MAX_RETRIES = 3
BASE_DELAY_SEC = 0.5  # Exponential backoff base


MAX_CACHE_SIZE = 5

class ToolExecutor:
    def __init__(self, budget: int = DEFAULT_BUDGET):
        self.budget = budget
        self._calls_made = 0
        self._trace: list[dict[str, Any]] = []
        # _cache maps cache_key -> {"data": result, "freq": int, "last_accessed": float}
        self._cache: dict[tuple, dict[str, Any]] = {}

    def _make_hashable(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return tuple(sorted((k, self._make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return tuple(self._make_hashable(v) for v in obj)
        return obj

    def call(self, tool_name: str, **kwargs) -> Any:
        cache_key = (tool_name, self._make_hashable(kwargs))
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            entry["freq"] += 1
            entry["last_accessed"] = time.time()
            return entry["data"]

        if self._calls_made >= self.budget:
            raise Exception(
                f"Tool call budget exhausted ({self.budget} calls used). "
                "Cannot make more tool calls for this request."
            )

        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {tool_name}. Available: {list(TOOL_REGISTRY.keys())}")

        fn = TOOL_REGISTRY[tool_name]
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                result = fn(**kwargs)
                self._calls_made += 1

                self._trace.append({
                    "tool": tool_name,
                    "inputs": kwargs,
                    "output_summary": result,
                    "status": "success",
                    "attempt": attempt + 1,
                })

                self._add_to_cache(cache_key, result)
                return result

            except TimeoutError as e:
                last_error = e
                logger.warning(
                    f"Tool {tool_name} timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )

                if attempt < MAX_RETRIES - 1:
                    delay = BASE_DELAY_SEC * (2 ** attempt)
                    time.sleep(delay)

        self._calls_made += 1
        self._trace.append({
            "tool": tool_name,
            "inputs": kwargs,
            "output_summary": None,
            "status": "timeout",
            "attempt": MAX_RETRIES,
            "error": str(last_error),
        })

        raise TimeoutError(
            f"Tool {tool_name} failed after {MAX_RETRIES} retries: {last_error}"
        )

    def get_trace(self) -> list[dict[str, Any]]:
        return list(self._trace)

    def remaining_budget(self) -> int:
        return max(0, self.budget - self._calls_made)

    def calls_made(self) -> int:
        return self._calls_made

    def reset(self):
        self._calls_made = 0
        self._trace = []

    def _add_to_cache(self, cache_key: tuple, result: Any) -> None:
        if len(self._cache) >= MAX_CACHE_SIZE and cache_key not in self._cache:
            lfu_key = min(
                self._cache.keys(),
                key=lambda k: (self._cache[k]["freq"], self._cache[k]["last_accessed"])
            )
            del self._cache[lfu_key]
        self._cache[cache_key] = {
            "data": result,
            "freq": 1,
            "last_accessed": time.time()
        }