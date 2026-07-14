from typing import Any
from datetime import datetime

from llm.client import LLMClient
from agent.prompts import format_tool_data_for_prompt

TOOL_DESCRIPTION = """- profile.get_user: 
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
            - destination: str (for transfers) ถ้าแนวโน้มเป็น crypto, bitcoin ให้บอกด้วย
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
        - estimated_response: str - expected response time"""

CLASSIFICATION_PROMPT = """คุณเป็นระบบจำแนกการใช้ tool ของข้อความจากลูกค้าผู้สูงอายุในระบบจัดการสินทรัพย์
[ข้อมูลระบบ: วันที่ปัจจุบันคือ {current_date}]

ให้วิเคราะห์ข้อความและตอบเป็น JSON ที่มี:
- "requires_tools": list ของ tools ที่น่าจะต้องใช้ (เช่น ["accounts.list_accounts"], ["compliance.check"])
- "reasoning": อธิบายสั้นๆ ว่าทำไมถึงต้องใช้ tool นี้ และวิเคราะห์ว่าต้องใช้พารามิเตอร์อะไรบ้าง
- "tool_params": dict ของ parameters ที่ต้องส่งให้ tools (เฉพาะ parameters ที่จำเป็น)
- "has_next_step": boolean (true/false) ระบุว่าคุณต้องการข้อมูลอื่นเพิ่มอีกไหม (ถ้าได้ข้อมูลครบพอที่จะตอบผู้ใช้แล้ว หรือต้องการแค่เรียก Tool ในรอบนี้เป็นรอบสุดท้าย ให้ตอบ false)

ให้วิเคราะห์ข้อความและตอบกลับเป็น JSON ที่มีโครงสร้างแบบนี้เท่านั้น (ห้ามเพิ่มฟิลด์อื่น และห้ามมีข้อความอื่นนอกจาก JSON):

```json
{
  "requires_tools": [
    "tool_name_1",
    "tool_name_2"
  ],
  "reasoning": "เหตุผลสั้นๆ ที่เลือกใช้ tools และวิเคราะห์ว่าต้องดึงค่าอะไรมาใส่ใน parameters",
  "tool_params": {
    "tool_name_1": {
      "param_key": "param_value"
    }
  },
  "has_next_step": true
}
```

**กฎเหล็กเกี่ยวกับการเรียก Tools:**
1. ถ้าผู้ใช้ต้องการทำธุรกรรมที่มีผลกระทบ (เช่น โอนเงิน, ถอนเงิน, ซื้อขายหุ้น/กองทุน, เปลี่ยนผู้รับผลประโยชน์, ปิดบัญชี, อัพเดทโปรไฟล์) 
   -> **คุณต้องเรียกใช้ tool `compliance.check` เสมอ** เพื่อตรวจสอบสิทธิ์
   - ตัวอย่าง tool_params: {"compliance.check": {"action": "transfer_funds", "context": {"amount": 500, "destination": "ลูกชาย"}}}
2. ถ้าผู้ใช้แค่ขอดูยอดเงิน ดูประวัติ ดูพอร์ต หรือขอคำแนะนำทั่วไป (Read-only)
   -> **ห้ามเรียก `compliance.check` เด็ดขาด (ย้ำ! แค่ดูพอร์ตหรือประวัติไม่ต้องเช็ค)** ให้เรียกใช้ tools ดึงข้อมูลตามปกติ เช่น `accounts.list_accounts`, `transactions.search`, `portfolio.get_positions`
3. ถ้าผู้ใช้ต้องการติดต่อเจ้าหน้าที่, ขอพูดกับแอดมิน, หรือมีเรื่องเร่งด่วนที่บอทจัดการเองไม่ได้
   -> **เรียกใช้ `support.create_case`** พร้อมระบุ summary ที่สรุปเรื่องที่ user ต้องการ
   - ตัวอย่าง tool_params: {"support.create_case": {"summary": "ลูกค้าต้องการพูดคุยกับเจ้าหน้าที่เรื่องเร่งด่วน", "evidence": []}}
4. หากต้องการเรียก Tool เดิมซ้ำหลายครั้ง (เช่น ค้นหาธุรกรรมหลายช่วงเวลา หรือดูพอร์ตหลายบัญชี)
   -> **ให้ส่งพารามิเตอร์เป็น list ของ object**
   - ตัวอย่าง tool_params: {"transactions.search": [{"account_id": "ACC-1", "filters": {"start_date": "2023-12-01"}}, {"account_id": "ACC-1", "filters": {"start_date": "2024-06-01"}}]}
5. การดึงข้อมูลที่มีพารามิเตอร์: หากคุณต้องดึงข้อมูลที่ระบุเจาะจง (เช่น ดึงพอร์ต หรือ ธุรกรรม ของบัญชีใดบัญชีหนึ่ง) คุณต้องระบุพารามิเตอร์ให้ถูกต้องเสมอ
6. การจัดการเมื่อไม่ทราบพารามิเตอร์: **ห้ามเดาหรือสร้างพารามิเตอร์ (เช่น account_id) ขึ้นมาเองเด็ดขาด** หากคุณไม่ทราบค่าพารามิเตอร์ที่จำเป็น ให้ข้าม Tool นั้นไปก่อนในรอบนี้ **และให้เรียกใช้ Tool ค้นหาพื้นฐาน (เช่น `accounts.list_accounts`) แทน** เพื่อนำข้อมูลมาหาพารามิเตอร์ในรอบถัดไป (ระบบรองรับการทำงานแบบวนลูปหลายรอบเพื่อหาข้อมูลทีละขั้นตอน)
7. การระบุช่วงเวลา: หากผู้ใช้ขอข้อมูลย้อนหลังเป็นเดือน (เช่น "ย้อนหลัง 3 เดือน") ให้คุณระบุทั้ง `start_date` และ `end_date` เพื่อครอบคลุมช่วงเดือนที่ระบุอย่างชัดเจน (พิจารณาจากเดือนปัจจุบัน)

รายละเอียด Tools และ Parameters ที่รองรับ:
""" + TOOL_DESCRIPTION


