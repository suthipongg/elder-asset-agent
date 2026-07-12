"""
Tests for the mock tools.

These tests verify that the tools work correctly and return expected data structures.
Run with: pytest tests/test_tools.py -v
"""

import pytest
from unittest.mock import patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import (
    get_user,
    list_accounts,
    get_positions,
    search,
    get_risk_profile,
    check,
    create_case,
)


# Fixture to disable random timeouts for all tests by default
@pytest.fixture(autouse=True)
def disable_random_timeouts(monkeypatch):
    """Disable random timeouts for deterministic tests."""
    monkeypatch.setattr("tools.profile.random.random", lambda: 0.99)
    monkeypatch.setattr("tools.accounts.random.random", lambda: 0.99)
    monkeypatch.setattr("tools.portfolio.random.random", lambda: 0.99)
    monkeypatch.setattr("tools.transactions.random.random", lambda: 0.99)
    monkeypatch.setattr("tools.kyc.random.random", lambda: 0.99)
    monkeypatch.setattr("tools.compliance.random.random", lambda: 0.99)
    monkeypatch.setattr("tools.support.random.random", lambda: 0.99)


# =============================================================================
# Profile Tests: get_user()
# =============================================================================


class TestGetUser:
    """Tests for profile.get_user()"""

    def test_returns_user_profile(self):
        """Should return user profile with required fields."""
        user = get_user()

        assert "user_id" in user
        assert "name" in user
        assert "age" in user
        assert "language_preference" in user
        assert "accessibility" in user

    def test_user_is_elderly(self):
        """User should be elderly (age >= 60)."""
        user = get_user()
        assert user["age"] >= 60

    def test_user_is_thai(self):
        """User should be Thai with Thai language preference."""
        user = get_user()
        assert user["language_preference"] == "th"

    def test_accessibility_preferences(self):
        """Should return accessibility preferences."""
        user = get_user()

        assert "large_text" in user["accessibility"]
        assert "screen_reader" in user["accessibility"]
        assert "high_contrast" in user["accessibility"]

    def test_timeout_error(self, monkeypatch):
        """Should raise TimeoutError occasionally."""
        monkeypatch.setattr("tools.profile.random.random", lambda: 0.01)
        with pytest.raises(TimeoutError):
            get_user()


# =============================================================================
# Accounts Tests: list_accounts()
# =============================================================================


class TestListAccounts:
    """Tests for accounts.list_accounts()"""

    def test_returns_list_of_accounts(self):
        """Should return a list of accounts."""
        accounts = list_accounts()

        assert isinstance(accounts, list)
        assert len(accounts) > 0

    def test_account_structure(self):
        """Each account should have required fields."""
        accounts = list_accounts()

        for account in accounts:
            assert "account_id" in account
            assert "account_type" in account
            assert "account_name" in account
            assert "balance" in account
            assert "currency" in account
            assert "status" in account

    def test_currency_is_thb(self):
        """All accounts should be in THB."""
        accounts = list_accounts()

        for account in accounts:
            assert account["currency"] == "THB"

    def test_has_investment_account(self):
        """Should have at least one investment account."""
        accounts = list_accounts()

        investment_accounts = [a for a in accounts if a["account_type"] == "investment"]
        assert len(investment_accounts) >= 1

    def test_account_types(self):
        """Should have checking, savings, and investment accounts."""
        accounts = list_accounts()

        account_types = {a["account_type"] for a in accounts}
        assert "checking" in account_types
        assert "savings" in account_types
        assert "investment" in account_types

    def test_timeout_error(self, monkeypatch):
        """Should raise TimeoutError occasionally."""
        monkeypatch.setattr("tools.accounts.random.random", lambda: 0.01)
        with pytest.raises(TimeoutError):
            list_accounts()


# =============================================================================
# Portfolio Tests: get_positions(account_id)
# =============================================================================


