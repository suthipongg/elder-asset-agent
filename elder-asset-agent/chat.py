#!/usr/bin/env python3
"""
Chat CLI for Elder Asset Agent.

A simple command-line interface for interacting with the agent.
Run with: python chat.py
"""

import sys
import json
from agent import ElderAssetAgent


def print_banner():
    """Print welcome banner."""
    print("=" * 60)
    print("  Elder Asset Agent - Chat Interface")
    print("=" * 60)
    print()
    print("Type your message and press Enter.")
    print("Commands: 'quit' or 'exit' to leave, 'clear' to reset.")
    print()


def print_response(response: dict):
    """Pretty print the agent response."""
    print()
    print("-" * 40)

    # Status indicator
    status = response.get("status", "unknown")
    status_icons = {
        "success": "[OK]",
        "needs_clarification": "[?]",
        "handoff": "[>>]",
        "refused": "[X]"
    }
    icon = status_icons.get(status, "[?]")

    print(f"{icon} Status: {status}")
    print("-" * 40)

    # Main message
    if "message" in response:
        print(response["message"])

    # Safety info
    safety = response.get("safety", {})
    confirmations = safety.get("confirmations_requested", [])
    violations = safety.get("violations", [])

    if confirmations:
        print()
        print(f"Confirmations required: {', '.join(confirmations)}")

    if violations:
        print()
        print(f"Policy violations: {', '.join(violations)}")

    # Tool trace (abbreviated)
    tool_trace = response.get("tool_trace", [])
    if tool_trace:
        print()
        print(f"Tools called: {len(tool_trace)}")
        for trace in tool_trace[:5]:  # Show first 5
            tool_name = trace.get("tool", "unknown")
            print(f"  - {tool_name}")
        if len(tool_trace) > 5:
            print(f"  ... and {len(tool_trace) - 5} more")

    print("-" * 40)
    print()


def main():
    """Main chat loop."""
    print_banner()

    try:
        agent = ElderAssetAgent()
    except Exception as e:
        print(f"Error initializing agent: {e}")
        sys.exit(1)

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if user_input.lower() == "clear":
                print("\033[2J\033[H")  # Clear screen
                print_banner()
                continue

            if user_input.lower() == "debug":
                print("Debug mode: Next response will show full JSON")
                user_input = input("You: ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break
                try:
                    response = agent.solve(user_input)
                    print(json.dumps(response, indent=2, default=str))
                except Exception as e:
                    print(f"[Error] {type(e).__name__}: {e}")
                continue

            # Call the agent
            try:
                response = agent.solve(user_input)
                print_response(response)
            except NotImplementedError:
                print()
                print("[Agent not implemented yet]")
                print("Implement the solve() method in agent/agent.py")
                print()
            except Exception as e:
                print()
                print(f"[Error] {type(e).__name__}: {e}")
                print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
