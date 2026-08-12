from abc import ABC, abstractmethod

class Broker(ABC):
    @abstractmethod
    def place_order(self, symbol, side, quantity, order_type="MARKET", price=0.0):
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id):
        raise NotImplementedError

    @abstractmethod
    def health_check(self):
        raise NotImplementedError

class PaperBroker(Broker):
    def __init__(self):
        self.orders = []
        self.counter = 0

    def place_order(self, symbol, side, quantity, order_type="MARKET", price=0.0):
        self.counter += 1
        order = {
            "order_id": f"PAPER-{self.counter}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "type": order_type,
            "price": price,
            "status": "PAPER_ACCEPTED",
        }
        self.orders.append(order)
        return order

    def cancel_order(self, order_id):
        for order in self.orders:
            if order["order_id"] == order_id:
                order["status"] = "CANCELLED"
                return order
        return None

    def health_check(self):
        return True
