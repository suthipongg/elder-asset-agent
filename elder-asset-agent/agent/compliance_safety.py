import logging
from typing import Any

from agent.tool_executor import ToolExecutor

from datetime import datetime

logger = logging.getLogger(__name__)


# Actions ที่ต้องส่งเจ้าหน้าที่เสมอ ไม่ว่า confirmations จะเป็นแค่ sms_otp ก็ตาม
# (ตาม Assignment: System Limitations — Requires Human Agent Escalation)
MUST_HANDOFF_ACTIONS = {
    "transfer_funds",
    "withdraw_funds",
    "buy_security",
    "sell_security",
    "change_beneficiary",
    "close_account",
}

# Actions ที่ user สามารถทำเองได้หลังยืนยันตัวตน (ไม่ต้องผ่านเจ้าหน้าที่)
USER_COMPLETABLE_ACTIONS = {
    "update_profile",
}

# รวมทั้งหมดที่ต้องเช็ค compliance
FORBIDDEN_ACTIONS = MUST_HANDOFF_ACTIONS | USER_COMPLETABLE_ACTIONS

SAFE_ACTIONS = {
    "view_balance",
    "view_transactions",
    "view_portfolio",
}

ACTION_THAI = {
    "transfer_funds": "โอนเงิน",
    "withdraw_funds": "ถอนเงิน",
    "buy_security": "ซื้อหลักทรัพย์",
    "sell_security": "ขายหลักทรัพย์",
    "change_beneficiary": "เปลี่ยนแปลงผู้รับผลประโยชน์",
    "close_account": "ปิดบัญชี",
    "update_profile": "อัปเดตข้อมูลส่วนตัว",
}

CONFIRMATION_THAI = {
    "sms_otp": "รหัส OTP (SMS)",
    "email_confirm": "ยืนยันผ่านอีเมล",
    "security_questions": "ตอบคำถามความปลอดภัย",
    "verbal_confirmation": "โทรศัพท์ยืนยันกับเจ้าหน้าที่",
    "cooling_off_period": "ระยะเวลาทบทวนรายการ (Cooling-off)",
}

# Confirmations ที่ต้องใช้เจ้าหน้าที่ดำเนินการ (บอท/ผู้ใช้ทำเองไม่ได้)
AGENT_REQUIRED_CONFIRMATIONS = {"verbal_confirmation", "cooling_off_period"}

