"""
Support case tools.

Provides functionality for escalating issues to human support.
"""

import random
from typing import Any
from datetime import datetime
import uuid


def create_case(summary: str, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Create a support case for human review.

    Use this when the agent cannot handle a request or detects
    something that requires human intervention (e.g., potential fraud,
    complex requests, user distress).

    Args:
        summary: Brief description of the issue requiring human review
        evidence: Optional list of evidence items, each containing:
            - type: str (e.g., "transaction", "conversation", "screenshot")
            - data: Any - the actual evidence data
            - timestamp: str (ISO format)

    Returns:
        Dictionary containing:
        - case_id: str - unique identifier for the case
        - status: str - "open"
        - created_at: str (ISO format)
        - summary: str
        - evidence_count: int
        - estimated_response: str - expected response time

    Raises:
        ValueError: If summary is empty
        TimeoutError: Randomly, to simulate network issues
    """
    # Simulate occasional network timeout
    if random.random() < 0.05:
        raise TimeoutError("Support service temporarily unavailable")

    if not summary or not summary.strip():
        raise ValueError("Summary cannot be empty")

    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    evidence_list = evidence or []

    return {
        "case_id": case_id,
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "evidence_count": len(evidence_list),
        "estimated_response": "24 hours"
    }
