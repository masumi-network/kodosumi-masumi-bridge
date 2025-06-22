import pytest
from masumi_kodosuni_connector.database.repositories import AgentRunRepository
from masumi_kodosuni_connector.models.agent_run import AgentRunStatus


@pytest.mark.asyncio
async def test_create_agent_run(test_db):
    repository = AgentRunRepository(test_db)
    
    agent_run = await repository.create(
        agent_key="test_agent",
        request_data={"prompt": "test prompt"},
        masumi_payment_id="payment_123"
    )
    
    assert agent_run.id is not None
    assert agent_run.agent_key == "test_agent"
    assert agent_run.status == AgentRunStatus.PENDING_PAYMENT
    assert agent_run.masumi_payment_id == "payment_123"
    assert agent_run.created_at is not None


@pytest.mark.asyncio 
async def test_get_by_id(test_db):
    repository = AgentRunRepository(test_db)
    
    created_run = await repository.create(
        agent_key="test_agent",
        request_data={"prompt": "test prompt"}
    )
    
    retrieved_run = await repository.get_by_id(created_run.id)
    assert retrieved_run is not None
    assert retrieved_run.id == created_run.id
    assert retrieved_run.agent_key == "test_agent"


@pytest.mark.asyncio
async def test_update_status(test_db):
    repository = AgentRunRepository(test_db)
    
    agent_run = await repository.create(
        agent_key="test_agent", 
        request_data={"prompt": "test prompt"}
    )
    
    success = await repository.update_status(
        agent_run.id,
        AgentRunStatus.RUNNING,
        kodosumi_job_id="job_123"
    )
    
    assert success is True
    
    updated_run = await repository.get_by_id(agent_run.id)
    assert updated_run.status == AgentRunStatus.RUNNING
    assert updated_run.kodosumi_job_id == "job_123"
    assert updated_run.started_at is not None