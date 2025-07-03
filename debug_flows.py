#!/usr/bin/env python3
"""Debug script to test flow discovery and identify timeout issues."""

import asyncio
import httpx
import time
from typing import Dict, List, Any

async def test_flow_discovery():
    """Test the flow discovery process step by step."""
    
    base_url = "http://209.38.221.56:3370"
    username = "admin"
    password = "SecureKodo2025!"
    
    print("=== Testing Flow Discovery ===")
    
    # Step 1: Authentication
    print("1. Testing authentication...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/login",
                data={"name": username, "password": password},
                timeout=30.0
            )
            print(f"   Auth response: {response.status_code}")
            if response.status_code != 200:
                print(f"   Auth failed: {response.text}")
                return
            
            cookies = response.cookies
            print("   Authentication successful")
            
        except Exception as e:
            print(f"   Auth error: {e}")
            return
    
    # Step 2: Flow discovery with pagination
    print("2. Testing flow discovery with pagination...")
    
    all_flows = []
    offset = None
    page_count = 0
    max_pages = 5  # Limit for testing
    
    async with httpx.AsyncClient() as client:
        while page_count < max_pages:
            page_count += 1
            
            # Build URL
            url = f"{base_url}/flow"
            if offset is not None:
                url += f"?offset={offset}"
            
            print(f"   Page {page_count}: Requesting {url}")
            
            try:
                start_time = time.time()
                response = await client.get(url, cookies=cookies, timeout=30.0)
                elapsed = time.time() - start_time
                
                print(f"   Page {page_count}: Response {response.status_code} in {elapsed:.2f}s")
                
                if response.status_code != 200:
                    print(f"   Error: {response.text}")
                    break
                
                data = response.json()
                items = data.get("items", [])
                current_offset = data.get("offset")
                
                print(f"   Page {page_count}: Found {len(items)} items")
                print(f"   Page {page_count}: Next offset: {current_offset}")
                
                if not items:
                    print("   No more items, ending pagination")
                    break
                
                all_flows.extend(items)
                
                # Check if we got the same offset (infinite loop detection)
                if current_offset == offset:
                    print("   WARNING: Same offset returned, potential infinite loop!")
                    break
                
                offset = current_offset
                
                # If no offset returned, we're done
                if offset is None:
                    print("   No offset returned, ending pagination")
                    break
                
            except Exception as e:
                print(f"   Page {page_count}: Error: {e}")
                break
    
    print(f"3. Flow discovery completed:")
    print(f"   Total flows: {len(all_flows)}")
    print(f"   Pages processed: {page_count}")
    
    # Step 3: Test a single flow schema request
    if all_flows:
        print("4. Testing flow schema request...")
        first_flow = all_flows[0]
        flow_url = first_flow.get("url", "")
        
        if flow_url:
            print(f"   Requesting schema for: {flow_url}")
            async with httpx.AsyncClient() as client:
                try:
                    start_time = time.time()
                    response = await client.get(
                        f"{base_url}{flow_url}",
                        cookies=cookies,
                        timeout=30.0
                    )
                    elapsed = time.time() - start_time
                    print(f"   Schema response: {response.status_code} in {elapsed:.2f}s")
                    
                    if response.status_code == 200:
                        schema_data = response.json()
                        print(f"   Schema keys: {list(schema_data.keys())}")
                    else:
                        print(f"   Schema error: {response.text}")
                        
                except Exception as e:
                    print(f"   Schema error: {e}")

if __name__ == "__main__":
    asyncio.run(test_flow_discovery())