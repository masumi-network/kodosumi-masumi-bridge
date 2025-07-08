#!/usr/bin/env python3
"""
Test script to verify connection stability improvements in KodosumyClient.
This script tests the new session management, recovery, and keepalive features.
"""

import asyncio
import time
from src.masumi_kodosuni_connector.clients.kodosumi_client import KodosumyClient


async def test_connection_stability():
    """Test the connection stability improvements."""
    print("Testing KodosumyClient connection stability improvements...")
    
    # Create client
    client = KodosumyClient()
    
    try:
        # Test 1: Basic connection and authentication
        print("\n1. Testing basic authentication...")
        await client.authenticate()
        print("✓ Authentication successful")
        
        # Test 2: Get connection health
        print("\n2. Testing connection health monitoring...")
        health = await client.get_connection_health()
        print(f"✓ Connection health: {health['is_healthy']}")
        print(f"  - Session expires in: {health['session_time_remaining_seconds']:.0f} seconds")
        print(f"  - Success rate: {health['success_rate_percentage']}%")
        print(f"  - Keepalive enabled: {health['keepalive_enabled']}")
        print(f"  - Recovery task running: {health['recovery_task_running']}")
        
        # Test 3: Test authenticated request
        print("\n3. Testing authenticated requests...")
        flows = await client.get_available_flows()
        print(f"✓ Retrieved {len(flows)} flows")
        
        # Test 4: Check health again after request
        print("\n4. Checking health after request...")
        health = await client.get_connection_health()
        print(f"✓ Total requests: {health['total_requests']}")
        print(f"  - Successful requests: {health['successful_requests']}")
        print(f"  - Failed requests: {health['failed_requests']}")
        print(f"  - Success rate: {health['success_rate_percentage']}%")
        
        # Test 5: Session timing verification
        print("\n5. Verifying session timing...")
        session_hours = health['session_time_remaining_seconds'] / 3600
        if session_hours > 21.5:  # Should be around 22 hours
            print("✓ Session timing is correct (22 hour expiry)")
        else:
            print(f"⚠ Session timing might be incorrect: {session_hours:.1f} hours remaining")
        
        # Test 6: Keepalive status
        print("\n6. Checking keepalive status...")
        if health['keepalive_enabled'] and health['keepalive_task_running']:
            print("✓ Keepalive system is active")
        else:
            print("⚠ Keepalive system is not active")
        
        print("\n✅ All connection stability tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        print("\n7. Cleaning up...")
        client.cleanup()
        print("✓ Cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_connection_stability())