import httpx
from typing import Dict, Any, Optional, List
from masumi_kodosuni_connector.config.settings import settings


class KodosumyFlowStatus:
    STARTING = "starting"
    RUNNING = "running" 
    FINISHED = "finished"
    ERROR = "error"


def interpret_kodosumi_status(status_data: Dict[str, Any]) -> str:
    """Interpret Kodosumi status response from both new and old API endpoints."""
    print(f"DEBUG: interpret_kodosumi_status called with keys: {list(status_data.keys())}")
    
    # Check if this is new format (from /outputs/status/{fid})
    if "status" in status_data:
        status = status_data.get("status", "").lower()
        print(f"DEBUG: New API format - Kodosumi status field: '{status}'")
        
        # Map Kodosumi status values to our internal status
        if status == "finished":
            print(f"DEBUG: Detected FINISHED from status field")
            return KodosumyFlowStatus.FINISHED
        elif status == "running":
            print(f"DEBUG: Detected RUNNING from status field")
            return KodosumyFlowStatus.RUNNING
        elif status == "error" or status == "failed":
            print(f"DEBUG: Detected ERROR from status field")
            return KodosumyFlowStatus.ERROR
        elif status == "starting" or status == "pending":
            print(f"DEBUG: Detected STARTING from status field")
            return KodosumyFlowStatus.STARTING
        else:
            # If no clear status, fall back to looking at the final field
            final_result = status_data.get("final")
            if final_result:
                print(f"DEBUG: Detected FINISHED based on final result presence")
                return KodosumyFlowStatus.FINISHED
            else:
                print(f"DEBUG: Unknown status '{status}', defaulting to RUNNING")
                return KodosumyFlowStatus.RUNNING
    
    # Check if this is old format (from form endpoint with elements)
    elif "elements" in status_data:
        print(f"DEBUG: Old API format - checking elements")
        elements = status_data.get("elements", [])
        
        # Look for completion indicators in elements
        for element in elements:
            element_type = element.get("type", "")
            element_text = element.get("text", "")
            element_value = element.get("value", "")
            
            # Look for result or completion indicators
            if element_type in ["markdown", "text"] and element_text:
                # Check for completion keywords in text
                text_lower = element_text.lower()
                if any(keyword in text_lower for keyword in ["completed", "finished", "result", "done", "analysis complete"]):
                    print(f"DEBUG: Found completion indicator in element text")
                    return KodosumyFlowStatus.FINISHED
            
            # Check if text/input fields have been populated (indicating completion)
            if element_type in ["text", "textarea"] and element_value and len(element_value) > 50:
                print(f"DEBUG: Found populated result field, assuming FINISHED")
                return KodosumyFlowStatus.FINISHED
        
        # If we have elements but no completion indicators, assume still running
        print(f"DEBUG: Old format with elements but no completion indicators, assuming RUNNING")
        return KodosumyFlowStatus.RUNNING
    
    else:
        # Unknown format
        print(f"DEBUG: Unknown response format, checking for final field")
        final_result = status_data.get("final")
        if final_result:
            print(f"DEBUG: Found final result, assuming FINISHED")
            return KodosumyFlowStatus.FINISHED
        else:
            print(f"DEBUG: No clear indicators, defaulting to RUNNING")
            return KodosumyFlowStatus.RUNNING


