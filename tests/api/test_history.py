"""История операций. Требование REQ-HIST-01, тест-кейсы TC-041, TC-042."""
import pytest


def test_history_order_and_direction(make_user):
    """TC-041: новые сверху; direction out / in / self; чужих операций нет"""
    alice = make_user(rub="10000", usd="0")
    bob = make_user(rub="10000")
    out_tx = alice.client.transfer(alice.rub, bob.rub, "100").json()["id"]
    in_tx = bob.client.transfer(bob.rub, alice.rub, "50").json()["id"]
    self_tx = alice.client.transfer(alice.rub, alice.usd, "1000").json()["id"]

    history = alice.client.get("/transactions").json()
    assert [t["id"] for t in history[:3]] == [self_tx, in_tx, out_tx]
    assert [t["direction"] for t in history[:3]] == ["self", "in", "out"]
    assert history[-1]["type"] == "topup"
    my_accounts = {alice.rub, alice.usd}
    assert all(t["from_account_id"] in my_accounts or t["to_account_id"] in my_accounts for t in history)


def test_history_pagination(make_user, recipient):
    """TC-042: limit/offset без пересечений"""
    user = make_user(rub="10000")
    for _ in range(4):
        user.client.transfer(user.rub, recipient.rub, "10")
    page1 = user.client.get("/transactions", params={"limit": 2, "offset": 0}).json()
    page2 = user.client.get("/transactions", params={"limit": 2, "offset": 2}).json()
    assert len(page1) == 2 and len(page2) == 2
    assert not {t["id"] for t in page1} & {t["id"] for t in page2}


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_history_invalid_pagination(user, params):
    """TC-042"""
    assert user.client.get("/transactions", params=params).status_code == 422
