import pytest
from masumi_kodosuni_connector.database.repositories import FlowRunRepository
from masumi_kodosuni_connector.models.agent_run import FlowRunStatus


@pytest.mark.asyncio
async def test_create_flow_run(test_db):
    repository = FlowRunRepository(test_db)
    
    flow_run = await repository.create(
        flow_path="/test/flow",
        flow_name="Test Flow",
        inputs={"prompt": "test prompt"},
        masumi_payment_id="payment_123"
    )
    
    assert flow_run.id is not None
    assert flow_run.flow_path == "/test/flow"
    assert flow_run.flow_name == "Test Flow"
    assert flow_run.status == FlowRunStatus.PENDING_PAYMENT
    assert flow_run.masumi_payment_id == "payment_123"
    assert flow_run.created_at is not None


@pytest.mark.asyncio 
async def test_get_by_id(test_db):
    repository = FlowRunRepository(test_db)
    
    created_run = await repository.create(
        flow_path="/test/flow",
        flow_name="Test Flow",
        inputs={"prompt": "test prompt"}
    )
    
    retrieved_run = await repository.get_by_id(created_run.id)
    assert retrieved_run is not None
    assert retrieved_run.id == created_run.id
    assert retrieved_run.flow_path == "/test/flow"


@pytest.mark.asyncio
async def test_update_status(test_db):
    repository = FlowRunRepository(test_db)
    
    flow_run = await repository.create(
        flow_path="/test/flow",
        flow_name="Test Flow",
        inputs={"prompt": "test prompt"}
    )
    
    success = await repository.update_status(
        flow_run.id,
        FlowRunStatus.RUNNING,
        kodosumi_run_id="run_123"
    )
    
    assert success is True
    
    updated_run = await repository.get_by_id(flow_run.id)
    assert updated_run.status == FlowRunStatus.RUNNING
    assert updated_run.kodosumi_run_id == "run_123"
    assert updated_run.started_at is not None