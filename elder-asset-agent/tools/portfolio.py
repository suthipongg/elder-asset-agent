"""
Portfolio management tools.

Provides access to investment portfolio information.
"""

import json
import random
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"


def get_positions(account_id: str) -> dict[str, Any]:
    """
    Retrieve positions/holdings for an investment account.

    Note: Data may be stale. Check the 'last_updated' timestamp.

    Args:
        account_id: The investment account ID

    Returns:
        Dictionary containing:
        - account_id: str
        - last_updated: str (ISO format timestamp) - MAY BE STALE
        - is_stale: bool - True if data is more than 24 hours old
        - holdings: list of holdings, each containing:
            - symbol: str
            - name: str
            - quantity: float
            - current_price: float
            - market_value: float
            - cost_basis: float
            - gain_loss: float
            - gain_loss_percent: float
        - total_value: float
        - asset_allocation: dict with category percentages

    Raises:
        ValueError: If account is not an investment account
        TimeoutError: Randomly, to simulate network issues
    """
    # Simulate occasional network timeout
    if random.random() < 0.05:
        raise TimeoutError("Portfolio service temporarily unavailable")

    with open(DATA_DIR / "portfolio.json", "r") as f:
        portfolios = json.load(f)

    for portfolio in portfolios:
        if portfolio.get("account_id") == account_id:
            # Check if data is stale (more than 24 hours old)
            last_updated = datetime.fromisoformat(portfolio["last_updated"].replace("Z", "+00:00"))
            now = datetime.now(last_updated.tzinfo)
            is_stale = (now - last_updated) > timedelta(hours=24)

            return {
                "account_id": account_id,
                "last_updated": portfolio["last_updated"],
                "is_stale": is_stale,
                "holdings": portfolio["holdings"],
                "total_value": portfolio["total_value"],
                "asset_allocation": portfolio["asset_allocation"]
            }

    raise ValueError(f"No portfolio found for account: {account_id}")
