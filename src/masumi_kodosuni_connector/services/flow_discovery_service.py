import asyncio
import structlog
from typing import Dict, List, Any
from masumi_kodosuni_connector.clients.kodosumi_client import KodosumyClient

logger = structlog.get_logger()


class FlowDiscoveryService:
    def __init__(self):
        self.client = KodosumyClient()
        self._flows_cache: Dict[str, Dict[str, Any]] = {}
        self._last_refresh = 0
        self._cache_duration = 300  # 5 minutes
        self._refresh_lock = asyncio.Lock()
    
    async def get_available_flows(self) -> Dict[str, Dict[str, Any]]:
        """Get available flows from Kodosumi, with caching."""
        import time
        current_time = time.time()
        
        if current_time - self._last_refresh > self._cache_duration:
            # Use async lock to prevent concurrent cache refreshes
            async with self._refresh_lock:
                # Double-check the cache after acquiring the lock
                # Another request might have refreshed it while we were waiting
                if current_time - self._last_refresh > self._cache_duration:
                    await self._refresh_flows()
                    self._last_refresh = current_time
        
        return self._flows_cache
    
    async def get_flow_schema(self, flow_key: str) -> Dict[str, Any]:
        """Get the input schema for a specific flow."""
        flows = await self.get_available_flows()
        flow_info = flows.get(flow_key)
        
        if not flow_info:
            raise ValueError(f"Flow {flow_key} not found")
        
        return await self.client.get_flow_schema(flow_info["url"])
    
    async def _refresh_flows(self) -> None:
        """Refresh the flows cache from Kodosumi."""
        try:
            # Add timeout to prevent hanging
            flows = await asyncio.wait_for(
                self.client.get_available_flows(), 
                timeout=30.0
            )
            self._flows_cache = {}
            
            for flow in flows:
                # Create a flow key from the URL path
                flow_path = flow.get("url", "")
                if flow_path.startswith("/"):
                    flow_key = flow_path[1:].replace("/", "_")
                else:
                    flow_key = flow_path.replace("/", "_")
                
                # Skip empty keys
                if not flow_key:
                    continue
                
                self._flows_cache[flow_key] = {
                    "name": flow.get("summary", flow_key),
                    "description": flow.get("description", ""),
                    "url": flow_path,
                    "version": flow.get("version", "1.0.0"),
                    "author": flow.get("author", ""),
                    "tags": flow.get("tags", [])
                }
            
            logger.info("Refreshed flows cache", flow_count=len(self._flows_cache))
            
        except asyncio.TimeoutError:
            logger.error("Flow refresh timed out after 30 seconds")
            # Try to force reconnect on timeout
            try:
                await self.client.force_reconnect()
            except Exception as reconnect_error:
                logger.error("Failed to reconnect after timeout", error=str(reconnect_error))
        except Exception as e:
            logger.error("Failed to refresh flows", error=str(e))
            # Try to force reconnect on any error
            try:
                await self.client.force_reconnect()
            except Exception as reconnect_error:
                logger.error("Failed to reconnect after error", error=str(reconnect_error))
    
    def get_flow_key_from_path(self, path: str) -> str:
        """Convert a URL path to a flow key."""
        if path.startswith("/"):
            path = path[1:]
        return path.replace("/", "_")


# Global instance
flow_discovery = FlowDiscoveryService()