class TestGetPositions:
    """Tests for portfolio.get_positions()"""

    def test_returns_positions_for_valid_account(self):
        """Should return positions for valid investment account."""
        positions = get_positions("ACC-1003")

        assert "account_id" in positions
        assert "holdings" in positions
        assert "total_value" in positions
        assert "last_updated" in positions
        assert "is_stale" in positions
        assert "asset_allocation" in positions

    def test_holdings_structure(self):
        """Each holding should have required fields."""
        positions = get_positions("ACC-1003")

        assert len(positions["holdings"]) > 0
        for holding in positions["holdings"]:
            assert "symbol" in holding
            assert "name" in holding
            assert "quantity" in holding
            assert "current_price" in holding
            assert "market_value" in holding

    def test_holdings_are_thai_funds(self):
        """Holdings should include Thai mutual funds."""
        positions = get_positions("ACC-1003")

        symbols = [h["symbol"] for h in positions["holdings"]]
        # Should have Thai fund symbols
        assert any("RMF" in s or "K-" in s or "SCB" in s for s in symbols)

    def test_invalid_account_raises_error(self):
        """Should raise ValueError for invalid account."""
        with pytest.raises(ValueError, match="No portfolio found"):
            get_positions("INVALID-ACCOUNT")

    def test_is_stale_flag(self):
        """Should include is_stale flag based on last_updated."""
        positions = get_positions("ACC-1003")
        assert isinstance(positions["is_stale"], bool)

    def test_asset_allocation(self):
        """Should return asset allocation breakdown."""
        positions = get_positions("ACC-1003")

        assert isinstance(positions["asset_allocation"], dict)
        assert len(positions["asset_allocation"]) > 0

    def test_timeout_error(self, monkeypatch):
        """Should raise TimeoutError occasionally."""
        monkeypatch.setattr("tools.portfolio.random.random", lambda: 0.01)
        with pytest.raises(TimeoutError):
            get_positions("ACC-1003")


# =============================================================================
# Transactions Tests: search(account_id, filters)
# =============================================================================


class TestSearch:
    """Tests for transactions.search()"""

    def test_returns_transactions_for_account(self):
        """Should return transactions for valid account."""
        transactions = search("ACC-1001")

        assert isinstance(transactions, list)
        assert len(transactions) > 0

    def test_transaction_structure(self):
        """Each transaction should have required fields."""
        transactions = search("ACC-1001")

        for txn in transactions:
            assert "transaction_id" in txn
            assert "account_id" in txn
            assert "amount" in txn
            assert "date" in txn
            assert "merchant" in txn
            assert "status" in txn

    def test_currency_is_thb(self):
        """All transactions should be in THB."""
        transactions = search("ACC-1001")

        for txn in transactions:
            assert txn["currency"] == "THB"

    def test_has_pension_income(self):
        """Should have pension income from Social Security."""
        transactions = search("ACC-1001")

        pension_txns = [t for t in transactions if "ประกันสังคม" in t.get("merchant", "") or "PENSION" in t.get("merchant", "")]
        assert len(pension_txns) > 0

    def test_has_electricity_bill(self):
        """Should have electricity bill payment."""
        transactions = search("ACC-1001")

        electric_txns = [t for t in transactions if "ไฟฟ้า" in t.get("merchant", "") or "กฟน" in t.get("merchant", "") or "MEA" in t.get("merchant", "")]
        assert len(electric_txns) > 0

    def test_filter_by_date_range(self):
        """Should filter transactions by date range."""
        transactions = search(
            "ACC-1001",
            filters={"start_date": "2024-01-01", "end_date": "2024-01-15"}
        )

        for txn in transactions:
            assert txn["date"] >= "2024-01-01"
            assert txn["date"] <= "2024-01-15"

    def test_filter_by_merchant(self):
        """Should filter transactions by merchant (partial match)."""
        transactions = search("ACC-1001", filters={"merchant": "GRAB"})

        assert len(transactions) > 0
        for txn in transactions:
            assert "grab" in txn["merchant"].lower()

    def test_filter_by_min_amount(self):
        """Should filter transactions by minimum amount."""
        transactions = search("ACC-1001", filters={"min_amount": 1000})

        for txn in transactions:
            assert abs(txn["amount"]) >= 1000

    def test_contains_duplicates(self):
        """Transactions should contain duplicates (data quality issue)."""
        transactions = search("ACC-1001")

        ids = [t["transaction_id"] for t in transactions]
        assert len(ids) != len(set(ids)), "Expected duplicate transactions"

    def test_inconsistent_merchant_names(self):
        """Same merchants may have different names (data quality issue)."""
        transactions = search("ACC-1001")

        merchants = [t["merchant"] for t in transactions]
        # Should have inconsistent naming (e.g., "GRAB*TRIP-BKK" vs "GRAB TH*TRIP")
        grab_variants = [m for m in merchants if "grab" in m.lower()]
        assert len(grab_variants) > 1, "Expected multiple GRAB transaction variants"
        # Merchant names should be different even for same service
        assert len(set(grab_variants)) > 1, "Expected different merchant name formats"

    def test_some_mixed_language_memos(self):
        """Some descriptions may contain mixed Thai/English text."""
        transactions = search("ACC-1001")

        descriptions = [t.get("description", "") for t in transactions if t.get("description")]
        # Most descriptions are pure Thai or English, but some may be mixed
        thai_only = [d for d in descriptions if all(ord(c) > 127 or not c.isalpha() for c in d)]
        english_only = [d for d in descriptions if all(ord(c) < 128 for c in d)]
        mixed = [d for d in descriptions if any(ord(c) > 127 for c in d) and any(c.isascii() and c.isalpha() for c in d)]

        # Should have mostly pure Thai/English with occasional mixed
        assert len(thai_only) + len(english_only) > len(mixed), \
            "Most descriptions should be pure Thai or English"

    def test_missing_optional_fields(self):
        """Some transactions should be missing optional fields."""
        transactions = search("ACC-1001")

        missing_category = any("category" not in t for t in transactions)
        missing_description = any("description" not in t for t in transactions)

        assert missing_category or missing_description, \
            "Expected some transactions to be missing optional fields"

    def test_empty_for_invalid_account(self):
        """Should return empty list for invalid account."""
        transactions = search("INVALID-ACCOUNT")
        assert transactions == []

    def test_timeout_error(self, monkeypatch):
        """Should raise TimeoutError occasionally (10% rate)."""
        monkeypatch.setattr("tools.transactions.random.random", lambda: 0.01)
        with pytest.raises(TimeoutError):
            search("ACC-1001")


