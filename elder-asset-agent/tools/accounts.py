"""
Account management tools.

Provides access to user account information.
"""

import json
import random
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"


def list_accounts() -> list[dict[str, Any]]:
    """
    List all accounts for the current user.

    Returns:
        List of account dictionaries, each containing:
        - account_id: str
        - account_type: str (checking, savings, investment)
        - account_name: str
        - balance: float
        - currency: str
        - status: str (active, frozen, closed)

    Raises:
        TimeoutError: Randomly, to simulate network issues
    """
    # Simulate occasional network timeout
    if random.random() < 0.05:
        raise TimeoutError("Account service temporarily unavailable")

    with open(DATA_DIR / "accounts.json", "r") as f:
        accounts = json.load(f)

    return accounts
