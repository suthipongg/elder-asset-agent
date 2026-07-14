import logging
from typing import Any

from agent.tool_executor import ToolExecutor
from agent.utils import deduplicate_transactions, extract_evidence, format_thb
from agent.prompts import (
    SYSTEM_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    GRACEFUL_DEGRADATION_TEMPLATE,
    format_tool_data_for_prompt,
)
from llm.client import LLMClient
import json
logger = logging.getLogger(__name__)


def handle_safe_request(
    user_message: str,
    requires_tools: list[str],
    tool_params: dict[str, Any],
    tool_executor: ToolExecutor,
    llm: LLMClient,
) -> dict[str, Any]:
    try:
        tool_outputs = execute_safe_tools(requires_tools, tool_params, tool_executor)
    except TimeoutError as e:
        service_name = str(e).split("Tool ")[1].split(" ")[0] if "Tool " in str(e) else "ข้อมูล"
        return {
            "status": "needs_clarification",
            "message": GRACEFUL_DEGRADATION_TEMPLATE.format(service=service_name),
            "evidence": {},
        }
    evidence = extract_evidence(
        transactions=tool_outputs.get("transactions"),
        accounts=tool_outputs.get("accounts"),
        portfolio=tool_outputs.get("portfolio"),
    )
    response_message = _generate_response(user_message, requires_tools, tool_outputs, llm)
    return {
        "status": "success",
        "message": response_message,
        "evidence": evidence,
    }


def execute_safe_tools(
    requires_tools: list[str],
    tool_params: dict[str, Any],
    tool_executor: ToolExecutor,
) -> dict[str, Any]:
    tool_outputs: dict[str, Any] = {}
    for tool_name in requires_tools:
        if tool_name == "compliance.check":
            continue
            
        new_outputs = _gather_data(tool_name, tool_params, tool_executor)
        print(json.dumps(new_outputs, indent=2, ensure_ascii=False))
        tool_outputs.update(new_outputs)
    
    return _strip_internal_fields(tool_outputs)


def _strip_internal_fields(tool_outputs: dict[str, Any]) -> dict[str, Any]:
    # --- accounts list ---
    for acc in tool_outputs.get("accounts") or []:
        acc.pop("created_at", None)   # internal metadata
        acc.pop("last_activity", None) # not needed for responses
        acc.pop("bank", None)          # might be redundant

    # --- portfolio ---
    portfolio = tool_outputs.get("portfolio")
    if isinstance(portfolio, dict):
        portfolio.pop("is_stale", None)     # handled via stale_warning key
        portfolio.pop("last_updated", None) # handled via stale_warning key

    # --- user profile ---
    user = tool_outputs.get("user")
    if isinstance(user, dict):
        user.pop("user_id", None)  # internal ID

    # --- support case ---
    case = tool_outputs.get("support_case")
    if isinstance(case, dict):
        case.pop("created_at", None)     # not useful for user
        case.pop("evidence_count", None) # not useful for user
        case.pop("status", None)         # always "open", not needed
        case.pop("summary", None)        # redundant (agent already knows)

    # --- KYC ---
    risk = tool_outputs.get("risk_profile")
    if isinstance(risk, dict):
        risk.pop("last_assessed", None)  # internal audit field

    return tool_outputs

def _gather_data(
    tool_name: str,
    tool_params: dict[str, Any],
    executor: ToolExecutor,
) -> dict[str, Any]:
    if tool_name == "accounts.list_accounts":
        return _gather_balance_info(executor)
    
    elif tool_name == "transactions.search":
        return _gather_transaction_info(tool_params, executor)
    
    elif tool_name == "portfolio.get_positions":
        return _gather_portfolio_info(executor)
    
    elif tool_name == "kyc.get_risk_profile":
        return _gather_guidance_info(executor)
    
    elif tool_name == "profile.get_user":
        return _gather_user_info(executor)
    
    elif tool_name == "support.create_case":
        support_params = tool_params.get("support.create_case", {})
        return _create_user_support_case(support_params, executor)
    
    else:
        print("Unknown safe tool: {tool_name}, falling back to balance")
        return _gather_balance_info(executor)


def _gather_balance_info(executor: ToolExecutor) -> dict[str, Any]:
    outputs: dict[str, Any] = {}

    try:
        outputs["accounts"] = executor.call("accounts.list_accounts")
    except TimeoutError:
        outputs["accounts"] = None

    try:
        outputs["user"] = executor.call("profile.get_user")
    except TimeoutError:
        outputs["user"] = None

    return outputs


