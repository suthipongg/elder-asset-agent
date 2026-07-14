"""
Elder Asset Agent - Main agent implementation.
"""

import logging
from typing import Any

from llm.client import LLMClient
from agent.tool_executor import ToolExecutor
from agent.classify_tool import classify_tool
from agent.compliance_safety import ComplianceSafety
from agent.safe_request import handle_safe_request
from agent.memory import ConversationMemory
import json
logger = logging.getLogger(__name__)


class ElderAssetAgent:
    """
    An AI agent that assists elderly users with asset and financial management.

    The agent should:
    - Interpret natural language requests
    - Use the provided tools to gather information and take actions
    - Enforce safety policies (see data/policies/)
    - Handle errors, ambiguity, and edge cases gracefully
    """

    def __init__(self):
        self.llm = LLMClient()
        self.tool_executor = ToolExecutor()
        self.compliance_safety = ComplianceSafety(self.tool_executor)
        self.memory = ConversationMemory(max_turns=5)

    def solve(self, user_message: str) -> dict[str, Any]:
        """
        Process a user message and return a response.

        Args:
            user_message: The natural language message from the user.

        Returns:
            A dictionary with the following structure:
            {
                "status": "success" | "needs_clarification" | "handoff" | "refused",
                "message": str,              # user-facing response
                "tool_trace": list,          # every tool call with inputs/outputs
                "evidence": dict,            # IDs/fields used to justify claims
                "safety": {
                    "confirmations_requested": list,
                    "violations": list
                }
            }

            Status values:
            - "success": Request completed successfully
            - "needs_clarification": Ambiguous request, asking user for more info
            - "handoff": Escalated to human support (via support.create_case)
            - "refused": Request denied due to policy violation
        """
        self.tool_executor.reset()
        chat_history = self.memory.get_history()

        try:
            tool_result = classify_tool(user_message, chat_history, self.llm)
            print(json.dumps(tool_result, indent=2, ensure_ascii=False))
            tool_params = tool_result.get("tool_params", {})
            
            compliance_eval = self.compliance_safety.evaluate_action(
                compliance_context=tool_params.get("compliance.check", {}),
            )

            if not compliance_eval["action"]:
                response = self._build_response(
                    status=compliance_eval['status'],
                    message=compliance_eval['message'],
                    evidence=compliance_eval.get('evidence', {}),
                    violations=compliance_eval.get('violations', []),
                    confirmations=compliance_eval.get('confirmations_requested', []),
                )
                self.memory.add_turn(user_message, response["message"])
                return response
            
            result = handle_safe_request(
                user_message=user_message,
                requires_tools=tool_result.get("requires_tools", []),
                tool_params=tool_params,
                tool_executor=self.tool_executor,
                llm=self.llm,
                chat_history=chat_history,
            )

            response = self._build_response(
                status=result["status"],
                message=result["message"],
                evidence=result.get("evidence", {}),
            )
            self.memory.add_turn(user_message, response["message"])
            return response

        except Exception as e:
            print("Error in solve:", e)
            return self._build_response(
                status="needs_clarification",
                message=(
                    "ขออภัยค่ะ เกิดข้อผิดพลาดในการประมวลผล "
                    "กรุณาลองใหม่อีกครั้ง หรือติดต่อเจ้าหน้าที่ที่ 02-xxx-xxxx ค่ะ"
                ),
                violations=[f"internal_error:{type(e).__name__}"],
            )
            
    def _build_response(
        self,
        status: str,
        message: str,
        evidence: dict | None = None,
        violations: list | None = None,
        confirmations: list | None = None,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "message": message,
            "tool_trace": self.tool_executor.get_trace(),
            "evidence": evidence or {},
            "safety": {
                "confirmations_requested": confirmations or [],
                "violations": violations or [],
            },
        }