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
        
        # Initialize with fallback flows to ensure the system works even when Kodosumi is down
        self._fallback_flows = {
            "-_127.0.0.1_8001_page_analysis_-_": {
                "name": "Page Content Analysis",
                "description": "Answer questions about the content and design of a single website URL",
                "url": "/-/127.0.0.1/8001/page_analysis/-/",
                "version": "1.0.0",
                "author": "system",
                "tags": ["Content", "Website", "Design"]
            }
        }
    
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
                    try:
                        await asyncio.wait_for(self._refresh_flows(), timeout=60.0)  # Increased to account for rate limiting
                        self._last_refresh = current_time
                    except asyncio.TimeoutError:
                        logger.warning("Flow refresh timed out, using existing cache")
                        # Update last_refresh to prevent immediate retry for longer
                        self._last_refresh = current_time - 60  # Only retry after 4 minutes
                    except Exception as e:
                        logger.error("Flow refresh failed, using existing cache", error=str(e))
                        # Update last_refresh to prevent immediate retry for longer
                        self._last_refresh = current_time - 60  # Only retry after 4 minutes
        
        # If cache is still empty (e.g., first startup or persistent failures), use fallback flows
        if not self._flows_cache:
            logger.warning("Using fallback flows due to empty cache")
            return self._fallback_flows
        
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
            # Add timeout to prevent hanging (increased to account for rate limiting)
            flows = await asyncio.wait_for(
                self.client.get_available_flows(), 
                timeout=45.0  # Increased timeout to account for rate limiting delays
            )
            self._flows_cache = {}
            
            for flow in flows:
                # Ensure flow is a dictionary
                if not isinstance(flow, dict):
                    logger.warning("Skipping non-dict flow", flow_type=type(flow).__name__, flow_data=str(flow))
                    continue
                
                # Create a flow key from the URL path
                flow_path = flow.get("url", "")
                if flow_path.startswith("/"):
                    flow_key = flow_path[1:].replace("/", "_")
                else:
                    flow_key = flow_path.replace("/", "_")
                
                # Skip empty keys
                if not flow_key:
                    logger.warning("Skipping flow with empty key", flow_data=str(flow)[:200])
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
            logger.warning("Flow refresh timed out after 45 seconds, keeping existing cache")
            # Don't try to reconnect immediately to avoid cascading failures
            # Just keep the existing cache
        except Exception as e:
            logger.error("Failed to refresh flows", error=str(e))
            # Keep existing cache on error
            # Don't force reconnect on every error - this causes too many re-auths
    
    def get_flow_key_from_path(self, path: str) -> str:
        """Convert a URL path to a flow key."""
        if path.startswith("/"):
            path = path[1:]
        return path.replace("/", "_")


# Global instance
flow_discovery = FlowDiscoveryService()