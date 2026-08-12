"""
Broker adapter for DhanHQ v2, verified against the `dhanhq` SDK's own
source for endpoint/payload shape. Dhan identifies instruments by a numeric
`security_id`, not a ticker string, so the caller must supply a
symbol -> security_id map up front (see fundamentals for a similar
manually-curated mapping pattern in sector_strength.SECTOR_INDEX). Getting
that mapping wrong would silently route orders to the wrong instrument, so
this deliberately does not attempt to auto-resolve or guess it.
"""
from data.dhan_data import get_dhan_client
from execution.broker import Broker

class DhanBroker(Broker):
    def __init__(self, client_id, access_token, symbol_to_security_id: dict,
                 exchange_segment="NSE_EQ", product_type="INTRADAY"):
        self.client = get_dhan_client(client_id, access_token)
        self.symbol_to_security_id = symbol_to_security_id
        self.exchange_segment = exchange_segment
        self.product_type = product_type

    def _security_id(self, symbol):
        security_id = self.symbol_to_security_id.get(symbol)
        if security_id is None:
            raise ValueError(
                f"No Dhan security_id configured for '{symbol}'. Add it to the "
                f"symbol_to_security_id map passed to DhanBroker before trading it."
            )
        return security_id

    def place_order(self, symbol, side, quantity, order_type="MARKET", price=0.0):
        security_id = self._security_id(symbol)
        transaction_type = "BUY" if side == "LONG" else "SELL"

        response = self.client.place_order(
            security_id=security_id,
            exchange_segment=self.exchange_segment,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product_type=self.product_type,
            price=price,
        )

        if response.get("status") != "success":
            raise RuntimeError(f"Dhan order placement failed: {response.get('remarks')}")

        return response["data"]

    def cancel_order(self, order_id):
        response = self.client.cancel_order(order_id)
        if response.get("status") != "success":
            return None
        return response["data"]

    def health_check(self):
        try:
            response = self.client.get_order_list()
            return response.get("status") == "success"
        except Exception:
            return False