# =============================================================================
# KYC Tests: get_risk_profile()
# =============================================================================


class TestGetRiskProfile:
    """Tests for kyc.get_risk_profile()"""

    def test_returns_risk_profile(self):
        """Should return risk profile with required fields."""
        profile = get_risk_profile()

        assert "risk_tolerance" in profile
        assert "investment_horizon" in profile
        assert "last_assessed" in profile

    def test_risk_tolerance_values(self):
        """Risk tolerance should be valid value."""
        profile = get_risk_profile()

        valid_values = ["conservative", "moderate", "aggressive"]
        assert profile["risk_tolerance"] in valid_values

    def test_investment_horizon_values(self):
        """Investment horizon should be valid value."""
        profile = get_risk_profile()

        valid_values = ["short", "medium", "long"]
        assert profile["investment_horizon"] in valid_values

    def test_timeout_error(self, monkeypatch):
        """Should raise TimeoutError occasionally."""
        monkeypatch.setattr("tools.kyc.random.random", lambda: 0.01)
        with pytest.raises(TimeoutError):
            get_risk_profile()


# =============================================================================
# Compliance Tests: check(action, context)
# =============================================================================


class TestCheck:
    """Tests for compliance.check()"""

    def test_read_only_actions_allowed(self):
        """Read-only actions should be allowed without confirmations."""
        for action in ["view_balance", "view_transactions", "view_portfolio"]:
            result = check(action, {})

            assert result["allowed"] is True
            assert result["required_confirmations"] == []
            assert result["risk_level"] == "low"

    def test_transfer_requires_sms_for_elderly(self):
        """Transfers should require SMS OTP for elderly users."""
        result = check("transfer_funds", {"amount": 5000})

        assert result["allowed"] is True
        assert "sms_otp" in result["required_confirmations"]

    def test_large_transfer_requires_verbal_confirmation(self):
        """Large transfers (>200k THB) should require verbal confirmation."""
        result = check("transfer_funds", {"amount": 250000})

        assert result["allowed"] is True
        assert "verbal_confirmation" in result["required_confirmations"]
        assert result["risk_level"] == "high"

    def test_very_large_transfer_requires_cooling_off(self):
        """Very large transfers (>1M THB) should require cooling-off period."""
        result = check("transfer_funds", {"amount": 1500000})

        assert result["allowed"] is True
        assert "cooling_off_period" in result["required_confirmations"]

    def test_crypto_transfer_blocked(self):
        """Cryptocurrency transfers should be blocked."""
        result = check("transfer_funds", {"amount": 10000, "destination": "Bitcoin wallet"})

        assert result["allowed"] is False
        assert "crypto" in result["reason"].lower() or "not permitted" in result["reason"].lower()

    def test_beneficiary_change_high_risk(self):
        """Beneficiary changes should be high risk for elderly."""
        result = check("change_beneficiary", {})

        assert result["allowed"] is True
        assert "verbal_confirmation" in result["required_confirmations"]
        assert result["risk_level"] == "high"

    def test_trading_actions(self):
        """Trading actions should require confirmation for elderly."""
        for action in ["buy_security", "sell_security"]:
            result = check(action, {"amount": 50000})

            assert result["allowed"] is True
            assert "sms_otp" in result["required_confirmations"]

    def test_unknown_action_blocked(self):
        """Unknown actions should be blocked."""
        result = check("unknown_action", {})

        assert result["allowed"] is False
        assert "manual review" in result["reason"].lower()

    def test_response_structure(self):
        """Response should have required fields."""
        result = check("view_balance", {})

        assert "allowed" in result
        assert "required_confirmations" in result
        assert "reason" in result
        assert "risk_level" in result

    def test_timeout_error(self, monkeypatch):
        """Should raise TimeoutError occasionally."""
        monkeypatch.setattr("tools.compliance.random.random", lambda: 0.01)
        with pytest.raises(TimeoutError):
            check("view_balance", {})


