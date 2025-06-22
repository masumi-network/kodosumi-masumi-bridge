import httpx
from typing import Dict, Any, Optional
from masumi_kodosuni_connector.config.settings import settings


class KodosumyJobStatus:
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"


class KodosumyClient:
    def __init__(self):
        self.base_url = settings.kodosumi_base_url.rstrip("/")
        self.api_key = settings.kodosumi_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def start_job(self, agent_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/agents/{agent_id}/jobs",
                json=job_data,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/jobs/{job_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/jobs/{job_id}/cancel",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_job_result(self, job_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/jobs/{job_id}/result",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()