from typing import Any

from llm.client import LLMClient


CLASSIFICATION_PROMPT = """คุณเป็นระบบจำแนกdการใช้ tool ของข้อความจากลูกค้าผู้สูงอายุในระบบจัดการสินทรัพย์

ให้วิเคราะห์ข้อความและตอบเป็น JSON ที่มี:
- "requires_tools": list ของ tools ที่น่าจะต้องใช้
- "tool_params": dict ของ parameters ที่ต้องส่งให้ tools (ดูรายละเอียดด้านล่าง)
- "reasoning": อธิบายสั้นๆ ว่าทำไมถึงต้องใช้ tool นี้

ตอบเป็น JSON เท่านั้น ไม่ต้องมีข้อความอื่น

รายละเอียด Tools และ Parameters ที่รองรับ:
- profile.get_user: 
    Retrieve the current user's profile information.

    Returns:
        Dictionary containing user profile data:
        - user_id: str
        - name: str
        - age: int
        - language_preference: str (e.g., "en", "es")
        - accessibility: dict with preferences like:
            - large_text: bool
            - screen_reader: bool
            - high_contrast: bool
- accounts.list_accounts: 
    List all accounts for the current user.

    Returns:
        List of account dictionaries, each containing:
        - account_id: str
        - account_type: str (checking, savings, investment)
        - account_name: str
        - balance: float
        - currency: str
        - status: str (active, frozen, closed)
- portfolio.get_positions: 
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
- transactions.search: 
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
- kyc.get_risk_profile: 
    Get the current user's investment risk profile.

    Returns:
        Dictionary containing:
        - risk_tolerance: str - "conservative", "moderate", or "aggressive"
        - investment_horizon: str - "short", "medium", or "long"
        - last_assessed: str (ISO format date)
        - notes: str | None - additional notes from assessment
- compliance.check: 
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
- support.create_case: 
    Create a support case for human review.

    Use this when the agent cannot handle a request or detects
    something that requires human intervention (e.g., potential fraud,
    complex requests, user distress).

    Args:
        summary: Brief description of the issue requiring human review
        evidence: Optional list of evidence items, each containing:
            - type: str (e.g., "transaction", "conversation", "screenshot")
            - data: Any - the actual evidence data
            - timestamp: str (ISO format)

    Returns:
        Dictionary containing:
        - case_id: str - unique identifier for the case
        - status: str - "open"
        - created_at: str (ISO format)
        - summary: str
        - evidence_count: int
        - estimated_response: str - expected response time
"""


def classify_tool(user_message: str, llm_client: LLMClient) -> dict[str, Any]:
    return {
        'requires_tools': ['profile.get_user', 'compliance.check'], 
        'tool_params': {'compliance.check':
            {
                'action': 'transfer_funds', 
                'context': {
                    'amount': 200.0, 
                    'destination': 'AC001'
                }
             }
        }, 
        'reasoning': 'test'
    }
    messages = [
        {"role": "system", "content": CLASSIFICATION_PROMPT},
        {"role": "user", "content": user_message},
    ]
    result = llm_client.generate_json(messages, temperature=0.1)
    return {
        "requires_tools": result.get("requires_tools", []),
        "tool_params": result.get("tool_params", {}),
        "reasoning": result.get("reasoning", ""),
    }
