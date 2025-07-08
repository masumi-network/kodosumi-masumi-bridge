#!/usr/bin/env python3
"""
Script to retrieve input schemas for all flows from Kodosumi API
"""
import httpx
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

KODOSUMI_BASE_URL = os.getenv("KODOSUMI_BASE_URL")
KODOSUMI_USERNAME = os.getenv("KODOSUMI_USERNAME")
KODOSUMI_PASSWORD = os.getenv("KODOSUMI_PASSWORD")

def authenticate():
    """Authenticate with Kodosumi API and return cookies"""
    print(f"Authenticating with {KODOSUMI_BASE_URL}...")
    
    resp = httpx.post(
        f"{KODOSUMI_BASE_URL}/login",
        data={
            "name": KODOSUMI_USERNAME,
            "password": KODOSUMI_PASSWORD
        }
    )
    
    if resp.status_code != 200:
        print(f"Authentication failed with status code: {resp.status_code}")
        print(f"Response: {resp.text}")
        return None
        
    print("Authentication successful!")
    return resp.cookies

def get_flows(cookies):
    """Get list of all flows"""
    print("Retrieving flows...")
    
    resp = httpx.get(f"{KODOSUMI_BASE_URL}/flow", cookies=cookies)
    
    if resp.status_code != 200:
        print(f"Failed to get flows with status code: {resp.status_code}")
        print(f"Response: {resp.text}")
        return None
        
    flows_data = resp.json()
    flows = flows_data.get("items", [])
    print(f"Found {len(flows)} flows")
    return flows

def get_flow_schema(url, cookies):
    """Get input schema for a specific flow"""
    full_url = f"{KODOSUMI_BASE_URL}{url}"
    print(f"Getting schema for: {full_url}")
    
    resp = httpx.get(full_url, cookies=cookies)
    
    if resp.status_code != 200:
        print(f"Failed to get schema for {url} with status code: {resp.status_code}")
        return None
        
    return resp.json()

def main():
    # Authenticate
    cookies = authenticate()
    if not cookies:
        return
    
    # Get all flows
    flows = get_flows(cookies)
    if not flows:
        return
    
    # Get schema for each flow
    flow_schemas = {}
    
    for flow in flows:
        flow_url = flow.get("url")
        flow_summary = flow.get("summary")
        flow_uid = flow.get("uid")
        
        print(f"\n--- Processing flow: {flow_summary} ({flow_uid}) ---")
        
        schema = get_flow_schema(flow_url, cookies)
        if schema:
            flow_schemas[flow_uid] = {
                "summary": flow_summary,
                "url": flow_url,
                "schema": schema
            }
            print(f"✓ Successfully retrieved schema for {flow_summary}")
        else:
            print(f"✗ Failed to retrieve schema for {flow_summary}")
    
    # Save results to file
    output_file = "flow_schemas.json"
    with open(output_file, "w") as f:
        json.dump(flow_schemas, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    print(f"Successfully retrieved schemas for {len(flow_schemas)} flows")

if __name__ == "__main__":
    main()