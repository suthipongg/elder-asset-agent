import pytest
from unittest.mock import Mock

from agent.safe_request import execute_safe_tools


@pytest.fixture
def mock_tool_executor():
    executor = Mock()
    return executor


def test_execute_safe_tools_skips_compliance(mock_tool_executor):
    """Test that compliance.check is skipped during data gathering."""
    requires_tools = ["compliance.check"]
    result = execute_safe_tools(requires_tools, {}, mock_tool_executor)
    
    assert result == {}
    mock_tool_executor.call.assert_not_called()


def test_execute_safe_tools_handles_support_create_case(mock_tool_executor):
    """Test that support.create_case IS executed (not skipped) for user requests."""
    mock_tool_executor.call.return_value = {
        "case_id": "CASE-001", "status": "open", "estimated_response": "24 hours"
    }
    
    requires_tools = ["support.create_case"]
    tool_params = {"support.create_case": {"summary": "ลูกค้าต้องการติดต่อเจ้าหน้าที่"}}
    result = execute_safe_tools(requires_tools, tool_params, mock_tool_executor)
    
    assert result["support_case"]["case_id"] == "CASE-001"
    mock_tool_executor.call.assert_called_once_with(
        "support.create_case",
        summary="ลูกค้าต้องการติดต่อเจ้าหน้าที่",
        evidence=[],
    )


def test_gather_balance_info(mock_tool_executor):
    """Test gathering balance info."""
    def mock_call(tool, **kwargs):
        if tool == "accounts.list_accounts":
            return [{"account_id": "acc-1"}]
        if tool == "profile.get_user":
            return {"name": "Test User"}
        raise ValueError(f"Unexpected tool: {tool}")
        
    mock_tool_executor.call.side_effect = mock_call
    
    requires_tools = ["accounts.list_accounts"]
    result = execute_safe_tools(requires_tools, {}, mock_tool_executor)
    
    assert "accounts" in result
    assert "user" in result
    assert result["accounts"] == [{"account_id": "acc-1"}]
    assert result["user"] == {"name": "Test User"}


def test_gather_transaction_info_with_account(mock_tool_executor):
    """Test gathering transactions when account_id is provided."""
    def mock_call(tool, **kwargs):
        if tool == "accounts.list_accounts":
            return [{"account_id": "acc-1"}]
        if tool == "transactions.search":
            return [
                {"transaction_id": "tx-1", "amount": 100},
                {"transaction_id": "tx-1", "amount": 100}, # duplicate
                {"transaction_id": "tx-2", "amount": -50}
            ]
        return None
        
    mock_tool_executor.call.side_effect = mock_call
    
    requires_tools = ["transactions.search"]
    tool_params = {
        "transactions.search": {
            "account_id": "acc-1",
            "filters": {"min_amount": 50}
        }
    }
    
    result = execute_safe_tools(requires_tools, tool_params, mock_tool_executor)
    
    assert result["accounts"] == [{"account_id": "acc-1"}]
    # 3 raw, 2 unique after dedup
    assert len(result["transactions"]) == 2
    mock_tool_executor.call.assert_any_call(
        "transactions.search", 
        account_id="acc-1", 
        filters={"min_amount": 50}
    )


def test_gather_transaction_info_missing_account(mock_tool_executor):
    """Test gathering transactions when account_id is missing (should prompt user)."""
    mock_tool_executor.call.return_value = [{"account_id": "acc-1"}]
    
    requires_tools = ["transactions.search"]
    tool_params = {} # missing account_id
    
    result = execute_safe_tools(requires_tools, tool_params, mock_tool_executor)
    
    assert isinstance(result["transactions"], str)
    assert "ERROR" in result["transactions"]
    assert "account_id" in result["transactions"]


def test_gather_transaction_info_multi_period(mock_tool_executor):
    """Test that LLM can query multiple months by passing a list of param sets."""
    def mock_call(tool, **kwargs):
        if tool == "accounts.list_accounts":
            return [{"account_id": "acc-1"}]
        if tool == "transactions.search":
            # Return different transactions based on date filter
            if kwargs.get("filters", {}).get("start_date") == "2023-12-01":
                return [{"transaction_id": "tx-dec", "amount": -100}]
            if kwargs.get("filters", {}).get("start_date") == "2024-06-01":
                return [{"transaction_id": "tx-jun", "amount": -200}]
        return []
    
    mock_tool_executor.call.side_effect = mock_call
    
    requires_tools = ["transactions.search"]
    tool_params = {
        "transactions.search": [
            {"account_id": "acc-1", "filters": {"start_date": "2023-12-01", "end_date": "2023-12-31"}},
            {"account_id": "acc-1", "filters": {"start_date": "2024-06-01", "end_date": "2024-06-30"}},
        ]
    }
    
    result = execute_safe_tools(requires_tools, tool_params, mock_tool_executor)
    
    # Should have called transactions.search twice
    assert mock_tool_executor.call.call_count == 3  # 1 list_accounts + 2 search
    # Should have transactions from both months merged together
    assert len(result["transactions"]) == 2
    txn_ids = {t["transaction_id"] for t in result["transactions"]}
    assert "tx-dec" in txn_ids
    assert "tx-jun" in txn_ids



def test_gather_portfolio_info(mock_tool_executor):
    """Test gathering investment portfolio and risk profile."""
    def mock_call(tool, **kwargs):
        if tool == "accounts.list_accounts":
            return [{"account_id": "inv-1", "account_type": "investment"}]
        if tool == "portfolio.get_positions":
            return {"account_id": "inv-1", "is_stale": True, "last_updated": "2026-07-13"}
        if tool == "kyc.get_risk_profile":
            return {"risk_tolerance": "moderate"}
        return None
        
    mock_tool_executor.call.side_effect = mock_call
    
    requires_tools = ["portfolio.get_positions"]
    result = execute_safe_tools(requires_tools, {}, mock_tool_executor)
    
    assert "portfolio" in result
    assert "is_stale" not in result["portfolio"]   # stripped by _strip_internal_fields
    assert "stale_warning" in result               # stale converted to human-readable warning
    assert result["risk_profile"]["risk_tolerance"] == "moderate"


def test_gather_data_timeout(mock_tool_executor):
    """Test that timeouts in tool calls are caught and set to None."""
    mock_tool_executor.call.side_effect = TimeoutError("Simulated timeout")
    
    requires_tools = ["accounts.list_accounts"]
    result = execute_safe_tools(requires_tools, {}, mock_tool_executor)
    
    # Should catch TimeoutError and return None for the field
    assert result["accounts"] is None
    assert result["user"] is None


def test_multiple_tools(mock_tool_executor):
    """Test executing multiple tools in one request."""
    def mock_call(tool, **kwargs):
        if tool == "accounts.list_accounts":
            return [{"account_id": "acc-1"}]
        if tool == "profile.get_user":
            return {"name": "Test"}
        if tool == "kyc.get_risk_profile":
            return {"risk_tolerance": "conservative"}
        return None
        
    mock_tool_executor.call.side_effect = mock_call
    
    requires_tools = ["accounts.list_accounts", "kyc.get_risk_profile"]
    result = execute_safe_tools(requires_tools, {}, mock_tool_executor)
    
    # Should combine outputs from both tools
    assert result["accounts"] == [{"account_id": "acc-1"}]
    assert result["user"] == {"name": "Test"}
    assert result["risk_profile"] == {"risk_tolerance": "conservative"}
