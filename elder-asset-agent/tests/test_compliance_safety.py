import pytest
from unittest.mock import Mock, patch

from agent.tool_executor import ToolExecutor
from agent.compliance_safety import (
    ComplianceSafety,
    FORBIDDEN_ACTIONS,
    MUST_HANDOFF_ACTIONS,
    USER_COMPLETABLE_ACTIONS,
    AGENT_REQUIRED_CONFIRMATIONS,
    USER_DOABLE_CONFIRMATIONS,
)


@pytest.fixture
def mock_tool_executor():
    executor = Mock(spec=ToolExecutor)
    return executor


@pytest.fixture
def compliance_safety(mock_tool_executor):
    return ComplianceSafety(mock_tool_executor)


# ============================================================
# เคส: Safe action (ไม่ใช่ FORBIDDEN_ACTION → ไม่ต้องเช็ค compliance)
# ============================================================
def test_evaluate_action_safe(compliance_safety, mock_tool_executor):
    """view_balance ไม่อยู่ใน FORBIDDEN_ACTIONS → ผ่านเลย ไม่เรียก compliance.check"""
    context = {"action": "view_balance"}
    result = compliance_safety.evaluate_action(context)
    
    assert result["action"] is True
    assert result["compliance_result"] is None
    mock_tool_executor.call.assert_not_called()


# ============================================================
# เคส 1: Refused — นโยบายไม่อนุญาตเลย (เช่น crypto)
# ============================================================
def test_case1_refused_crypto(compliance_safety, mock_tool_executor):
    """โอนเงินไป Bitcoin → compliance deny → status=refused"""
    context = {"action": "transfer_funds", "amount": 500, "destination": "Bitcoin wallet"}
    
    mock_tool_executor.call.return_value = {
        "allowed": False,
        "reason": "Cryptocurrency transfers are not permitted",
        "required_confirmations": [],
        "risk_level": "high"
    }
    
    result = compliance_safety.evaluate_action(context)
    
    assert result["action"] is False
    assert result["status"] == "refused"
    assert "Cryptocurrency" in result["message"]
    assert "action_denied:transfer_funds" in result["violations"]
    assert result["confirmations_requested"] == []


# ============================================================
# เคส 2: Handoff — มี verbal_confirmation / cooling_off_period
# ============================================================
def test_case2_handoff_verbal_confirmation(compliance_safety, mock_tool_executor):
    """โอนเงิน > 10,000 (elderly) → verbal_confirmation + sms_otp → handoff"""
    context = {"action": "transfer_funds", "amount": 15000, "destination": "ลูกชาย"}
    
    def mock_call(tool_name, **kwargs):
        if tool_name == "compliance.check":
            return {
                "allowed": True,
                "reason": "Action permitted with confirmations",
                "required_confirmations": ["verbal_confirmation", "sms_otp"],
                "risk_level": "high"
            }
        elif tool_name == "support.create_case":
            return {
                "case_id": "CASE-001",
                "status": "open",
                "estimated_response": "24 hours"
            }
        raise ValueError(f"Unexpected tool call: {tool_name}")
        
    mock_tool_executor.call.side_effect = mock_call
    
    result = compliance_safety.evaluate_action(context)
    
    assert result["action"] is False
    assert result["status"] == "handoff"
    assert "CASE-001" in result["message"]
    assert "ระบบ/เจ้าหน้าที่จะต้องใช้" in result["message"]
    assert "คุณลูกค้าต้องยืนยันตัวตนผ่าน" in result["message"]
    assert "verbal_confirmation" in result["confirmations_requested"]
    assert "sms_otp" in result["confirmations_requested"]


def test_case2_handoff_cooling_off(compliance_safety, mock_tool_executor):
    """โอนเงิน > 50,000 (elderly) → cooling_off_period + verbal + sms → handoff"""
    context = {"action": "transfer_funds", "amount": 60000}
    
    def mock_call(tool_name, **kwargs):
        if tool_name == "compliance.check":
            return {
                "allowed": True,
                "reason": "Action permitted with confirmations",
                "required_confirmations": ["verbal_confirmation", "cooling_off_period", "sms_otp"],
                "risk_level": "high"
            }
        elif tool_name == "support.create_case":
            return {"case_id": "CASE-002", "status": "open", "estimated_response": "24 hours"}
        raise ValueError(f"Unexpected tool call: {tool_name}")
        
    mock_tool_executor.call.side_effect = mock_call
    
    result = compliance_safety.evaluate_action(context)
    
    assert result["action"] is False
    assert result["status"] == "handoff"
    assert "Cooling-off" in result["message"]


