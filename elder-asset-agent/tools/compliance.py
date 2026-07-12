"""
Compliance checking tools.

Provides policy-based compliance checks for agent actions.
"""

import json
import random
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"


def check(action: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Check if an action is compliant with current policies.

    This is the primary tool for policy enforcement. The agent should
    call this before performing sensitive actions.

    Args:
        action: The action being performed. Known actions include:
            - view_balance
            - view_transactions
            - view_portfolio
            - transfer_funds
            - update_profile
            - change_beneficiary
            - close_account
            - withdraw_funds
            - buy_security
            - sell_security
        context: Additional context for the compliance check, may include:
            - amount: float (for financial actions)
            - destination: str (for transfers)
            - account_id: str
            - security: str (for trades)

    Returns:
        Dictionary containing:
        - allowed: bool - whether the action is permitted
        - required_confirmations: list - confirmations needed before proceeding
            May include: "sms_otp", "email_confirm", "security_questions",
                        "verbal_confirmation", "cooling_off_period"
        - reason: str - explanation of the decision
        - risk_level: str - "low", "medium", "high"

    Raises:
        TimeoutError: Randomly, to simulate network issues
    """
    # Simulate occasional network timeout
    if random.random() < 0.05:
        raise TimeoutError("Compliance service temporarily unavailable")

    # Load user data for context-aware checks
    with open(DATA_DIR / "users.json", "r") as f:
        users = json.load(f)
    user = users[0]
    user_age = user.get("age", 0)
    is_elderly = user_age >= 60

    # Read-only actions are generally allowed
    read_only_actions = ["view_balance", "view_transactions", "view_portfolio"]
    if action in read_only_actions:
        return {
            "allowed": True,
            "required_confirmations": [],
            "reason": "Read-only action permitted",
            "risk_level": "low"
        }

    # High-risk actions
    high_risk_actions = ["transfer_funds", "change_beneficiary", "close_account", "withdraw_funds"]
    if action in high_risk_actions:
        confirmations = []
        risk_level = "medium"

        amount = context.get("amount", 0)

        # Large amounts require more confirmations
        if amount > 10000:
            confirmations.append("verbal_confirmation")
            risk_level = "high"

        if amount > 50000:
            confirmations.append("cooling_off_period")

        # Elderly users get additional protections
        if is_elderly:
            if "sms_otp" not in confirmations:
                confirmations.append("sms_otp")
            if action in ["change_beneficiary", "close_account"]:
                confirmations.append("verbal_confirmation")
                risk_level = "high"

        # Check for suspicious patterns
        if action == "transfer_funds":
            destination = context.get("destination", "")
            if "crypto" in destination.lower() or "bitcoin" in destination.lower():
                return {
                    "allowed": False,
                    "required_confirmations": [],
                    "reason": "Cryptocurrency transfers are not permitted",
                    "risk_level": "high"
                }

        return {
            "allowed": True,
            "required_confirmations": confirmations,
            "reason": f"Action permitted with confirmations" if confirmations else "Action permitted",
            "risk_level": risk_level
        }

    # Trading actions
    trading_actions = ["buy_security", "sell_security"]
    if action in trading_actions:
        confirmations = []
        risk_level = "medium"

        amount = context.get("amount", 0)

        if amount > 25000:
            confirmations.append("verbal_confirmation")
            risk_level = "high"

        if is_elderly:
            confirmations.append("sms_otp")

        return {
            "allowed": True,
            "required_confirmations": confirmations,
            "reason": "Trading action permitted",
            "risk_level": risk_level
        }

    # Profile updates
    if action == "update_profile":
        confirmations = ["email_confirm"]
        if is_elderly:
            confirmations.append("sms_otp")

        return {
            "allowed": True,
            "required_confirmations": confirmations,
            "reason": "Profile update permitted with confirmation",
            "risk_level": "low"
        }

    # Unknown actions require manual review
    return {
        "allowed": False,
        "required_confirmations": [],
        "reason": f"Unknown action '{action}' requires manual review",
        "risk_level": "high"
    }
