import logging
from typing import Any

from agent.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


FORBIDDEN_ACTIONS = {
    "transfer_funds",
    "withdraw_funds",
    "buy_security",
    "sell_security",
    "change_beneficiary",
    "close_account",
    "update_profile",
}

SAFE_ACTIONS = {
    "view_balance",
    "view_transactions",
    "view_portfolio",
}


class ComplianceSafety:
    def __init__(self, tool_executor: ToolExecutor):
        self.tool_executor = tool_executor

    def check_compliance(
        self, action: str, compliance_context: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            result = self.tool_executor.call(
                "compliance.check",
                action=action,
                context=compliance_context,
            )
            return result
        except TimeoutError:
            # If compliance service is down, default to DENY (fail-safe)
            print("Compliance service unavailable — defaulting to deny")
            return {
                "allowed": False,
                "required_confirmations": [],
                "reason": "ไม่สามารถตรวจสอบความปลอดภัยได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง",
                "risk_level": "high",
            }

    def evaluate_action(
        self, compliance_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        compliance_context = compliance_context or {}
        action = compliance_context.get("action", None)

        if action and action in FORBIDDEN_ACTIONS:
            compliance_result = self.check_compliance(action, compliance_context)
            return {
                "action": False,
                "evidence": [],
                "message": '',
                "violations": '',
                "confirmations_requested": '',
            }

        return {
            "action": True,
            "compliance_result": None,
        }