# Confirmations ที่ผู้ใช้ทำเองได้ผ่านแชท (ไม่ต้องผ่านเจ้าหน้าที่)
USER_DOABLE_CONFIRMATIONS = {"sms_otp", "email_confirm", "security_questions"}


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
        actual_context = compliance_context.get("context", {})
        
        action_th = ACTION_THAI.get(action, action) if action else "ไม่ทราบคำสั่ง"

        if action and action in FORBIDDEN_ACTIONS:
            compliance_result = self.check_compliance(action, actual_context)
            
            # กรณีที่ 1: นโยบายไม่อนุญาตเลย (Refused)
            # เช่น โอนเงินไป crypto/bitcoin, unknown action
            if not compliance_result["allowed"]:
                return {
                    "action": False,
                    "status": "refused",
                    "evidence": {},
                    "message": (
                        f"❌ ขออภัยค่ะ ระบบไม่สามารถทำรายการ '{action_th}' ให้ได้\n\n"
                        f"เหตุผล: {compliance_result['reason']}\n\n"
                        f"หากท่านต้องการดำเนินการเรื่องนี้ กรุณาติดต่อเจ้าหน้าที่โดยตรงค่ะ"
                    ),
                    "violations": [f"action_denied:{action}"],
                    "confirmations_requested": [],
                }
            
            # นโยบายอนุญาต → แยกประเภท confirmations
            confirmations = list(set(compliance_result.get("required_confirmations", [])))
            agent_confirms = [c for c in confirmations if c in AGENT_REQUIRED_CONFIRMATIONS]
            user_confirms = [c for c in confirmations if c in USER_DOABLE_CONFIRMATIONS]
            
            agent_confirms_th = [CONFIRMATION_THAI.get(c, c) for c in agent_confirms]
            user_confirms_th = [CONFIRMATION_THAI.get(c, c) for c in user_confirms]
                
            # กรณีที่ 2: มี verbal_confirmation หรือ cooling_off_period → ต้องส่งเจ้าหน้าที่ (Handoff)
            # เช่น โอนเงิน > 10,000 (verbal), > 50,000 (cooling), change_beneficiary (elderly)
            if agent_confirms:
                case_info, evidence_data = self._create_support_case(action, actual_context, compliance_result)
                
                confirm_parts = []
                if user_confirms:
                    confirm_parts.append(f"- คุณลูกค้าต้องยืนยันตัวตนผ่าน: {', '.join(user_confirms_th)}")
                if agent_confirms:
                    confirm_parts.append(f"- ระบบ/เจ้าหน้าที่จะต้องใช้: {', '.join(agent_confirms_th)}")
                confirm_text = "\n".join(confirm_parts)

                return {
                    "action": False,
                    "status": "handoff",
                    "evidence": {"case_evidence": evidence_data},
                    "message": (
                        f"⚠️ รายการ '{action_th}' ของคุณลูกค้า จำเป็นต้องดำเนินการผ่านเจ้าหน้าที่เพื่อความปลอดภัยค่ะ\n\n"
                        f"ขั้นตอนที่ต้องดำเนินการ:\n{confirm_text}\n"
                        f"{case_info}"
                    ),
                    "violations": [],
                    "confirmations_requested": confirmations,
                }
            
            # กรณีที่ 3: มีแค่ sms_otp / email_confirm (ไม่มี verbal/cooling)
            if user_confirms:
                # 3a: ถ้าเป็น financial action (โอนเงิน, ซื้อขาย ฯลฯ) → ต้อง handoff เสมอ ตาม System Limitations
                # เช่น elderly โอนเงินยอดน้อย → compliance ให้แค่ sms_otp → แต่บอททำเองไม่ได้อยู่ดี
                if action in MUST_HANDOFF_ACTIONS:
                    case_info, evidence_data = self._create_support_case(action, actual_context, compliance_result)
                    return {
                        "action": False,
                        "status": "handoff",
                        "evidence": {"case_evidence": evidence_data},
                        "message": (
                            f"⚠️ รายการ '{action_th}' ของคุณลูกค้า จำเป็นต้องดำเนินการผ่านเจ้าหน้าที่เพื่อความปลอดภัยค่ะ\n\n"
                            f"ขั้นตอนที่ต้องดำเนินการ:\n"
                            f"- คุณลูกค้าต้องยืนยันตัวตนผ่าน: {', '.join(user_confirms_th)}\n"
                            f"{case_info}"
                        ),
                        "violations": [],
                        "confirmations_requested": user_confirms,
                    }
                
                # 3b: ถ้าเป็น action ที่ user ทำเองได้ (เช่น update_profile) → ถามยืนยันก่อน
                return {
                    "action": False,
                    "status": "needs_clarification",
                    "evidence": {},
                    "message": (
                        f"🔒 เพื่อความปลอดภัย กรุณายืนยันตัวตนก่อนทำรายการ '{action_th}' ค่ะ\n"
                        f"ระบบจะส่งรหัสยืนยันไปทาง: {', '.join(user_confirms_th)}"
                    ),
                    "violations": [],
                    "confirmations_requested": user_confirms,
                }
            
            # กรณีที่ 4: ไม่มี confirmations เลย แต่เป็น FORBIDDEN_ACTION → Handoff ตรง
            # เช่น โอนเงินยอดน้อย (ไม่ใช่ elderly, ไม่ต้อง confirm อะไร) → แต่บอททำเองไม่ได้อยู่ดี
            case_info, evidence_data = self._create_support_case(action, actual_context, compliance_result)
            return {
                "action": False,
                "status": "handoff",
                "evidence": {"case_evidence": evidence_data},
                "message": (
                    f"⚠️ รายการ '{action_th}' ของคุณลูกค้า จำเป็นต้องดำเนินการผ่านเจ้าหน้าที่ค่ะ\n"
                    f"ระบบได้ส่งเรื่องให้เจ้าหน้าที่ดูแลเรียบร้อยแล้ว\n"
                    f"{case_info}"
                ),
                "violations": [],
                "confirmations_requested": [],
            }

        return {
            "action": True,
            "compliance_result": None,
        }

    def _create_support_case(
        self,
        action: str,
        context: dict[str, Any],
        compliance_result: dict[str, Any],
    ) -> tuple[str, list[dict]]:
        request_details = {k: v for k, v in context.items() if k != "action"}
        
        # แยก confirmations ตามหน้าที่
        all_confirmations = compliance_result.get("required_confirmations", [])
        agent_confirms = [c for c in all_confirmations if c in AGENT_REQUIRED_CONFIRMATIONS]
        user_confirms = [c for c in all_confirmations if c in USER_DOABLE_CONFIRMATIONS]

        evidence = [
            {
                "type": "action_request",
                "data": {
                    "action": action,
                    "details": request_details,
                },
                "timestamp": datetime.now().isoformat(),
            },
            {
                "type": "compliance_decision",
                "data": {
                    "allowed": compliance_result.get("allowed"),
                    "reason": compliance_result.get("reason"),
                    "risk_level": compliance_result.get("risk_level"),
                },
                "timestamp": datetime.now().isoformat(),
            },
            {
                "type": "required_confirmations",
                "data": {
                    "agent_required": agent_confirms,
                    "user_completed": user_confirms,
                },
                "timestamp": datetime.now().isoformat(),
            },
        ]
        
        # สร้าง summary ที่มีรายละเอียดเพียงพอให้เจ้าหน้าที่เข้าใจทันที
        summary_parts = [f"Handoff: ลูกค้าต้องการ {action}"]
        if request_details.get("amount"):
            summary_parts.append(f"ยอด {request_details['amount']}")
        if request_details.get("destination"):
            summary_parts.append(f"ปลายทาง {request_details['destination']}")
        if request_details.get("security"):
            summary_parts.append(f"หลักทรัพย์ {request_details['security']}")
        summary_parts.append(f"[risk: {compliance_result.get('risk_level', 'unknown')}]")
        summary = " | ".join(summary_parts)

        try:
            case_result = self.tool_executor.call(
                "support.create_case",
                summary=summary,
                evidence=evidence,
            )
            case_info = f"\nเลขที่เคส: {case_result.get('case_id')} — เจ้าหน้าที่จะติดต่อกลับภายใน {case_result.get('estimated_response')}"
        except Exception as e:
            logger.error(f"Failed to create support case: {e}")
            case_info = ""
            
        return case_info, evidence