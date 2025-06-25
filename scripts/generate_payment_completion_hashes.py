#!/usr/bin/env python3
"""
Script to generate payment completion hashes for finished jobs.
This script extracts all finished jobs from the database and generates
the hashes that would be submitted to masumi for payment completion.
"""

import asyncio
import sys
import os
import json
from typing import List, Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env from the project root
project_root = os.path.join(os.path.dirname(__file__), '..')
env_file = os.path.join(project_root, '.env')

# Try multiple possible .env locations
possible_env_files = [
    env_file,
    '/root/kodosumi-masumi-bridge/.env',
    os.path.join(os.getcwd(), '.env'),
    '.env'
]

env_loaded = False
for env_path in possible_env_files:
    if os.path.exists(env_path):
        print(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
        env_loaded = True
        break

if not env_loaded:
    print("ERROR: Could not find .env file in any of these locations:")
    for env_path in possible_env_files:
        print(f"  - {env_path}")
    print("\nPlease run this script from the project root directory where .env is located")
    sys.exit(1)

# Debug: Show some environment variables
print(f"DATABASE_URL set: {'DATABASE_URL' in os.environ}")
print(f"KODOSUMI_BASE_URL set: {'KODOSUMI_BASE_URL' in os.environ}")

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(project_root, 'src'))

from masumi_kodosuni_connector.database.connection import AsyncSessionLocal
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus
from sqlalchemy import select


def create_masumi_output_hash(job_output: str, identifier_from_purchaser: str) -> str:
    """
    Replicate the masumi package's hash creation logic.
    This should match the hash creation in the masumi pip package.
    """
    import hashlib
    
    # Combine job output and identifier
    combined_data = f"{job_output}{identifier_from_purchaser}"
    
    # Create SHA-256 hash
    hash_object = hashlib.sha256(combined_data.encode('utf-8'))
    return hash_object.hexdigest()


async def get_finished_jobs() -> List[FlowRun]:
    """Get all finished jobs from the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FlowRun).where(FlowRun.status == FlowRunStatus.FINISHED)
        )
        return result.scalars().all()


def extract_result_output(result_data: Dict[str, Any]) -> str:
    """Extract the actual output from result data."""
    if not result_data:
        return ""
    
    # Try to get output field first
    if "output" in result_data:
        return str(result_data["output"])
    
    # Fallback to entire result_data as string
    return str(result_data)


async def main():
    """Main function to generate payment completion data."""
    print("Fetching all finished jobs from database...")
    
    finished_jobs = await get_finished_jobs()
    
    if not finished_jobs:
        print("No finished jobs found in database.")
        return
    
    print(f"Found {len(finished_jobs)} finished jobs.")
    print("\nGenerating payment completion data...\n")
    
    completion_data = []
    
    for job in finished_jobs:
        # Extract job output
        job_output = extract_result_output(job.result_data)
        
        # Get identifier from purchaser (might be in payment_response)
        identifier_from_purchaser = ""
        blockchain_identifier = ""
        
        if job.payment_response:
            if isinstance(job.payment_response, dict):
                payment_data = job.payment_response.get('data', {})
                identifier_from_purchaser = payment_data.get('identifierFromPurchaser', '')
                blockchain_identifier = payment_data.get('blockchainIdentifier', '')
            
        # Fallback to masumi_payment_id if no blockchain_identifier
        if not blockchain_identifier:
            blockchain_identifier = job.masumi_payment_id or ""
        
        # Create the hash that would be submitted to masumi
        if job_output and identifier_from_purchaser:
            submit_result_hash = create_masumi_output_hash(job_output, identifier_from_purchaser)
        else:
            submit_result_hash = "MISSING_DATA"
        
        job_data = {
            "job_id": str(job.id),
            "flow_path": job.flow_path,
            "flow_name": job.flow_name,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "blockchain_identifier": blockchain_identifier,
            "identifier_from_purchaser": identifier_from_purchaser,
            "masumi_payment_id": job.masumi_payment_id,
            "submit_result_hash": submit_result_hash,
            "job_output_preview": job_output[:200] + "..." if len(job_output) > 200 else job_output,
            "has_payment_response": bool(job.payment_response),
            "has_result_data": bool(job.result_data)
        }
        
        completion_data.append(job_data)
        
        # Print summary for each job
        status = "✅ READY" if submit_result_hash != "MISSING_DATA" else "❌ MISSING DATA"
        print(f"{status} Job {job.id}")
        print(f"   Flow: {job.flow_path}")
        print(f"   Blockchain ID: {blockchain_identifier}")
        print(f"   Hash: {submit_result_hash}")
        print(f"   Output preview: {job_output[:100]}...")
        print()
    
    # Save to JSON file (use current directory)
    output_file = "/tmp/payment_completion_data.json"
    with open(output_file, 'w') as f:
        json.dump(completion_data, f, indent=2, default=str)
    
    print(f"\n✅ Generated payment completion data for {len(finished_jobs)} jobs")
    print(f"📄 Data saved to: {output_file}")
    
    # Print summary statistics
    ready_jobs = [job for job in completion_data if job["submit_result_hash"] != "MISSING_DATA"]
    missing_data_jobs = [job for job in completion_data if job["submit_result_hash"] == "MISSING_DATA"]
    
    print(f"\n📊 Summary:")
    print(f"   Ready for completion: {len(ready_jobs)}")
    print(f"   Missing data: {len(missing_data_jobs)}")
    
    if missing_data_jobs:
        print(f"\n⚠️  Jobs with missing data:")
        for job in missing_data_jobs:
            print(f"   - {job['job_id']}: {job['flow_path']}")


if __name__ == "__main__":
    asyncio.run(main())