from typing import Any


def deduplicate_transactions(transactions: list[dict]) -> list[dict]:
    seen_ids: set[str] = set()
    unique: list[dict] = []

    for txn in transactions:
        txn_id = txn.get("transaction_id", "")
        if txn_id and txn_id not in seen_ids:
            seen_ids.add(txn_id)
            unique.append(txn)

    return unique


def format_thb(amount: float) -> str:
    if amount < 0:
        return f"-{abs(amount):,.2f} บาท"
    return f"{amount:,.2f} บาท"

def extract_evidence(
    transactions: list[dict] | None = None,
    accounts: list[dict] | None = None,
    portfolio: dict | None = None,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {}

    if transactions:
        evidence["transaction_ids"] = list({
            txn["transaction_id"] for txn in transactions
            if "transaction_id" in txn
        })
        evidence["transaction_count"] = len(transactions)

    if accounts:
        evidence["account_ids"] = [
            acc["account_id"] for acc in accounts
            if "account_id" in acc
        ]

    if portfolio:
        evidence["portfolio_account"] = portfolio.get("account_id")
        evidence["portfolio_last_updated"] = portfolio.get("last_updated")
        evidence["portfolio_is_stale"] = portfolio.get("is_stale", False)
        if portfolio.get("holdings"):
            evidence["holding_symbols"] = [
                h["symbol"] for h in portfolio["holdings"]
            ]

    return evidence
