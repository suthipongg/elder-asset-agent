"""
Transaction search tools.

Provides access to transaction history with realistic quirks.
"""

import json
import random
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"


def search(account_id: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Search transactions for an account.

    Note: Results may contain duplicates and some transactions
    may be missing optional fields. This is a known data quality issue.

    Args:
        account_id: The account to search transactions for
        filters: Optional filters including:
            - start_date: str (ISO format) - transactions on or after this date
            - end_date: str (ISO format) - transactions on or before this date
            - min_amount: float - minimum transaction amount
            - max_amount: float - maximum transaction amount
            - merchant: str - partial match on merchant name
            - category: str - transaction category

    Returns:
        List of transaction dictionaries. Note:
        - May contain duplicate transactions (known data quality issue)
        - Some transactions may be missing optional fields

        Each transaction contains:
        - transaction_id: str
        - account_id: str
        - amount: float (negative for debits, positive for credits)
        - currency: str
        - merchant: str (may be messy/inconsistent)
        - category: str (OPTIONAL - may be missing)
        - date: str (ISO format)
        - description: str (OPTIONAL - may be missing)
        - status: str (completed, pending, failed)

    Raises:
        TimeoutError: Randomly, to simulate network issues (10% rate)
    """
    # Simulate occasional network timeout (higher rate for this service)
    if random.random() < 0.10:
        raise TimeoutError("Transaction service temporarily unavailable")

    with open(DATA_DIR / "transactions.json", "r") as f:
        all_transactions = json.load(f)

    # Filter by account
    transactions = [t for t in all_transactions if t["account_id"] == account_id]

    if not filters:
        return transactions

    # Apply filters
    filtered = []
    for txn in transactions:
        # Date filters
        if "start_date" in filters:
            if txn["date"] < filters["start_date"]:
                continue
        if "end_date" in filters:
            if txn["date"] > filters["end_date"]:
                continue

        # Amount filters
        if "min_amount" in filters:
            if abs(txn["amount"]) < filters["min_amount"]:
                continue
        if "max_amount" in filters:
            if abs(txn["amount"]) > filters["max_amount"]:
                continue

        # Merchant filter (partial match, case-insensitive)
        if "merchant" in filters:
            if filters["merchant"].lower() not in txn.get("merchant", "").lower():
                continue

        # Category filter
        if "category" in filters:
            if txn.get("category") != filters["category"]:
                continue

        filtered.append(txn)

    return filtered
