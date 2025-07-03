"""Global agent configuration manager for database-backed agent settings."""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.services.agent_config_service import AgentConfigService
from masumi_kodosuni_connector.database.connection import get_db
from masumi_kodosuni_connector.config.logging import get_logger

logger = get_logger("agent_config_manager")


class AgentConfigManager:
    """Global manager for agent configuration that can be used synchronously across the app."""
    
    def __init__(self):
        self._cached_configs: Dict[str, Dict] = {}
        self._cache_valid = False
    
    async def _get_service(self):
        """Get an agent config service with a new database session."""
        # Create a new session for each operation
        async for db in get_db():
            yield AgentConfigService(db)
            break
    
    async def refresh_cache(self) -> None:
        """Refresh the cached agent configurations from database."""
        try:
            async for service in self._get_service():
                configs = await service.get_all_agent_configs()
                break
            
            self._cached_configs = {}
            for config in configs:
                self._cached_configs[config.flow_key] = {
                    'agent_identifier': config.agent_identifier,
                    'enabled': config.enabled,
                    'flow_name': config.flow_name,
                    'description': config.description
                }
            
            self._cache_valid = True
            logger.info(f"Refreshed agent config cache with {len(self._cached_configs)} configurations")
            
        except Exception as e:
            logger.error(f"Failed to refresh agent config cache: {e}")
            self._cache_valid = False
    
    def _ensure_cache_valid(self) -> None:
        """Ensure cache is valid, log warning if not."""
        if not self._cache_valid:
            logger.warning("Agent config cache is invalid. Some operations may not work correctly.")
    
    def is_agent_enabled(self, flow_key: str) -> bool:
        """Check if an agent is enabled (synchronous)."""
        self._ensure_cache_valid()
        config = self._cached_configs.get(flow_key, {})
        return config.get('enabled', False) and config.get('agent_identifier') is not None
    
    def get_agent_identifier(self, flow_key: str) -> Optional[str]:
        """Get agent identifier (synchronous)."""
        self._ensure_cache_valid()
        config = self._cached_configs.get(flow_key, {})
        if config.get('enabled', False):
            return config.get('agent_identifier')
        return None
    
    def get_configured_agents(self) -> Dict[str, str]:
        """Get all enabled agent identifiers (synchronous)."""
        self._ensure_cache_valid()
        enabled_agents = {}
        for flow_key, config in self._cached_configs.items():
            if config.get('enabled', False) and config.get('agent_identifier'):
                enabled_agents[flow_key] = config['agent_identifier']
        return enabled_agents
    
    def get_all_configs(self) -> Dict[str, Dict]:
        """Get all cached configurations (synchronous)."""
        self._ensure_cache_valid()
        return self._cached_configs.copy()
    
    async def enable_agent(self, flow_key: str, agent_identifier: str, flow_name: Optional[str] = None, description: Optional[str] = None) -> bool:
        """Enable an agent (async)."""
        try:
            async for service in self._get_service():
                await service.enable_agent(flow_key, agent_identifier, flow_name, description)
                break
            await self.refresh_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to enable agent {flow_key}: {e}")
            return False
    
    async def disable_agent(self, flow_key: str) -> bool:
        """Disable an agent (async)."""
        try:
            async for service in self._get_service():
                await service.disable_agent(flow_key)
                break
            await self.refresh_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to disable agent {flow_key}: {e}")
            return False
    
    async def sync_with_flows(self, discovered_flows: Dict[str, Dict]) -> None:
        """Sync with discovered flows and refresh cache."""
        try:
            async for service in self._get_service():
                await service.sync_with_discovered_flows(discovered_flows)
                break
            await self.refresh_cache()
        except Exception as e:
            logger.error(f"Failed to sync with discovered flows: {e}")


# Global instance
agent_config_manager = AgentConfigManager()