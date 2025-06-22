import httpx
from typing import Dict, Any, Optional, List
from masumi_kodosuni_connector.config.settings import settings


class KodosumyFlowStatus:
    STARTING = "starting"
    RUNNING = "running" 
    FINISHED = "finished"
    ERROR = "error"


class KodosumyClient:
    def __init__(self):
        self.base_url = settings.kodosumi_base_url.rstrip("/")
        self.username = settings.kodosumi_username
        self.password = settings.kodosumi_password
        self._cookies: Optional[httpx.Cookies] = None
    
    async def authenticate(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/login",
                data={"name": self.username, "password": self.password},
                timeout=30.0
            )
            response.raise_for_status()
            self._cookies = response.cookies
    
    async def _ensure_authenticated(self) -> httpx.Cookies:
        if self._cookies is None:
            await self.authenticate()
        return self._cookies
    
    async def get_available_flows(self) -> List[Dict[str, Any]]:
        cookies = await self._ensure_authenticated()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/flow",
                cookies=cookies,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
    
    async def get_flow_schema(self, flow_path: str) -> Dict[str, Any]:
        cookies = await self._ensure_authenticated()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{flow_path}",
                cookies=cookies,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def launch_flow(self, flow_path: str, inputs: Dict[str, Any]) -> str:
        cookies = await self._ensure_authenticated()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{flow_path}",
                data=inputs,
                cookies=cookies,
                timeout=30.0
            )
            response.raise_for_status()
            
            # Extract the run_id from the response headers or body
            # The actual response structure may vary, adjust as needed
            if "location" in response.headers:
                # Extract run_id from redirect location
                location = response.headers["location"]
                run_id = location.split("/")[-1]
                return run_id
            else:
                # If response contains run_id directly
                data = response.json()
                return data.get("run_id")
    
    async def get_flow_status(self, run_id: str) -> Dict[str, Any]:
        cookies = await self._ensure_authenticated()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/run/{run_id}/status",
                cookies=cookies,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_flow_events(self, run_id: str) -> List[Dict[str, Any]]:
        cookies = await self._ensure_authenticated()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/run/{run_id}/events",
                cookies=cookies,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("events", [])
    
    async def get_flow_result(self, run_id: str) -> Dict[str, Any]:
        events = await self.get_flow_events(run_id)
        
        # Find the final result event
        for event in reversed(events):
            if event.get("event") == "final":
                return event.get("data", {})
        
        return {}