class KodosumyClient:
    def __init__(self):
        self.base_url = settings.kodosumi_base_url.rstrip("/")
        self.username = settings.kodosumi_username
        self.password = settings.kodosumi_password
        self._cookies: Optional[httpx.Cookies] = None
    
    async def authenticate(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/login",
                data={"name": self.username, "password": self.password},
                timeout=30.0
            )
            response.raise_for_status()
            self._cookies = response.cookies
    
    async def _ensure_authenticated(self) -> httpx.Cookies:
        if self._cookies is None:
            await self.authenticate()
        return self._cookies
    
    async def get_available_flows(self) -> List[Dict[str, Any]]:
        cookies = await self._ensure_authenticated()
        all_flows = []
        offset = 0
        page_size = 10  # Default page size, we'll try to determine this
        
        async with httpx.AsyncClient() as client:
            while True:
                # Request flows with offset for pagination
                url = f"{self.base_url}/flow"
                if offset > 0:
                    url += f"?offset={offset}"
                
                print(f"DEBUG: Requesting flows from URL: {url}")
                response = await client.get(
                    url,
                    cookies=cookies,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                print(f"DEBUG: Response keys: {list(data.keys())}")
                print(f"DEBUG: Response data: {data}")
                
                items = data.get("items", [])
                if not items:
                    print(f"DEBUG: No more items found, breaking pagination")
                    break
                
                all_flows.extend(items)
                print(f"DEBUG: Retrieved {len(items)} flows, total so far: {len(all_flows)}")
                
                # If we got fewer items than expected page size, we're likely at the end
                if len(items) < page_size:
                    print(f"DEBUG: Got {len(items)} items (less than page size {page_size}), assuming end of data")
                    break
                
                # Check different pagination patterns
                current_offset = data.get("offset")
                if current_offset is not None:
                    # Use the offset returned by the API
                    offset = current_offset
                    print(f"DEBUG: Using API-provided offset: {offset}")
                else:
                    # Increment offset by the number of items we got
                    offset += len(items)
                    print(f"DEBUG: Incrementing offset by items count: {offset}")
                
                # Safety check to prevent infinite loops
                if offset > 1000:  # Arbitrary large number
                    print(f"DEBUG: Safety break at offset {offset}")
                    break
        
        print(f"DEBUG: Retrieved total of {len(all_flows)} flows")
        return all_flows
    
    async def get_flow_schema(self, flow_path: str) -> Dict[str, Any]:
        cookies = await self._ensure_authenticated()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{flow_path}",
                cookies=cookies,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def launch_flow(self, flow_path: str, inputs: Dict[str, Any]) -> str:
        cookies = await self._ensure_authenticated()
        
        print(f"DEBUG: Launching flow at {self.base_url}{flow_path}")
        print(f"DEBUG: Flow inputs: {inputs}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{flow_path}",
                    json=inputs,
                    cookies=cookies,
                    timeout=30.0
                )
                print(f"DEBUG: Kodosumi response status: {response.status_code}")
                print(f"DEBUG: Kodosumi response headers: {dict(response.headers)}")
                print(f"DEBUG: Kodosumi full response text: {response.text}")
                
                if response.status_code >= 400:
                    print(f"DEBUG: Error response received - not raising for debugging")
                    return None  # Return None for error to prevent exception during debugging
                
                response.raise_for_status()
                
                # According to Kodosumi docs, successful POST returns {"result": "fid"}
                data = response.json()
                fid = data.get("result")
                
                if not fid:
                    # Check for errors
                    errors = data.get("errors")
                    if errors:
                        raise Exception(f"Kodosumi validation errors: {errors}")
                    else:
                        raise Exception(f"No fid returned from Kodosumi: {data}")
                
                print(f"DEBUG: Successfully launched flow, got fid: {fid}")
                return fid
            except Exception as e:
                print(f"DEBUG: Kodosumi launch error: {e}")
                print(f"DEBUG: Error type: {type(e)}")
                raise
    
    async def get_flow_status(self, flow_path: str, fid: str) -> Dict[str, Any]:
        cookies = await self._ensure_authenticated()
        
        # Try the new API first, fall back to old API for compatibility
        async with httpx.AsyncClient() as client:
            try:
                # Try new API endpoint first
                response = await client.get(
                    f"{self.base_url}/outputs/status/{fid}",
                    cookies=cookies,
                    timeout=30.0
                )
                if response.status_code == 200:
                    print(f"DEBUG: Successfully used new /outputs/status/{fid} endpoint")
                    return response.json()
            except Exception as e:
                print(f"DEBUG: New API failed, trying old API. Error: {e}")
            
            try:
                # Fall back to old API for existing jobs
                response = await client.get(
                    f"{self.base_url}{flow_path}?run_id={fid}",
                    cookies=cookies,
                    timeout=30.0
                )
                if response.status_code == 200:
                    print(f"DEBUG: Successfully used old {flow_path}?run_id={fid} endpoint")
                    return response.json()
                else:
                    print(f"DEBUG: Old API also failed with status {response.status_code}")
                    response.raise_for_status()
            except Exception as e:
                print(f"DEBUG: Both APIs failed. Final error: {e}")
                raise
    
    async def get_flow_events(self, flow_path: str, fid: str) -> List[Dict[str, Any]]:
        # Since Kodosumi doesn't seem to have traditional events API,
        # we'll extract information from the status response
        try:
            status_data = await self.get_flow_status(flow_path, fid)
            elements = status_data.get("elements", [])
            
            # Convert elements to event-like structure for compatibility
            events = []
            for element in elements:
                if element.get("type") in ["markdown", "text"] and element.get("text"):
                    events.append({
                        "event": "status_update",
                        "data": {
                            "type": element.get("type"),
                            "content": element.get("text", ""),
                            "timestamp": None  # Kodosumi doesn't provide timestamps
                        }
                    })
            return events
        except:
            return []
    
    async def get_flow_result(self, flow_path: str, fid: str) -> Dict[str, Any]:
        # Extract result from the status response (supports both old and new formats)
        try:
            status_data = await self.get_flow_status(flow_path, fid)
            
            # New API format: check for 'final' field first
            final_result = status_data.get("final")
            if final_result:
                print(f"DEBUG: Found final result in new API format")
                
                # Parse the final result JSON to extract actual content
                try:
                    import json
                    final_data = json.loads(final_result)
                    
                    # Extract meaningful content from common structures
                    actual_content = final_result  # fallback to raw
                    
                    if isinstance(final_data, dict):
                        # Look for common output patterns
                        if "CrewOutput" in final_data and "raw" in final_data["CrewOutput"]:
                            actual_content = final_data["CrewOutput"]["raw"]
                        elif "raw" in final_data:
                            actual_content = final_data["raw"]
                        elif "output" in final_data:
                            actual_content = final_data["output"]
                        elif "result" in final_data:
                            actual_content = final_data["result"]
                        elif "content" in final_data:
                            actual_content = final_data["content"]
                    
                    print(f"DEBUG: Extracted actual content from final JSON")
                    return {
                        "output": actual_content,
                        "status": "completed",
                        "raw_response": status_data
                    }
                except json.JSONDecodeError:
                    print(f"DEBUG: Could not parse final result as JSON, using as-is")
                    return {
                        "output": final_result,
                        "status": "completed",
                        "raw_response": status_data
                    }
            
            # Old API format: extract from elements
            elements = status_data.get("elements", [])
            if elements:
                print(f"DEBUG: Extracting results from old API format elements")
                result_parts = []
                
                for element in elements:
                    element_type = element.get("type", "")
                    element_text = element.get("text", "")
                    element_value = element.get("value", "")
                    
                    # Extract meaningful results from different element types
                    if element_type == "markdown" and element_text:
                        # Skip short markdown elements (likely headers/descriptions)
                        if len(element_text) > 100:
                            result_parts.append(element_text)
                    elif element_type == "text" and element_value:
                        # Text fields that have been populated with results
                        if len(element_value) > 50:
                            result_parts.append(element_value)
                    elif element_type == "textarea" and element_value:
                        # Textarea fields with results
                        result_parts.append(element_value)
                
                if result_parts:
                    combined_result = "\n\n".join(result_parts)
                    print(f"DEBUG: Extracted {len(result_parts)} result parts from old format")
                    return {
                        "output": combined_result,
                        "status": "completed",
                        "raw_response": status_data
                    }
            
            print(f"DEBUG: No results found in either format, job may still be running")
            return {
                "status": "pending",
                "raw_response": status_data
            }
                
        except Exception as e:
            print(f"DEBUG: Error extracting results: {e}")
            return {"error": str(e)}