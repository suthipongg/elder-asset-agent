"""
KYC (Know Your Customer) tools.

Provides access to user risk profile information.
"""

import json
import random
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"


def get_risk_profile() -> dict[str, Any]:
    """
    Get the current user's investment risk profile.

    Returns:
        Dictionary containing:
        - risk_tolerance: str - "conservative", "moderate", or "aggressive"
        - investment_horizon: str - "short", "medium", or "long"
        - last_assessed: str (ISO format date)
        - notes: str | None - additional notes from assessment

    Raises:
        TimeoutError: Randomly, to simulate network issues
    """
    # Simulate occasional network timeout
    if random.random() < 0.05:
        raise TimeoutError("KYC service temporarily unavailable")

    with open(DATA_DIR / "users.json", "r") as f:
        users = json.load(f)

    user = users[0]
    risk_profile = user.get("risk_profile", {})

    return {
        "risk_tolerance": risk_profile.get("risk_tolerance", "conservative"),
        "investment_horizon": risk_profile.get("investment_horizon", "medium"),
        "last_assessed": risk_profile.get("last_assessed", "2023-01-15"),
        "notes": risk_profile.get("notes", ""),
    }