def _gather_transaction_info(
    tool_params: dict[str, Any],
    executor: ToolExecutor,
) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    try:
        accounts = executor.call("accounts.list_accounts")
        outputs["accounts"] = accounts
    except TimeoutError:
        outputs["accounts"] = None
        return outputs

    txn_params = tool_params.get("transactions.search", {})
    account_id = txn_params.get("account_id")
    filters = txn_params.get("filters", None)

    if not account_id:
        outputs["transactions"] = (
            "ERROR: ไม่พบพารามิเตอร์ account_id "
            "โปรดถามผู้ใช้ว่าต้องการดูประวัติธุรกรรมของบัญชีไหน "
            "(เช่น ออมทรัพย์ หรือ กระแสรายวัน)"
        )
        return outputs

    try:
        raw_txns = executor.call(
            "transactions.search",
            account_id=account_id,
            filters=filters,
        )
        unique_txns = deduplicate_transactions(raw_txns)
        outputs["transactions"] = unique_txns
    except TimeoutError:
        outputs["transactions"] = None

    return outputs


def _gather_portfolio_info(executor: ToolExecutor) -> dict[str, Any]:
    outputs: dict[str, Any] = {}

    try:
        accounts = executor.call("accounts.list_accounts")
        outputs["accounts"] = accounts
    except TimeoutError:
        outputs["accounts"] = None
        return outputs

    investment_accounts = [
        a for a in accounts if a.get("account_type") == "investment"
    ]

    if investment_accounts:
        acc_id = investment_accounts[0]["account_id"]
        try:
            portfolio = executor.call("portfolio.get_positions", account_id=acc_id)
            outputs["portfolio"] = portfolio

            if portfolio.get("is_stale"):
                outputs["stale_warning"] = (
                    f"ข้อมูลพอร์ตอัพเดทล่าสุดเมื่อ {portfolio.get('last_updated')} "
                    "ราคาอาจไม่ตรงกับปัจจุบัน"
                )
        except TimeoutError:
            outputs["portfolio"] = None

    try:
        outputs["risk_profile"] = executor.call("kyc.get_risk_profile")
    except TimeoutError:
        outputs["risk_profile"] = None

    return outputs


def _gather_guidance_info(executor: ToolExecutor) -> dict[str, Any]:
    outputs: dict[str, Any] = {}

    try:
        outputs["accounts"] = executor.call("accounts.list_accounts")
    except TimeoutError:
        outputs["accounts"] = None

    try:
        outputs["risk_profile"] = executor.call("kyc.get_risk_profile")
    except TimeoutError:
        outputs["risk_profile"] = None

    try:
        outputs["user"] = executor.call("profile.get_user")
    except TimeoutError:
        outputs["user"] = None

    return outputs


def _gather_user_info(executor: ToolExecutor) -> dict[str, Any]:
    outputs: dict[str, Any] = {}

    try:
        outputs["user"] = executor.call("profile.get_user")
    except TimeoutError:
        outputs["user"] = None

    return outputs


def _create_user_support_case(
    support_params: dict[str, Any],
    executor: ToolExecutor,
) -> dict[str, Any]:
    outputs: dict[str, Any] = {}

    summary = support_params.get("summary", "ลูกค้าต้องการติดต่อเจ้าหน้าที่")
    evidence = support_params.get("evidence", [])

    try:
        case_result = executor.call(
            "support.create_case",
            summary=summary,
            evidence=evidence,
        )
        outputs["support_case"] = case_result
    except (TimeoutError, Exception) as e:
        logger.error(f"Failed to create user support case: {e}")
        outputs["support_case"] = None

    return outputs


def _generate_response(
    user_message: str,
    requires_tools: list[str],
    tool_outputs: dict[str, Any],
    llm: LLMClient,
) -> str:
    tool_data_text = format_tool_data_for_prompt(tool_outputs)

    prompt = RESPONSE_GENERATION_PROMPT.format(
        user_message=user_message,
        tool_data=tool_data_text,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        return llm.generate(messages, temperature=0.3)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return _fallback_response(tool_outputs)


def _fallback_response(tool_outputs: dict[str, Any]) -> str:
    parts = ["ข้อมูลที่ค้นพบ:\n"]

    if "accounts" in tool_outputs and tool_outputs["accounts"]:
        parts.append("บัญชีของท่าน:")
        for acc in tool_outputs["accounts"]:
            parts.append(
                f"  - {acc.get('account_name', 'N/A')}: "
                f"{format_thb(acc.get('balance', 0))}"
            )

    if "transactions" in tool_outputs and isinstance(tool_outputs["transactions"], list):
        parts.append(f"\nพบธุรกรรม {len(tool_outputs['transactions'])} รายการ")

    if "portfolio" in tool_outputs and tool_outputs["portfolio"]:
        portfolio = tool_outputs["portfolio"]
        parts.append(
            f"\nมูลค่าพอร์ตรวม: {format_thb(portfolio.get('total_value', 0))}"
        )

    parts.append("\nหากต้องการข้อมูลเพิ่มเติม กรุณาติดต่อเจ้าหน้าที่ค่ะ")
    return "\n".join(parts)
