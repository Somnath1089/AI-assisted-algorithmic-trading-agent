import pytest

from execution.dhan_broker import DhanBroker

class _FakeDhanClient:
    def __init__(self, place_order_response=None, cancel_response=None, order_list_response=None):
        self.place_order_response = place_order_response
        self.cancel_response = cancel_response
        self.order_list_response = order_list_response
        self.last_place_order_kwargs = None

    def place_order(self, **kwargs):
        self.last_place_order_kwargs = kwargs
        return self.place_order_response

    def cancel_order(self, order_id):
        return self.cancel_response

    def get_order_list(self):
        return self.order_list_response

def _broker(monkeypatch, client):
    monkeypatch.setattr(
        "execution.dhan_broker.get_dhan_client",
        lambda client_id, access_token: client
    )
    return DhanBroker("cid", "token", symbol_to_security_id={"RELIANCE.NS": "2885"})

def test_place_order_maps_long_to_buy(monkeypatch):
    client = _FakeDhanClient(place_order_response={"status": "success", "data": {"orderId": "abc123"}})
    broker = _broker(monkeypatch, client)

    order = broker.place_order("RELIANCE.NS", "LONG", 10, price=2800.0)

    assert order == {"orderId": "abc123"}
    assert client.last_place_order_kwargs["transaction_type"] == "BUY"
    assert client.last_place_order_kwargs["security_id"] == "2885"
    assert client.last_place_order_kwargs["quantity"] == 10

def test_place_order_maps_short_to_sell(monkeypatch):
    client = _FakeDhanClient(place_order_response={"status": "success", "data": {"orderId": "xyz"}})
    broker = _broker(monkeypatch, client)

    broker.place_order("RELIANCE.NS", "SHORT", 5, price=2800.0)

    assert client.last_place_order_kwargs["transaction_type"] == "SELL"

def test_place_order_unmapped_symbol_raises(monkeypatch):
    client = _FakeDhanClient()
    broker = _broker(monkeypatch, client)

    with pytest.raises(ValueError, match="No Dhan security_id configured"):
        broker.place_order("UNKNOWN.NS", "LONG", 10, price=100.0)

def test_place_order_failure_raises(monkeypatch):
    client = _FakeDhanClient(place_order_response={"status": "failure", "remarks": "insufficient funds"})
    broker = _broker(monkeypatch, client)

    with pytest.raises(RuntimeError, match="Dhan order placement failed"):
        broker.place_order("RELIANCE.NS", "LONG", 10, price=2800.0)

def test_health_check_reflects_status(monkeypatch):
    client = _FakeDhanClient(order_list_response={"status": "success", "data": []})
    broker = _broker(monkeypatch, client)
    assert broker.health_check() is True

    client.order_list_response = {"status": "failure", "remarks": "bad token"}
    assert broker.health_check() is False
