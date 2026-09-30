# app/integrations/payment_gateway.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePaymentGateway(ABC):
    """Abstract base class for payment gateways. Never change business logic when switching banks."""
    
    @abstractmethod
    def generate_payment_url(self, amount: float, order_id: int, callback_url: str) -> Dict[str, Any]:
        """Returns a URL to redirect the user to the payment provider."""
        pass

    @abstractmethod
    def verify_payment(self, transaction_id: str, amount: float) -> bool:
        """Verifies with the provider that the payment was actually successful."""
        pass

class MockPaymentGateway(BasePaymentGateway):
    """Mock gateway for development. Will be replaced with Zarinpal/IDPay/etc. later."""
    
    def generate_payment_url(self, amount: float, order_id: int, callback_url: str) -> Dict[str, Any]:
        # In a real gateway, this calls the bank's API. 
        # Here, we just simulate a transaction ID.
        mock_transaction_id = f"MOCK_TXN_{order_id}_{int(amount)}"
        return {
            "payment_url": f"http://localhost:8000/payments/mock-success?tx={mock_transaction_id}",
            "transaction_id": mock_transaction_id
        }

    def verify_payment(self, transaction_id: str, amount: float) -> bool:
        # In a real gateway, this checks the bank's database.
        # Here, we just say it's always successful if it starts with MOCK_TXN.
        return transaction_id.startswith("MOCK_TXN")

# Singleton instance to use across the app
payment_gateway = MockPaymentGateway()