def classify_tool(user_message: str, chat_history: list[dict], tool_history: dict, loop_count: int, llm_client: LLMClient) -> dict[str, Any]:
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = CLASSIFICATION_PROMPT.replace("{current_date}", current_date)
    
    if tool_history:
        tool_data_text = format_tool_data_for_prompt(tool_history)
        if tool_data_text.strip():
            prompt += f"\n\nข้อมูลบริบทปัจจุบันของผู้ใช้ (State) เพื่อใช้อ้างอิงพารามิเตอร์เช่น account_id:\n{tool_data_text}"
            
    if loop_count > 1:
        prompt += f"\n\n[คำสั่งพิเศษสำหรับ Loop {loop_count}]: คุณกำลังอยู่ในรอบการทำงานต่อเนื่อง (Continuation Loop) ข้อมูล State ด้านบนคือสิ่งที่คุณเพิ่งเรียกและดึงมาได้สำเร็จแล้ว ให้คุณวิเคราะห์ว่า **ยังมีข้อมูลส่วนไหนที่ขาดหายไปอีก** เพื่อเติมเต็มคำขอของผู้ใช้ และ **ให้เรียกเฉพาะ Tool ที่ยังไม่ได้เรียกเท่านั้น** (ห้ามเรียก Tool ที่มี param ซ้ำกับข้อมูลที่มีใน State แล้วเด็ดขาด เช่น หากใน State มี 'support_case' และ summary เดียวกันแล้ว ห้ามเรียก support.create_case ซ้ำอีก)"

    messages = [{"role": "system", "content": prompt}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})
    
    result = llm_client.generate_json(messages, temperature=0.1)
    return {
        "requires_tools": result.get("requires_tools", []),
        "tool_params": result.get("tool_params", {}),
        "reasoning": result.get("reasoning", ""),
        "has_next_step": result.get("has_next_step", True),
    }