# =============================================================================
# Support Tests: create_case(summary, evidence)
# =============================================================================


class TestCreateCase:
    """Tests for support.create_case()"""

    def test_creates_case_with_summary(self):
        """Should create a case with provided summary."""
        case = create_case("ลูกค้าต้องการความช่วยเหลือเรื่องธุรกรรม")

        assert "case_id" in case
        assert case["case_id"].startswith("CASE-")
        assert case["status"] == "open"
        assert case["summary"] == "ลูกค้าต้องการความช่วยเหลือเรื่องธุรกรรม"

    def test_case_response_structure(self):
        """Response should have required fields."""
        case = create_case("Test summary")

        assert "case_id" in case
        assert "status" in case
        assert "created_at" in case
        assert "summary" in case
        assert "evidence_count" in case
        assert "estimated_response" in case

    def test_with_evidence(self):
        """Should track evidence count when provided."""
        evidence = [
            {"type": "transaction", "data": {"id": "TXN-001"}, "timestamp": "2024-01-15"},
            {"type": "conversation", "data": "ลูกค้าพูดว่า...", "timestamp": "2024-01-15"},
        ]
        case = create_case("พบกิจกรรมที่น่าสงสัย", evidence=evidence)

        assert case["evidence_count"] == 2

    def test_without_evidence(self):
        """Should handle missing evidence."""
        case = create_case("คำขอทั่วไป")

        assert case["evidence_count"] == 0

    def test_empty_summary_raises_error(self):
        """Should raise ValueError for empty summary."""
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            create_case("")

    def test_whitespace_summary_raises_error(self):
        """Should raise ValueError for whitespace-only summary."""
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            create_case("   ")

    def test_timeout_error(self, monkeypatch):
        """Should raise TimeoutError occasionally."""
        monkeypatch.setattr("tools.support.random.random", lambda: 0.01)
        with pytest.raises(TimeoutError):
            create_case("Test case")


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests that verify tools work together."""

    def test_get_user_and_accounts(self):
        """Should be able to get user and their accounts."""
        user = get_user()
        accounts = list_accounts()

        assert user["user_id"] is not None
        assert len(accounts) > 0

    def test_account_to_transactions_flow(self):
        """Should get transactions for an account."""
        accounts = list_accounts()
        checking = next(a for a in accounts if a["account_type"] == "checking")

        transactions = search(checking["account_id"])
        assert len(transactions) > 0

    def test_investment_account_to_positions_flow(self):
        """Should get positions for investment account."""
        accounts = list_accounts()
        investment = next(a for a in accounts if a["account_type"] == "investment")

        positions = get_positions(investment["account_id"])
        assert positions["total_value"] == investment["balance"]

    def test_compliance_before_transfer(self):
        """Should check compliance before making a transfer."""
        accounts = list_accounts()
        checking = next(a for a in accounts if a["account_type"] == "checking")

        # Check compliance for a transfer of 50,000 THB
        result = check("transfer_funds", {
            "account_id": checking["account_id"],
            "amount": 50000,
            "destination": "บัญชีภายนอก"
        })

        assert result["allowed"] is True
        # Elderly user should require SMS OTP
        assert "sms_otp" in result["required_confirmations"]

    def test_risk_profile_matches_conservative_user(self):
        """Risk profile should reflect conservative elderly user."""
        user = get_user()
        risk = get_risk_profile()

        # Elderly user should have conservative risk profile
        assert user["age"] >= 60
        assert risk["risk_tolerance"] == "conservative"

    def test_escalate_suspicious_activity(self):
        """Should be able to create a support case for suspicious activity."""
        transactions = search("ACC-1001")

        # Simulate detecting duplicate transactions
        case = create_case(
            summary="พบธุรกรรมซ้ำซ้อนที่ต้องตรวจสอบ",
            evidence=[{"type": "transaction", "data": transactions[0], "timestamp": "2024-01-15"}]
        )

        assert case["status"] == "open"
        assert case["evidence_count"] == 1

    def test_total_cash_across_accounts(self):
        """Should be able to calculate total cash across accounts."""
        accounts = list_accounts()

        # Checking + Savings = liquid cash
        liquid_accounts = [a for a in accounts if a["account_type"] in ("checking", "savings")]
        total_cash = sum(a["balance"] for a in liquid_accounts)

        # Should be around 2M THB (435k + 1.58M)
        assert total_cash > 2000000
