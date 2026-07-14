"""
Elder Asset Agent - Main agent implementation.
"""

import logging
from typing import Any

from llm.client import LLMClient
from agent.tool_executor import ToolExecutor
from agent.classify_tool import classify_tool
from agent.compliance_safety import ComplianceSafety
from agent.safe_request import execute_safe_tools, generate_response
from agent.utils import extract_evidence
from agent.memory import ConversationMemory

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
        tool_history = self.memory.get_tool_history()

        try:
            loop_count = 0
            max_loops = 3
            current_tool_outputs = {}
            executed_signatures = set()
            final_status = "success"
            compliance_violations = []
            
            while loop_count < max_loops:
                loop_count += 1
                context_for_classification = self._build_classification_context(tool_history, current_tool_outputs)
                tool_result = classify_tool(user_message, chat_history, context_for_classification, loop_count, self.llm)
                requires_tools = tool_result.get("requires_tools", [])
                tool_params = tool_result.get("tool_params", {})
                
                compliance_eval = self.compliance_safety.evaluate_action(
                    compliance_context=tool_params.get("compliance.check", {}),
                )
                if not compliance_eval["action"]:
                    final_status = compliance_eval['status']
                    compliance_violations = compliance_eval.get('violations', [])
                    response = self._build_response(
                        status=compliance_eval['status'],
                        message=compliance_eval['message'],
                        evidence=compliance_eval.get('evidence', {}),
                        violations=compliance_eval.get('violations', []),
                        confirmations=compliance_eval.get('confirmations_requested', []),
                    )
                    self.memory.add_turn(user_message, response["final message"])
                    return response
                
                new_tools, filtered_tool_params = self._filter_executed_tools(requires_tools, tool_params, executed_signatures)
                if not new_tools:
                    break # No new tools or parameters needed, exit loop
                
                new_outputs = execute_safe_tools(
                    requires_tools=new_tools,
                    tool_params=filtered_tool_params,
                    tool_executor=self.tool_executor
                )
                current_tool_outputs.update(new_outputs)
                
                if "system_errors" in new_outputs:
                    final_status = "needs_clarification"
                    break
                if not tool_result.get("has_next_step", True):
                    break

            evidence = extract_evidence(
                transactions=current_tool_outputs.get("transactions"),
                accounts=current_tool_outputs.get("accounts"),
                portfolio=current_tool_outputs.get("portfolio"),
            )
            response_message = generate_response(
                user_message=user_message,
                tool_outputs=current_tool_outputs,
                llm=self.llm,
                chat_history=chat_history
            )
            response = self._build_response(
                status=final_status,
                message=response_message,
                evidence=evidence,
                violations=compliance_violations,
            )
            self.memory.add_turn(user_message, response["final message"], tool_outputs=current_tool_outputs)
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
            
    def _build_classification_context(self, tool_history: dict, current_tool_outputs: dict) -> dict:
        context = tool_history.copy()
        for key, val in current_tool_outputs.items():
            if isinstance(val, list):
                existing = context.get(key, [])
                if isinstance(existing, list):
                    context[key] = existing + val
                else:
                    context[key] = val
            else:
                context[key] = val
        return context

    def _filter_executed_tools(self, requires_tools: list, tool_params: dict, executed_signatures: set) -> tuple[list, dict]:
        new_tools = []
        filtered_tool_params = {}
        
        for t in requires_tools:
            params = tool_params.get(t)
            param_list = params if isinstance(params, list) else [params] if params else [{}]
            new_param_list = []
            
            for p in param_list:
                sig = f"{t}:{json.dumps(p, sort_keys=True)}"
                if sig not in executed_signatures:
                    executed_signatures.add(sig)
                    new_param_list.append(p)
                    
            if new_param_list:
                new_tools.append(t)
                filtered_tool_params[t] = new_param_list if len(new_param_list) > 1 or isinstance(params, list) else new_param_list[0]
                
        return new_tools, filtered_tool_params

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
            "final message": message,
            "tool_trace": self.tool_executor.get_trace(),
            "evidence": evidence or {},
            "safety": {
                "confirmations_requested": confirmations or [],
                "violations": violations or [],
            },
        }