#!/usr/bin/env python3
"""
Test script to validate payment completion functionality.
This script tests the masumi payment completion flow and verifies the hash generation.
"""

import asyncio
import sys
import os
import json
import hashlib
from typing import Dict, Any

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
    print("ERROR: Could not find .env file")
    sys.exit(1)

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(project_root, 'src'))

# Only import masumi if not in test mode
try:
    from masumi_kodosuni_connector.config.settings import settings
    
    if not settings.masumi_test_mode:
        from masumi.config import Config
        from masumi.payment import Payment
        print("✅ Masumi package imported successfully")
    else:
        print("⚠️  Running in test mode - masumi package not imported")
        
except ImportError as e:
    print(f"❌ Failed to import masumi package: {e}")
    print("This might be expected if masumi is not installed in this environment")


def create_masumi_output_hash(job_output: str, identifier_from_purchaser: str) -> str:
    """
    Test hash creation to match masumi package logic.
    """
    # Try to replicate the masumi package hash creation
    combined_data = f"{job_output}{identifier_from_purchaser}"
    hash_object = hashlib.sha256(combined_data.encode('utf-8'))
    return hash_object.hexdigest()


async def test_masumi_payment_creation():
    """Test creating a payment request with masumi package."""
    print("\n🧪 Testing Masumi Payment Creation...")
    
    if settings.masumi_test_mode:
        print("⚠️  Skipping masumi test - running in test mode")
        return None
    
    try:
        # Test agent identifier
        test_agent_id = "ad6424e3ce9e47bbd8364984bd731b41de591f1d11f6d7d43d0da9b9d545df3286c57e23c930f9716d556c6ace3ed1506b6e0e32ddf3e61940909abf"
        
        config = Config(
            payment_service_url=settings.payment_service_url,
            payment_api_key=settings.payment_api_key
        )
        print(f"✅ Config created with URL: {settings.payment_service_url}")
        
        # Create payment instance
        payment = Payment(
            agent_identifier=test_agent_id,
            config=config,
            identifier_from_purchaser="test_identifier_123",
            input_data={"test": "data"},
            network=settings.network
        )
        print("✅ Payment instance created")
        
        # Test payment request creation
        print("📤 Testing payment request creation...")
        payment_response = await payment.create_payment_request()
        print("✅ Payment request created successfully")
        
        # Extract blockchain identifier
        blockchain_id = payment_response["data"]["blockchainIdentifier"]
        print(f"📋 Blockchain ID: {blockchain_id}")
        
        return {
            "payment": payment,
            "response": payment_response,
            "blockchain_id": blockchain_id
        }
        
    except Exception as e:
        print(f"❌ Payment creation failed: {e}")
        return None


async def test_payment_completion(payment_data: Dict[str, Any]):
    """Test payment completion with masumi package."""
    print("\n🎯 Testing Payment Completion...")
    
    if not payment_data:
        print("⚠️  Skipping completion test - no payment data")
        return
    
    try:
        payment = payment_data["payment"]
        blockchain_id = payment_data["blockchain_id"]
        
        # Test job output
        test_output = {
            "output": "This is a test job result with some meaningful content for testing",
            "status": "completed",
            "metadata": {"test": True}
        }
        
        print(f"📤 Testing payment completion for blockchain ID: {blockchain_id}")
        print(f"📋 Test output: {str(test_output)[:100]}...")
        
        # Call payment completion
        completion_response = await payment.complete_payment(blockchain_id, test_output)
        print("✅ Payment completion successful")
        print(f"📋 Completion response: {completion_response}")
        
        return completion_response
        
    except Exception as e:
        print(f"❌ Payment completion failed: {e}")
        return None


def test_hash_generation():
    """Test hash generation logic."""
    print("\n🔐 Testing Hash Generation...")
    
    test_cases = [
        {
            "output": "This is a test result",
            "identifier": "test_id_123"
        },
        {
            "output": '{"output": "Complex JSON result", "status": "completed"}',
            "identifier": "complex_test_456"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        output = test_case["output"]
        identifier = test_case["identifier"]
        
        hash_result = create_masumi_output_hash(output, identifier)
        
        print(f"  Test {i}:")
        print(f"    Output: {output[:50]}...")
        print(f"    Identifier: {identifier}")
        print(f"    Hash: {hash_result}")
        print()


async def validate_existing_jobs():
    """Validate hash generation for existing finished jobs."""
    print("\n📊 Validating Existing Jobs...")
    
    # Check if we have the data file
    data_file = "/Users/patricktobler/masumi_kodosuni_connector/data.json"
    if not os.path.exists(data_file):
        print(f"⚠️  Data file not found: {data_file}")
        return
    
    try:
        with open(data_file, 'r') as f:
            jobs = json.load(f)
        
        print(f"📋 Found {len(jobs)} jobs in data file")
        
        # Validate a few jobs
        for i, job in enumerate(jobs[:3]):  # Check first 3 jobs
            job_id = job.get("job_id", "unknown")
            blockchain_id = job.get("blockchain_identifier", "")
            hash_value = job.get("submit_result_hash", "")
            
            print(f"  Job {i+1} ({job_id}):")
            print(f"    Blockchain ID: {blockchain_id}")
            print(f"    Hash: {hash_value}")
            print(f"    Status: {'✅ Ready' if hash_value != 'MISSING_DATA' else '❌ Missing Data'}")
            print()
            
    except Exception as e:
        print(f"❌ Error reading data file: {e}")


async def main():
    """Main test function."""
    print("🚀 Starting Payment Completion Validation Tests")
    print("=" * 60)
    
    # Test 1: Hash generation
    test_hash_generation()
    
    # Test 2: Validate existing jobs
    await validate_existing_jobs()
    
    # Test 3: Masumi payment creation (if not in test mode)
    payment_data = await test_masumi_payment_creation()
    
    # Test 4: Payment completion (if payment creation worked)
    if payment_data:
        await test_payment_completion(payment_data)
    
    print("\n" + "=" * 60)
    print("🏁 Tests completed!")
    
    # Summary
    print("\n📋 Next Steps:")
    print("1. Check the test output above for any errors")
    print("2. If payment creation works, the masumi integration is correct")
    print("3. If hash generation works, the completion should work")
    print("4. Monitor logs when real jobs complete to see if payment completion succeeds")


if __name__ == "__main__":
    asyncio.run(main())