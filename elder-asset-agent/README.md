# Elder Asset Agent

A coding assignment for AI Engineer candidates.

## Overview

Your task is to implement an AI agent that assists elderly users with asset and financial management tasks. The agent must interpret user requests, call the appropriate tools, enforce safety policies, and handle ambiguous or incomplete information gracefully.

## Getting Started

### Prerequisites

- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`

### Interactive Chat

Test your agent interactively:

```bash
python chat.py
```

### Running the Evaluation

```bash
python eval/run_eval.py
```

This will run your agent against the visible test cases and report pass/fail status.

## Repository Structure

```
elder-asset-agent/
├── agent/          # Your agent implementation goes here
├── tools/          # Mock tools (DO NOT MODIFY)
├── data/           # Mock data and policies (DO NOT MODIFY)
├── llm/            # LLM clients
├── tests/          # Tool tests (DO NOT MODIFY)
├── chat.py         # Interactive chat CLI
```

## Available Tools

| Tool | Function | Description |
|------|----------|-------------|
| `profile` | `get_user()` | User profile (age, language, accessibility) |
| `accounts` | `list_accounts()` | List user's accounts |
| `portfolio` | `get_positions(account_id)` | Holdings (may be stale) |
| `transactions` | `search(account_id, filters)` | Transaction search (may have duplicates) |
| `kyc` | `get_risk_profile()` | Risk tolerance: conservative/moderate/aggressive |
| `compliance` | `check(action, context)` | Policy check: allow/deny + required confirmations |
| `support` | `create_case(summary, evidence)` | Escalate to human support |

**Note:** Tools may randomly raise `TimeoutError` to simulate network issues.

## Rules

1. **Do not modify tools or data** - The `tools/` and `data/` directories simulate production.
2. **Tools are the only source of truth** - Do not access data files directly.

## Evaluation Criteria

Your submission will be evaluated on:

- Correct interpretation of user intent
- Appropriate tool usage
- Policy compliance and safety checks
- Handling of edge cases and failures
- Code quality and design decisions

Good luck!
