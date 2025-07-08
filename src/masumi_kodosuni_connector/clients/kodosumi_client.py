import httpx
import asyncio
import time
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
        self._session_expires_at: Optional[float] = None
        self._session_lock = asyncio.Lock()
        self._last_successful_request = time.time()
        self._connection_failures = 0
        self._max_connection_failures = 3
        self._is_healthy = True
        self._recovery_task: Optional[asyncio.Task] = None
        self._recovery_interval = 300  # 5 minutes
        self._recovery_backoff = 1.0  # Start with 1 second backoff
        self._max_recovery_backoff = 300  # Max 5 minutes between recovery attempts
        self._keepalive_task: Optional[asyncio.Task] = None
        self._keepalive_interval = 600  # 10 minutes
        self._keepalive_enabled = True
        self._connection_start_time = time.time()
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._last_health_check = None
        self.logger = get_logger("kodosumi.client")
    
    async def authenticate(self) -> None:
        """Authenticate with Kodosumi and store session cookies with expiration tracking."""
        async with self._session_lock:
            self.logger.info("Authenticating with Kodosumi", url=f"{self.base_url}/login")
            
            # Clear any existing session state before authenticating
            self._clear_session_state()
            
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    response = await kodosumi_http_client.request(
                        client, "post",
                        f"{self.base_url}/login",
                        data={"name": self.username, "password": self.password},
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        self._cookies = response.cookies
                        # Set session expiration to 5 hours from now
                        # Re-authenticate every 5 hours to ensure fresh sessions
                        self._session_expires_at = time.time() + (5 * 60 * 60)
                        self._last_successful_request = time.time()
                        self._connection_failures = 0
                        self._is_healthy = True
                        self.logger.info("Authentication successful", expires_at=self._session_expires_at)
                        # Start keepalive task after successful authentication
                        self._start_keepalive_task()
                    else:
                        self._connection_failures += 1
                        self.logger.error("Authentication failed", 
                                        status_code=response.status_code,
                                        response_text=response.text[:200])
                        raise Exception(f"Authentication failed: {response.status_code}")
                        
            except Exception as e:
                self._connection_failures += 1
                self._is_healthy = False
                self.logger.error("Authentication exception", 
                                error=str(e),
                                failure_count=self._connection_failures)
                raise
    
    async def _ensure_authenticated(self) -> httpx.Cookies:
        """Ensure we have valid authentication cookies, re-authenticating if necessary."""
        current_time = time.time()
        
        # Check if we need to authenticate or re-authenticate
        needs_auth = (
            self._cookies is None or 
            self._session_expires_at is None or 
            current_time >= self._session_expires_at - 600  # Re-auth 10 minutes before expiry
        )
        
        if needs_auth:
            self.logger.info("Session expired or missing, re-authenticating", 
                           has_cookies=self._cookies is not None,
                           expires_at=self._session_expires_at,
                           current_time=current_time)
            await self.authenticate()
        
        return self._cookies
    
    async def _handle_auth_failure(self, response: httpx.Response) -> bool:
        """Handle authentication failures by checking status codes and re-authenticating."""
        if response.status_code in [401, 403, 404, 500, 502, 503, 504]:
            self.logger.warning("Authentication/connectivity failure detected, invalidating session", 
                              status_code=response.status_code)
            # Clear session data to force re-authentication
            self._clear_session_state()
            return True
        return False
    
    async def _make_authenticated_request(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an authenticated request with automatic retry on auth failure."""
        max_retries = 2
        
        # Ensure timeout is set
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30.0
        
        for attempt in range(max_retries + 1):
            try:
                self._total_requests += 1
                
                # Always try to authenticate fresh if we're unhealthy
                if not self._is_healthy or self._cookies is None:
                    self.logger.info("Forcing fresh authentication due to unhealthy state")
                    await self.authenticate()
                
                cookies = await self._ensure_authenticated()
                
                response = await kodosumi_http_client.request(
                    client, method, url, cookies=cookies, **kwargs
                )
                
                # Check for auth failure
                if await self._handle_auth_failure(response):
                    if attempt < max_retries:
                        self.logger.info("Retrying request after auth failure", 
                                       attempt=attempt + 1, 
                                       url=url)
                        continue
                    else:
                        self.logger.error("Max auth retries exceeded", url=url)
                        response.raise_for_status()
                
                # Update health status on success
                self._last_successful_request = time.time()
                self._connection_failures = 0
                self._is_healthy = True
                self._successful_requests += 1
                
                return response
                
            except Exception as e:
                self._connection_failures += 1
                self._failed_requests += 1
                if self._connection_failures >= self._max_connection_failures:
                    self._is_healthy = False
                    self.logger.error("Connection marked as unhealthy", 
                                    failure_count=self._connection_failures,
                                    error=str(e))
                    # Start recovery process
                    self._start_recovery_task()
                
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 1.0  # Exponential backoff
                    self.logger.warning("Request failed, retrying", 
                                      attempt=attempt + 1,
                                      wait_time=wait_time,
                                      error=str(e))
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error("All request attempts failed", 
                                    url=url,
                                    error=str(e))
                    # If all attempts failed, try one more time with fresh auth
                    if isinstance(e, (httpx.TimeoutException, httpx.ConnectError)):
                        self.logger.info("Attempting final retry with fresh authentication")
                        self._clear_session_state()
                        await self.authenticate()
                        response = await kodosumi_http_client.request(
                            client, method, url, cookies=self._cookies, **kwargs
                        )
                        self._last_successful_request = time.time()
                        self._connection_failures = 0
                        self._is_healthy = True
                        self._successful_requests += 1
                        return response
                    raise
        
        # This should never be reached
        raise Exception("Unexpected end of retry loop")
    
    async def get_available_flows(self) -> List[Dict[str, Any]]:
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
                response = await self._make_authenticated_request(
                    client, "get", url, timeout=30.0
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
        async with httpx.AsyncClient() as client:
            response = await self._make_authenticated_request(
                client, "get",
                f"{self.base_url}{flow_path}",
                timeout=30.0
            )
            return response.json()
    
    async def launch_flow(self, flow_path: str, inputs: Dict[str, Any]) -> str:
        self.logger.info("Launching Kodosumi flow", 
                        flow_path=flow_path, 
                        input_keys=list(inputs.keys()),
                        full_url=f"{self.base_url}{flow_path}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await self._make_authenticated_request(
                    client, "post",
                    f"{self.base_url}{flow_path}",
                    json=inputs,
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
        self.logger.debug("Getting flow status", flow_path=flow_path, fid=fid)
        
        # Try the new API first, fall back to old API for compatibility
        async with httpx.AsyncClient() as client:
            try:
                # Try new API endpoint first
                new_api_url = f"{self.base_url}/outputs/status/{fid}"
                self.logger.debug("Trying new API endpoint", url=new_api_url)
                
                response = await self._make_authenticated_request(
                    client, "get", new_api_url, timeout=30.0
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
                
                response = await self._make_authenticated_request(
                    client, "get", old_api_url, timeout=30.0
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
    
    def _start_recovery_task(self) -> None:
        """Start the automatic recovery task if not already running."""
        if self._recovery_task is None or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(self._recovery_loop())
            self.logger.info("Started automatic connection recovery task")
    
    async def _recovery_loop(self) -> None:
        """Background task to automatically recover unhealthy connections."""
        while not self._is_healthy:
            try:
                await asyncio.sleep(self._recovery_backoff)
                self.logger.info("Attempting connection recovery", 
                               backoff_seconds=self._recovery_backoff)
                
                # Try to perform a health check
                await self._perform_health_check()
                
                if self._is_healthy:
                    self.logger.info("Connection recovery successful")
                    self._recovery_backoff = 1.0  # Reset backoff
                    break
                else:
                    # Increase backoff for next attempt
                    self._recovery_backoff = min(
                        self._recovery_backoff * 2, 
                        self._max_recovery_backoff
                    )
                    self.logger.warning("Connection recovery failed, will retry", 
                                      next_attempt_in=self._recovery_backoff)
                    
            except Exception as e:
                self.logger.error("Error in recovery loop", error=str(e))
                self._recovery_backoff = min(
                    self._recovery_backoff * 2, 
                    self._max_recovery_backoff
                )
                await asyncio.sleep(self._recovery_backoff)
    
    async def _perform_health_check(self) -> None:
        """Perform a health check by attempting to get flows."""
        try:
            # Always try fresh authentication for health check
            self._clear_session_state()
            await self.authenticate()
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await self._make_authenticated_request(
                    client, "get", f"{self.base_url}/flow", timeout=10.0
                )
                if response.status_code == 200:
                    self.logger.info("Health check successful")
                    self._is_healthy = True
                    self._connection_failures = 0
                    self._last_successful_request = time.time()
                    self._last_health_check = time.time()
                else:
                    self.logger.warning("Health check failed", status_code=response.status_code)
                    
        except Exception as e:
            self.logger.warning("Health check exception", error=str(e))
            # Mark as unhealthy but don't raise - let recovery continue
            self._is_healthy = False

    async def force_reconnect(self) -> None:
        """Force a fresh connection by clearing state and re-authenticating."""
        self.logger.info("Forcing reconnection to Kodosumi")
        self._clear_session_state()
        await self.authenticate()
        
    def _clear_session_state(self) -> None:
        """Clear session state to force fresh authentication on next request."""
        self.logger.info("Clearing session state to force re-authentication")
        self._cookies = None
        self._session_expires_at = None
    
    async def get_connection_health(self) -> Dict[str, Any]:
        """Get detailed connection health information."""
        current_time = time.time()
        session_time_remaining = 0
        
        if self._session_expires_at:
            session_time_remaining = max(0, self._session_expires_at - current_time)
        
        connection_uptime = current_time - self._connection_start_time
        success_rate = (self._successful_requests / self._total_requests * 100) if self._total_requests > 0 else 0
        
        return {
            "is_healthy": self._is_healthy,
            "connection_failures": self._connection_failures,
            "max_connection_failures": self._max_connection_failures,
            "last_successful_request": self._last_successful_request,
            "seconds_since_last_success": current_time - self._last_successful_request,
            "session_expires_at": self._session_expires_at,
            "session_time_remaining_seconds": session_time_remaining,
            "has_valid_session": self._cookies is not None,
            "recovery_task_running": self._recovery_task is not None and not self._recovery_task.done(),
            "recovery_backoff_seconds": self._recovery_backoff,
            "keepalive_task_running": self._keepalive_task is not None and not self._keepalive_task.done(),
            "keepalive_enabled": self._keepalive_enabled,
            "keepalive_interval_seconds": self._keepalive_interval,
            "connection_uptime_seconds": connection_uptime,
            "connection_uptime_hours": connection_uptime / 3600,
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "success_rate_percentage": round(success_rate, 2),
            "last_health_check": self._last_health_check,
            "seconds_since_last_health_check": current_time - self._last_health_check if self._last_health_check else None
        }
    
    def stop_recovery(self) -> None:
        """Stop the recovery task (useful for cleanup)."""
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()
            self.logger.info("Stopped connection recovery task")
    
    def _start_keepalive_task(self) -> None:
        """Start the keepalive task if not already running."""
        if self._keepalive_enabled and (self._keepalive_task is None or self._keepalive_task.done()):
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            self.logger.info("Started connection keepalive task", 
                           interval_seconds=self._keepalive_interval)
    
    async def _keepalive_loop(self) -> None:
        """Background task to keep the connection alive with periodic health checks."""
        while self._keepalive_enabled and self._is_healthy:
            try:
                await asyncio.sleep(self._keepalive_interval)
                
                # Only do keepalive if we're healthy and have a session
                if self._is_healthy and self._cookies is not None:
                    self.logger.debug("Performing keepalive health check")
                    await self._perform_health_check()
                    
            except asyncio.CancelledError:
                self.logger.info("Keepalive task cancelled")
                break
            except Exception as e:
                self.logger.warning("Keepalive check failed", error=str(e))
                # Don't break the loop, just log the error
                continue
    
    def stop_keepalive(self) -> None:
        """Stop the keepalive task."""
        self._keepalive_enabled = False
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            self.logger.info("Stopped connection keepalive task")
    
    def enable_keepalive(self, interval_seconds: int = 600) -> None:
        """Enable keepalive with custom interval."""
        self._keepalive_enabled = True
        self._keepalive_interval = interval_seconds
        self._start_keepalive_task()
        self.logger.info("Enabled connection keepalive", interval_seconds=interval_seconds)
    
    async def force_recovery(self) -> None:
        """Force immediate connection recovery by clearing state and re-authenticating."""
        self.logger.info("Forcing connection recovery")
        
        # Stop existing tasks
        self.stop_recovery()
        self.stop_keepalive()
        
        # Clear all state
        self._clear_session_state()
        self._connection_failures = 0
        self._is_healthy = True
        
        # Re-authenticate
        await self.authenticate()
        
        self.logger.info("Forced recovery completed")
    
    def cleanup(self) -> None:
        """Cleanup all background tasks."""
        self.stop_recovery()
        self.stop_keepalive()
        self.logger.info("Cleaned up all background tasks")