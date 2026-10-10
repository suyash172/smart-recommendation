"""In-memory state of the mock bank. Pure Python (no web framework) so it is easy to test.

Every entry is either {"data": {...}} (normal response) or {"fault": {...}} (simulated failure).
Lookups are EXACT-match on purpose: an IBAN with spaces must not match the clean IBAN
(scenario E3C relies on this).
"""
import copy
from typing import Any

DEFAULT_BANK: dict[str, Any] = {"bank_status": "ONLINE", "estimated_recovery": None}
DEFAULT_ACCOUNT: dict[str, Any] = {
    "exists": True,
    "status": "ACTIVE",
    "account_name": "Default Account Holder",
    "currency": "USD",
    "account_type": "CHECKING",
}
DEFAULT_BALANCE: dict[str, Any] = {"current": 10000.0, "available": 9500.0}


class MockBankState:
    def __init__(self, seed: dict[str, Any] | None = None):
        self._seed = seed or {"banks": {}, "accounts": {}, "balances": {}}
        self.banks: dict[str, Any] = {}
        self.accounts: dict[str, Any] = {}
        self.balances: dict[str, Any] = {}
        self.forced_status_code: int | None = None
        self.calls: list[dict[str, str]] = []
        self.reset()

    def reset(self) -> None:
        """Back to the organisers' seed data."""
        self.banks = copy.deepcopy(self._seed.get("banks", {}))
        self.accounts = copy.deepcopy(self._seed.get("accounts", {}))
        self.balances = copy.deepcopy(self._seed.get("balances", {}))
        self.forced_status_code = None
        self.calls = []

    def clear(self) -> None:
        """Empty store: everything falls back to defaults."""
        self.banks, self.accounts, self.balances = {}, {}, {}
        self.forced_status_code = None
        self.calls = []

    def apply_scenario(self, scenario: dict[str, Any], replace: bool = True) -> None:
        """Apply a scenario file's `mock_bank_state` block."""
        if replace:
            self.clear()
        for bic, d in (scenario.get("bank_status") or {}).items():
            self.banks[bic] = {"data": copy.deepcopy(d)}
        for number, d in (scenario.get("accounts") or {}).items():
            self.accounts[number] = {"data": copy.deepcopy(d)}
        for number, d in (scenario.get("balances") or {}).items():
            self.balances[number] = {"data": copy.deepcopy(d)}
        fault = scenario.get("fault_injection") or {}
        self.forced_status_code = fault.get("forced_status_code")

    # ---- lookups (exact match, defaults when unknown) ----
    def lookup_bank(self, bic: str) -> dict[str, Any]:
        return self.banks.get(bic) or {"data": copy.deepcopy(DEFAULT_BANK)}

    def lookup_account(self, account_number: str) -> dict[str, Any]:
        return self.accounts.get(account_number) or {"data": copy.deepcopy(DEFAULT_ACCOUNT)}

    def lookup_balance(self, account_number: str) -> dict[str, Any]:
        return self.balances.get(account_number) or {"data": copy.deepcopy(DEFAULT_BALANCE)}

    def record_call(self, endpoint: str, key: str) -> None:
        self.calls.append({"endpoint": endpoint, "key": key})

    def snapshot(self) -> dict[str, Any]:
        return {
            "banks": self.banks,
            "accounts": self.accounts,
            "balances": self.balances,
            "forced_status_code": self.forced_status_code,
        }