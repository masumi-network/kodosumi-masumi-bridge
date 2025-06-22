import httpx
from typing import Dict, Any, Optional
from masumi_kodosuni_connector.config.settings import settings


class MasumiPaymentStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


class MasumiClient:
    def __init__(self):
        self.base_url = settings.masumi_node_url.rstrip("/")
        self.api_key = settings.masumi_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def create_payment_request(self, amount: float, currency: str = "USD", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payment_data = {
            "amount": amount,
            "currency": currency,
            "metadata": metadata or {}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/payments",
                json=payment_data,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def verify_payment(self, payment_id: str) -> bool:
        payment_data = await self.get_payment_status(payment_id)
        return payment_data.get("status") == MasumiPaymentStatus.CONFIRMED