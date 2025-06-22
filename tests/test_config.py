import pytest
import json
from masumi_kodosuni_connector.config.settings import Settings, AgentConfig


def test_agent_config_creation():
    config = AgentConfig("Test Agent", "test_agent_id")
    assert config.name == "Test Agent"
    assert config.kodosumi_agent_id == "test_agent_id"


def test_settings_agents_config_parsing():
    agents_config_json = json.dumps({
        "agent1": {"name": "Agent One", "kodosumi_agent_id": "agent_1_id"},
        "agent2": {"name": "Agent Two", "kodosumi_agent_id": "agent_2_id"}
    })
    
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        kodosumi_base_url="https://api.kodosumi.test",
        kodosumi_api_key="test_kodosumi_key",
        masumi_node_url="https://masumi.test",
        masumi_api_key="test_masumi_key",
        agents_config_raw=agents_config_json
    )
    
    agents_config = settings.agents_config
    assert len(agents_config) == 2
    assert "agent1" in agents_config
    assert "agent2" in agents_config
    assert agents_config["agent1"].name == "Agent One"
    assert agents_config["agent2"].kodosumi_agent_id == "agent_2_id"


def test_invalid_agents_config():
    with pytest.raises(ValueError, match="Invalid JSON"):
        Settings(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            kodosumi_base_url="https://api.kodosumi.test", 
            kodosumi_api_key="test_kodosumi_key",
            masumi_node_url="https://masumi.test",
            masumi_api_key="test_masumi_key",
            agents_config_raw="invalid json"
        )