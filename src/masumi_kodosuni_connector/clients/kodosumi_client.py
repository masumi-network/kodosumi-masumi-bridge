import httpx
from typing import Dict, Any, Optional, List
from masumi_kodosuni_connector.config.settings import settings
from masumi_kodosuni_connector.config.logging import get_logger
from masumi_kodosuni_connector.utils.rate_limiter import kodosumi_http_client


class KodosumyFlowStatus:
    STARTING = "starting"
    RUNNING = "running" 
    FINISHED = "finished"
    ERROR = "error"


def interpret_kodosumi_status(status_data: Dict[str, Any]) -> str:
    """Interpret Kodosumi status response from both new and old API endpoints."""
    logger = get_logger("kodosumi.status")
    
    logger.debug("Interpreting Kodosumi status", 
                 response_keys=list(status_data.keys()),
                 has_status_field="status" in status_data,
                 has_elements="elements" in status_data)
    
    # Check if this is new format (from /outputs/status/{fid})
    if "status" in status_data:
        status = status_data.get("status", "").lower()
        logger.debug("New API format detected", status_field=status)
        
        # Map Kodosumi status values to our internal status
        if status == "finished":
            logger.debug("Status interpreted as FINISHED")
            return KodosumyFlowStatus.FINISHED
        elif status == "running":
            logger.debug("Status interpreted as RUNNING")
            return KodosumyFlowStatus.RUNNING
        elif status == "error" or status == "failed":
            logger.debug("Status interpreted as ERROR")
            return KodosumyFlowStatus.ERROR
        elif status == "starting" or status == "pending":
            logger.debug("Status interpreted as STARTING")
            return KodosumyFlowStatus.STARTING
        else:
            # If no clear status, fall back to looking at the final field
            final_result = status_data.get("final")
            if final_result:
                logger.debug("Unknown status but final result present, interpreting as FINISHED", 
                           unknown_status=status)
                return KodosumyFlowStatus.FINISHED
            else:
                logger.warning("Unknown status, defaulting to RUNNING", unknown_status=status)
                return KodosumyFlowStatus.RUNNING
    
    # Check if this is old format (from form endpoint with elements)
    elif "elements" in status_data:
        elements = status_data.get("elements", [])
        logger.debug("Old API format detected", element_count=len(elements))
        
        # Look for completion indicators in elements
        for i, element in enumerate(elements):
            element_type = element.get("type", "")
            element_text = element.get("text", "")
            element_value = element.get("value", "")
            
            # Look for result or completion indicators
            if element_type in ["markdown", "text"] and element_text:
                # Check for completion keywords in text
                text_lower = element_text.lower()
                if any(keyword in text_lower for keyword in ["completed", "finished", "result", "done", "analysis complete"]):
                    logger.debug("Completion indicator found in element text", 
                               element_index=i, element_type=element_type)
                    return KodosumyFlowStatus.FINISHED
            
            # Check if text/input fields have been populated (indicating completion)
            if element_type in ["text", "textarea"] and element_value and len(element_value) > 50:
                logger.debug("Populated result field found, interpreting as FINISHED", 
                           element_index=i, element_type=element_type, value_length=len(element_value))
                return KodosumyFlowStatus.FINISHED
        
        # If we have elements but no completion indicators, assume still running
        logger.debug("Old format with elements but no completion indicators, interpreting as RUNNING")
        return KodosumyFlowStatus.RUNNING
    
    else:
        # Unknown format
        final_result = status_data.get("final")
        logger.debug("Unknown response format", has_final_field=bool(final_result))
        
        if final_result:
            logger.debug("Final result present in unknown format, interpreting as FINISHED")
            return KodosumyFlowStatus.FINISHED
        else:
            logger.warning("No clear status indicators, defaulting to RUNNING")
            return KodosumyFlowStatus.RUNNING


