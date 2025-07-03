"""Service for managing agent configurations in the database."""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from masumi_kodosuni_connector.models.agent_config import AgentConfig
from masumi_kodosuni_connector.config.logging import get_logger

logger = get_logger("agent_config")


class AgentConfigService:
    """Service for managing agent configurations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_agent_config(self, flow_key: str) -> Optional[AgentConfig]:
        """Get agent configuration by flow key."""
        result = await self.session.execute(
            select(AgentConfig).where(AgentConfig.flow_key == flow_key)
        )
        return result.scalar_one_or_none()
    
    async def get_all_agent_configs(self) -> List[AgentConfig]:
        """Get all agent configurations."""
        result = await self.session.execute(select(AgentConfig))
        return result.scalars().all()
    
    async def get_enabled_agents(self) -> Dict[str, str]:
        """Get all enabled agents as a dict of flow_key -> agent_identifier."""
        result = await self.session.execute(
            select(AgentConfig).where(AgentConfig.enabled == True)
        )
        configs = result.scalars().all()
        return {config.flow_key: config.agent_identifier for config in configs if config.agent_identifier}
    
    async def is_agent_enabled(self, flow_key: str) -> bool:
        """Check if an agent is enabled."""
        config = await self.get_agent_config(flow_key)
        return config is not None and config.enabled and config.agent_identifier is not None
    
    async def get_agent_identifier(self, flow_key: str) -> Optional[str]:
        """Get agent identifier for a flow key."""
        config = await self.get_agent_config(flow_key)
        if config and config.enabled:
            return config.agent_identifier
        return None
    
    async def set_agent_config(
        self, 
        flow_key: str, 
        agent_identifier: Optional[str] = None,
        enabled: bool = False,
        flow_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> AgentConfig:
        """Set or update agent configuration."""
        existing_config = await self.get_agent_config(flow_key)
        
        if existing_config:
            # Update existing configuration
            await self.session.execute(
                update(AgentConfig)
                .where(AgentConfig.flow_key == flow_key)
                .values(
                    agent_identifier=agent_identifier,
                    enabled=enabled,
                    flow_name=flow_name or existing_config.flow_name,
                    description=description or existing_config.description
                )
            )
            await self.session.commit()
            
            # Refetch the updated config
            updated_config = await self.get_agent_config(flow_key)
            logger.info(f"Updated agent config: {flow_key}, enabled={enabled}, identifier={agent_identifier}")
            return updated_config
        else:
            # Create new configuration
            new_config = AgentConfig(
                flow_key=flow_key,
                agent_identifier=agent_identifier,
                enabled=enabled,
                flow_name=flow_name,
                description=description
            )
            self.session.add(new_config)
            await self.session.commit()
            await self.session.refresh(new_config)
            
            logger.info(f"Created new agent config: {flow_key}, enabled={enabled}, identifier={agent_identifier}")
            return new_config
    
    async def enable_agent(self, flow_key: str, agent_identifier: str, flow_name: Optional[str] = None, description: Optional[str] = None) -> AgentConfig:
        """Enable an agent with the given identifier."""
        return await self.set_agent_config(
            flow_key=flow_key,
            agent_identifier=agent_identifier,
            enabled=True,
            flow_name=flow_name,
            description=description
        )
    
    async def disable_agent(self, flow_key: str) -> AgentConfig:
        """Disable an agent."""
        config = await self.get_agent_config(flow_key)
        if config:
            return await self.set_agent_config(
                flow_key=flow_key,
                agent_identifier=config.agent_identifier,  # Keep the identifier
                enabled=False,
                flow_name=config.flow_name,
                description=config.description
            )
        else:
            # Create disabled config
            return await self.set_agent_config(
                flow_key=flow_key,
                enabled=False
            )
    
    async def delete_agent_config(self, flow_key: str) -> bool:
        """Delete agent configuration."""
        result = await self.session.execute(
            delete(AgentConfig).where(AgentConfig.flow_key == flow_key)
        )
        await self.session.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted agent config: {flow_key}")
        return deleted
    
    async def sync_with_discovered_flows(self, discovered_flows: Dict[str, Dict]) -> None:
        """Sync agent configs with discovered flows, updating flow names and descriptions."""
        if not discovered_flows:
            return
            
        # Batch fetch all existing configs in one query
        flow_keys = list(discovered_flows.keys())
        result = await self.session.execute(
            select(AgentConfig).where(AgentConfig.flow_key.in_(flow_keys))
        )
        existing_configs = {config.flow_key: config for config in result.scalars().all()}
        
        # Prepare updates and inserts
        updates_to_make = []
        new_configs_to_add = []
        
        for flow_key, flow_info in discovered_flows.items():
            existing_config = existing_configs.get(flow_key)
            flow_name = flow_info.get("name")
            description = flow_info.get("description")
            
            if existing_config:
                # Check if update is needed
                if (existing_config.flow_name != flow_name or 
                    existing_config.description != description):
                    updates_to_make.append({
                        'flow_key': flow_key,
                        'flow_name': flow_name,
                        'description': description
                    })
            else:
                # Create new disabled config for newly discovered flows
                new_configs_to_add.append(AgentConfig(
                    flow_key=flow_key,
                    enabled=False,
                    flow_name=flow_name,
                    description=description
                ))
        
        # Perform bulk updates
        if updates_to_make:
            for update_data in updates_to_make:
                await self.session.execute(
                    update(AgentConfig)
                    .where(AgentConfig.flow_key == update_data['flow_key'])
                    .values(
                        flow_name=update_data['flow_name'],
                        description=update_data['description']
                    )
                )
        
        # Perform bulk inserts
        if new_configs_to_add:
            self.session.add_all(new_configs_to_add)
        
        await self.session.commit()
        logger.info(f"Synced agent configs with {len(discovered_flows)} discovered flows - {len(updates_to_make)} updates, {len(new_configs_to_add)} new configs")