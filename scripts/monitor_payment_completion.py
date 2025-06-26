#!/usr/bin/env python3
"""
Monitor payment completion in real-time.
This script monitors the database and logs for payment completion events.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Load environment variables
from dotenv import load_dotenv

project_root = os.path.join(os.path.dirname(__file__), '..')
possible_env_files = [
    os.path.join(project_root, '.env'),
    '/root/kodosumi-masumi-bridge/.env',
    '.env'
]

for env_path in possible_env_files:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

sys.path.insert(0, os.path.join(project_root, 'src'))

from masumi_kodosuni_connector.database.connection import AsyncSessionLocal
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus
from sqlalchemy import select, desc


async def monitor_jobs():
    """Monitor job completions and payment status."""
    print("🔍 Starting Payment Completion Monitor")
    print("Watching for job completions and payment events...")
    print("Press Ctrl+C to stop\n")
    
    last_check = datetime.utcnow() - timedelta(hours=1)  # Start from 1 hour ago
    
    try:
        while True:
            async with AsyncSessionLocal() as session:
                # Get recently completed jobs
                result = await session.execute(
                    select(FlowRun)
                    .where(FlowRun.updated_at > last_check)
                    .where(FlowRun.status == FlowRunStatus.FINISHED)
                    .order_by(desc(FlowRun.updated_at))
                )
                recent_jobs = result.scalars().all()
                
                for job in recent_jobs:
                    print(f"🎯 Job Completed: {job.id}")
                    print(f"   Flow: {job.flow_path}")
                    print(f"   Completed: {job.completed_at}")
                    print(f"   Payment ID: {job.masumi_payment_id}")
                    print(f"   Has Result: {'✅' if job.result_data else '❌'}")
                    print(f"   Has Payment Response: {'✅' if job.payment_response else '❌'}")
                    
                    # Check if payment completion data is available
                    if job.payment_response and job.result_data:
                        blockchain_id = None
                        if isinstance(job.payment_response, dict):
                            blockchain_id = job.payment_response.get('data', {}).get('blockchainIdentifier')
                        
                        if blockchain_id:
                            print(f"   ✅ Ready for payment completion")
                            print(f"   Blockchain ID: {blockchain_id}")
                        else:
                            print(f"   ❌ Missing blockchain identifier")
                    else:
                        print(f"   ❌ Missing payment or result data")
                    
                    print("-" * 50)
                
                if recent_jobs:
                    print(f"📊 Found {len(recent_jobs)} recently completed jobs")
                else:
                    print("⏳ No new job completions...")
                
                last_check = datetime.utcnow()
            
            # Wait 30 seconds before checking again
            await asyncio.sleep(30)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")


async def check_job_stats():
    """Show current job statistics."""
    print("📊 Current Job Statistics")
    print("=" * 40)
    
    async with AsyncSessionLocal() as session:
        # Count jobs by status
        for status in FlowRunStatus:
            result = await session.execute(
                select(FlowRun).where(FlowRun.status == status)
            )
            count = len(result.scalars().all())
            print(f"   {status.value}: {count}")
        
        # Recent finished jobs
        result = await session.execute(
            select(FlowRun)
            .where(FlowRun.status == FlowRunStatus.FINISHED)
            .order_by(desc(FlowRun.completed_at))
            .limit(5)
        )
        recent_finished = result.scalars().all()
        
        print(f"\n🎯 Recent Finished Jobs ({len(recent_finished)}):")
        for job in recent_finished:
            completion_ready = (
                job.payment_response and 
                job.result_data and 
                job.payment_response.get('data', {}).get('blockchainIdentifier')
            )
            status_icon = "✅" if completion_ready else "❌"
            print(f"   {status_icon} {job.id} - {job.flow_path} ({job.completed_at})")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor payment completion")
    parser.add_argument("--stats", action="store_true", help="Show job statistics and exit")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring mode")
    
    args = parser.parse_args()
    
    if args.stats:
        asyncio.run(check_job_stats())
    elif args.monitor:
        asyncio.run(monitor_jobs())
    else:
        print("Usage:")
        print("  --stats     Show current job statistics")
        print("  --monitor   Start real-time monitoring")
        print("\nExample:")
        print("  python3 monitor_payment_completion.py --stats")