class KodosumyClient:
    def __init__(self):
        self.base_url = settings.kodosumi_base_url.rstrip("/")
        self.username = settings.kodosumi_username
        self.password = settings.kodosumi_password
        self._cookies: Optional[httpx.Cookies] = None
        self.logger = get_logger("kodosumi.client")
    
    async def authenticate(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await kodosumi_http_client.request(
                client, "post",
                f"{self.base_url}/login",
                data={"name": self.username, "password": self.password},
                timeout=30.0
            )
            self._cookies = response.cookies
    
    async def _ensure_authenticated(self) -> httpx.Cookies:
        if self._cookies is None:
            await self.authenticate()
        return self._cookies
    
    async def get_available_flows(self) -> List[Dict[str, Any]]:
        cookies = await self._ensure_authenticated()
        all_flows = []
        offset = None
        page_size = 10  # Default page size
        
        self.logger.info("Starting flow discovery", base_url=self.base_url)
        
        async with httpx.AsyncClient() as client:
            while True:
                # Request flows with offset for pagination
                url = f"{self.base_url}/flow"
                if offset is not None:
                    url += f"?offset={offset}"
                
                self.logger.debug("Requesting flows page", url=url, offset=offset)
                response = await kodosumi_http_client.request(
                    client, "get", url,
                    cookies=cookies,
                    timeout=30.0
                )
                data = response.json()
                
                self.logger.debug("Flow API response received", 
                                response_keys=list(data.keys()),
                                status_code=response.status_code)
                
                items = data.get("items", [])
                if not items:
                    self.logger.debug("No more items found, ending pagination")
                    break
                
                all_flows.extend(items)
                self.logger.debug("Retrieved flows batch", 
                                batch_size=len(items), 
                                total_flows=len(all_flows))
                
                # If we got fewer items than expected page size, we're likely at the end
                if len(items) < page_size:
                    self.logger.debug("Partial batch received, assuming end of data", 
                                    received=len(items), 
                                    expected_page_size=page_size)
                    break
                
                # Get the next offset from the API response
                current_offset = data.get("offset")
                if current_offset is None:
                    self.logger.debug("No offset in response, ending pagination")
                    break
                
                # Set offset for next request
                offset = current_offset
                
                # Safety check to prevent infinite loops (max 100 pages)
                if len(all_flows) > 1000:
                    self.logger.warning("Safety limit reached, stopping flow discovery", 
                                      flows_retrieved=len(all_flows))
                    break
        
        self.logger.info("Flow discovery completed", total_flows=len(all_flows))
        return all_flows
    
    async def get_flow_schema(self, flow_path: str) -> Dict[str, Any]:
        cookies = await self._ensure_authenticated()
        
        async with httpx.AsyncClient() as client:
            response = await kodosumi_http_client.request(
                client, "get",
                f"{self.base_url}{flow_path}",
                cookies=cookies,
                timeout=30.0
            )
            return response.json()
    
    async def launch_flow(self, flow_path: str, inputs: Dict[str, Any]) -> str:
        cookies = await self._ensure_authenticated()
        
        self.logger.info("Launching Kodosumi flow", 
                        flow_path=flow_path, 
                        input_keys=list(inputs.keys()),
                        full_url=f"{self.base_url}{flow_path}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{flow_path}",
                    json=inputs,
                    cookies=cookies,
                    timeout=30.0
                )
                
                self.logger.debug("Kodosumi launch response received",
                                status_code=response.status_code,
                                response_headers=dict(response.headers),
                                response_size=len(response.text))
                
                if response.status_code >= 400:
                    self.logger.error("Kodosumi launch failed with error response",
                                    status_code=response.status_code,
                                    response_text=response.text[:500])  # Limit text length
                    return None  # Return None for error to prevent exception during debugging
                
                response.raise_for_status()
                
                # According to Kodosumi docs, successful POST returns {"result": "fid"}
                data = response.json()
                fid = data.get("result")
                
                if not fid:
                    # Check for errors
                    errors = data.get("errors")
                    if errors:
                        self.logger.error("Kodosumi validation errors", errors=errors)
                        raise Exception(f"Kodosumi validation errors: {errors}")
                    else:
                        self.logger.error("No fid returned from Kodosumi", response_data=data)
                        raise Exception(f"No fid returned from Kodosumi: {data}")
                
                self.logger.info("Flow launched successfully", fid=fid, flow_path=flow_path)
                return fid
                
            except Exception as e:
                self.logger.error("Kodosumi launch failed with exception", 
                                error=str(e), 
                                error_type=type(e).__name__,
                                flow_path=flow_path)
                raise
    
    async def get_flow_status(self, flow_path: str, fid: str) -> Dict[str, Any]:
        cookies = await self._ensure_authenticated()
        
        self.logger.debug("Getting flow status", flow_path=flow_path, fid=fid)
        
        # Try the new API first, fall back to old API for compatibility
        async with httpx.AsyncClient() as client:
            try:
                # Try new API endpoint first
                new_api_url = f"{self.base_url}/outputs/status/{fid}"
                self.logger.debug("Trying new API endpoint", url=new_api_url)
                
                response = await client.get(
                    new_api_url,
                    cookies=cookies,
                    timeout=30.0
                )
                if response.status_code == 200:
                    self.logger.debug("Successfully used new API endpoint")
                    return response.json()
                else:
                    self.logger.debug("New API returned non-200 status", status_code=response.status_code)
                    
            except Exception as e:
                self.logger.debug("New API failed, trying old API", error=str(e))
            
            try:
                # Fall back to old API for existing jobs
                old_api_url = f"{self.base_url}{flow_path}?run_id={fid}"
                self.logger.debug("Trying old API endpoint", url=old_api_url)
                
                response = await client.get(
                    old_api_url,
                    cookies=cookies,
                    timeout=30.0
                )
                if response.status_code == 200:
                    self.logger.debug("Successfully used old API endpoint")
                    return response.json()
                else:
                    self.logger.error("Old API also failed", 
                                    status_code=response.status_code,
                                    response_text=response.text[:200])
                    response.raise_for_status()
                    
            except Exception as e:
                self.logger.error("Both API endpoints failed", 
                                final_error=str(e),
                                flow_path=flow_path,
                                fid=fid)
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
        self.logger.debug("Extracting flow result", flow_path=flow_path, fid=fid)
        
        try:
            status_data = await self.get_flow_status(flow_path, fid)
            
            # New API format: check for 'final' field first
            final_result = status_data.get("final")
            if final_result:
                self.logger.debug("Found final result in new API format")
                
                # Parse the final result JSON to extract actual content
                try:
                    import json
                    final_data = json.loads(final_result)
                    
                    # Extract meaningful content from common structures
                    actual_content = final_result  # fallback to raw
                    
                    if isinstance(final_data, dict):
                        # Look for common output patterns
                        content_paths = [
                            ("CrewOutput", "raw"),
                            ("raw",),
                            ("output",),
                            ("result",),
                            ("content",)
                        ]
                        
                        for path in content_paths:
                            current = final_data
                            try:
                                for key in path:
                                    current = current[key]
                                actual_content = current
                                self.logger.debug("Extracted content using path", content_path=path)
                                break
                            except (KeyError, TypeError):
                                continue
                    
                    self.logger.debug("Successfully extracted content from final JSON")
                    return {
                        "output": actual_content,
                        "status": "completed",
                        "raw_response": status_data
                    }
                except json.JSONDecodeError:
                    self.logger.debug("Could not parse final result as JSON, using raw content")
                    return {
                        "output": final_result,
                        "status": "completed",
                        "raw_response": status_data
                    }
            
            # Old API format: extract from elements
            elements = status_data.get("elements", [])
            if elements:
                self.logger.debug("Extracting results from old API format", element_count=len(elements))
                result_parts = []
                
                for i, element in enumerate(elements):
                    element_type = element.get("type", "")
                    element_text = element.get("text", "")
                    element_value = element.get("value", "")
                    
                    # Extract meaningful results from different element types
                    if element_type == "markdown" and element_text and len(element_text) > 100:
                        result_parts.append(element_text)
                        self.logger.debug("Added markdown element to results", element_index=i)
                    elif element_type == "text" and element_value and len(element_value) > 50:
                        result_parts.append(element_value)
                        self.logger.debug("Added text element to results", element_index=i)
                    elif element_type == "textarea" and element_value:
                        result_parts.append(element_value)
                        self.logger.debug("Added textarea element to results", element_index=i)
                
                if result_parts:
                    combined_result = "\n\n".join(result_parts)
                    self.logger.info("Extracted results from old format", 
                                   result_parts_count=len(result_parts),
                                   total_length=len(combined_result))
                    return {
                        "output": combined_result,
                        "status": "completed",
                        "raw_response": status_data
                    }
            
            self.logger.debug("No results found in either format, job may still be running")
            return {
                "status": "pending",
                "raw_response": status_data
            }
                
        except Exception as e:
            self.logger.error("Error extracting flow results", 
                            error=str(e), 
                            flow_path=flow_path, 
                            fid=fid)
            return {"error": str(e)}