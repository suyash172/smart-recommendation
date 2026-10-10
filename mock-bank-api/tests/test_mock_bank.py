import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def fast_faults(monkeypatch):
    monkeypatch.setenv("MOCK_DELAY_SCALE", "0")  # skip the real 15 s timeout delay


@pytest.fixture()
def client():
    return TestClient(create_app())


def acct(client, number):
    return client.get("/api/accounts", params={"account-number": number})


def bal(client, number):
    return client.get("/api/accounts-balance", params={"account-number": number})


def bank(client, bic):
    return client.get("/api/bank-status", params={"bic-code": bic})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ---------- normal data ----------
def test_bank_online(client):
    body = bank(client, "DEUTDEFF").json()
    assert body["bank_status"] == "ONLINE" and body["estimated_recovery"] is None
    assert body["bic_code"] == "DEUTDEFF"


def test_bank_down_has_recovery_time(client):
    body = bank(client, "BARCGB22").json()
    assert body["bank_status"] == "DOWN"
    assert body["estimated_recovery"] == "2026-09-29T06:00:00Z"


def test_unknown_bank_defaults_to_online(client):
    assert bank(client, "ZZZZZZ99").json()["bank_status"] == "ONLINE"


def test_seed_account_returns_name_and_echoes_number(client):
    body = acct(client, "DE89370400440532013000").json()
    assert body["status"] == "ACTIVE" and body["account_name"] == "Acme GmbH"
    assert body["account_number"] == "DE89370400440532013000"


def test_iban_with_spaces_is_not_found(client):
    body = acct(client, "DE89 3704 0044 0532 0130 00").json()
    assert body["exists"] is False and body["status"] == "NOT_FOUND"


def test_unknown_account_defaults_to_active(client):
    body = acct(client, "SOMETHING-NOT-IN-SEED").json()
    assert body["exists"] is True and body["status"] == "ACTIVE"


def test_frozen_account_and_balance(client):
    assert acct(client, "IN400111001234567890").json()["status"] == "FROZEN"
    assert bal(client, "US12345678901234567890").json() == {"current": 500.0, "available": 200.0}


# ---------- faults from the seed ----------
@pytest.mark.parametrize("bic,code", [("BKBRBRLJ", 503), ("NABAAU3X", 500), ("CITIHKAX", 504)])
def test_bank_faults(client, bic, code):
    assert bank(client, bic).status_code == code


@pytest.mark.parametrize("number,code", [("IN001111111111111111111", 500), ("JP002222222222222222222", 504)])
def test_balance_faults(client, number, code):
    assert bal(client, number).status_code == code


def test_account_http_and_timeout_faults(client):
    assert acct(client, "FR0089012345678901234567890").status_code == 503
    assert acct(client, "DE00789012345678901234").status_code == 504


def test_malformed_json_fault(client):
    r = acct(client, "GB00901234567890123456")
    assert r.status_code == 200
    with pytest.raises(ValueError):
        r.json()


def test_invalid_data_fault_returns_negative_balance(client):
    assert bal(client, "DE00333333333333333333").json() == {"current": -500.0, "available": -200.0}


# ---------- admin helpers ----------
def test_seed_overrides_account_and_clears_the_rest(client):
    payload = {
        "accounts": {
            "DE89370400440532013000": {
                "exists": True, "status": "ACTIVE",
                "account_name": "Al-Amal Trading Co.", "currency": "USD",
            }
        },
        "fault_injection": None,
    }
    assert client.post("/admin/seed", json=payload).status_code == 200
    assert acct(client, "DE89370400440532013000").json()["account_name"] == "Al-Amal Trading Co."
    # replace=True cleared the organiser seed, so HDFCINBB is back to the ONLINE default
    assert bank(client, "HDFCINBB").json()["bank_status"] == "ONLINE"


@pytest.mark.parametrize("call", [
    lambda c: bank(c, "DEUTDEFF"),
    lambda c: acct(c, "DE89370400440532013000"),
    lambda c: bal(c, "DE89370400440532013000"),
])
def test_forced_status_code_applies_to_all_endpoints(client, call):
    client.post("/admin/seed", json={"fault_injection": {"forced_status_code": 503}})
    assert call(client).status_code == 503


def test_reset_restores_seed(client):
    client.post("/admin/seed", json={"fault_injection": {"forced_status_code": 503}})
    client.post("/admin/reset")
    assert bank(client, "DEUTDEFF").status_code == 200
    assert acct(client, "DE89370400440532013000").json()["account_name"] == "Acme GmbH"


def test_calls_log_records_and_clears_on_seed(client):
    bank(client, "DEUTDEFF")
    acct(client, "DE89370400440532013000")
    calls = client.get("/admin/calls").json()
    assert [c["endpoint"] for c in calls] == ["/api/bank-status", "/api/accounts"]
    client.post("/admin/seed", json={})
    assert client.get("/admin/calls").json() == []


def test_invalid_forced_status_rejected(client):
    assert client.post("/admin/seed", json={"fault_injection": {"forced_status_code": 200}}).status_code == 422