# ============================================================
# เคส 3a: Financial action + แค่ sms_otp → ยังต้อง handoff เสมอ
# (ตาม Assignment: System Limitations — transfer ต้องผ่านเจ้าหน้าที่)
# ============================================================
def test_case3a_financial_with_sms_still_handoff(compliance_safety, mock_tool_executor):
    """elderly โอนเงินยอดน้อย → compliance ให้แค่ sms_otp → ต้อง handoff ไม่ใช่ needs_clarification"""
    context = {"action": "transfer_funds", "amount": 500}
    
    def mock_call(tool_name, **kwargs):
        if tool_name == "compliance.check":
            return {
                "allowed": True,
                "reason": "Action permitted with confirmations",
                "required_confirmations": ["sms_otp"],
                "risk_level": "medium"
            }
        elif tool_name == "support.create_case":
            return {"case_id": "CASE-004", "status": "open", "estimated_response": "24 hours"}
        raise ValueError(f"Unexpected tool call: {tool_name}")
        
    mock_tool_executor.call.side_effect = mock_call
    
    result = compliance_safety.evaluate_action(context)
    
    # ต้องเป็น handoff ไม่ใช่ needs_clarification! เพราะ transfer ต้องผ่านเจ้าหน้าที่เสมอ
    assert result["action"] is False
    assert result["status"] == "handoff"
    assert "เจ้าหน้าที่" in result["message"]
    assert "sms_otp" in result["confirmations_requested"]
    assert "CASE-004" in result["message"]


# ============================================================
# เคส 3b: User-completable action (update_profile) → needs_clarification
# ============================================================
def test_case3b_update_profile_needs_clarification(compliance_safety, mock_tool_executor):
    """update_profile (elderly) → email_confirm + sms_otp → needs_clarification (ไม่ต้องเจ้าหน้าที่)"""
    context = {"action": "update_profile"}
    
    mock_tool_executor.call.return_value = {
        "allowed": True,
        "reason": "Profile update permitted with confirmation",
        "required_confirmations": ["email_confirm", "sms_otp"],
        "risk_level": "low"
    }
    
    result = compliance_safety.evaluate_action(context)
    
    assert result["action"] is False
    assert result["status"] == "needs_clarification"
    assert "email_confirm" in result["confirmations_requested"]
    assert "sms_otp" in result["confirmations_requested"]
    # ต้องไม่สร้าง support case
    mock_tool_executor.call.assert_called_once()


# ============================================================
# เคส 4: Handoff ตรง — ไม่มี confirmations เลย แต่บอททำเองไม่ได้
# ============================================================
def test_case4_handoff_no_confirmations(compliance_safety, mock_tool_executor):
    """โอนเงินยอดน้อย (ไม่ใช่ elderly) → ไม่มี confirm → handoff ตรง"""
    context = {"action": "transfer_funds", "amount": 500}
    
    def mock_call(tool_name, **kwargs):
        if tool_name == "compliance.check":
            return {
                "allowed": True,
                "reason": "Action permitted",
                "required_confirmations": [],
                "risk_level": "medium"
            }
        elif tool_name == "support.create_case":
            return {"case_id": "CASE-003", "status": "open", "estimated_response": "24 hours"}
        raise ValueError(f"Unexpected tool call: {tool_name}")
        
    mock_tool_executor.call.side_effect = mock_call
    
    result = compliance_safety.evaluate_action(context)
    
    assert result["action"] is False
    assert result["status"] == "handoff"
    assert "CASE-003" in result["message"]
    assert result["confirmations_requested"] == []


# ============================================================
# Edge Cases
# ============================================================
def test_check_compliance_timeout(compliance_safety, mock_tool_executor):
    """Compliance service timeout → fail-safe deny"""
    context = {"action": "transfer_funds"}
    
    mock_tool_executor.call.side_effect = TimeoutError("Connection lost")
    
    result = compliance_safety.check_compliance("transfer_funds", context)
    
    assert result["allowed"] is False
    assert result["risk_level"] == "high"
    assert "ไม่สามารถตรวจสอบ" in result["reason"]


def test_support_case_creation_failure(compliance_safety, mock_tool_executor):
    """support.create_case พัง → ไม่ crash, ยังส่ง handoff ได้แต่ไม่มีเลขเคส"""
    context = {"action": "transfer_funds", "amount": 15000}
    
    def mock_call(tool_name, **kwargs):
        if tool_name == "compliance.check":
            return {
                "allowed": True,
                "required_confirmations": ["verbal_confirmation"],
                "reason": "OK",
                "risk_level": "high",
            }
        elif tool_name == "support.create_case":
            raise Exception("API Down")
            
    mock_tool_executor.call.side_effect = mock_call
    
    result = compliance_safety.evaluate_action(context)
    
    assert result["action"] is False
    assert result["status"] == "handoff"
    assert "เลขที่เคส" not in result["message"]
