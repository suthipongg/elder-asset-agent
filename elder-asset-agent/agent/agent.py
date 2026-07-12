"""
Elder Asset Agent - Main agent implementation.
"""

from typing import Any, Literal


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
        """Initialize the agent."""
        # TODO: Set up your agent architecture
        pass

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

        TODO: Implement your agent logic
        """
        raise NotImplementedError("Agent logic not implemented")
