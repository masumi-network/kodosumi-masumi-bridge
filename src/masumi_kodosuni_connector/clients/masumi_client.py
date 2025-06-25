import asyncio
import time
import uuid
import hashlib
import structlog
from typing import Dict, Any, Optional
from masumi_kodosuni_connector.config.settings import settings

# Only import masumi if not in test mode
if not settings.masumi_test_mode:
    from masumi.config import Config
    from masumi.payment import Payment, Amount

logger = structlog.get_logger()


class MasumiPaymentStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


class MasumiClient:
    def __init__(self, flow_key: str):
        self.test_mode = settings.masumi_test_mode
        # Convert network to proper capitalization for masumi package
        network_lower = settings.network.lower()
        self.network = "Preprod" if network_lower == "preprod" else "Mainnet" if network_lower == "mainnet" else "Preprod"
        self.flow_key = flow_key
        self.agent_identifier = settings.get_agent_identifier(flow_key)
        self.seller_vkey = settings.get_agent_vkey(flow_key)
        self.payment_amount = int(settings.payment_amount)  # Convert to int as expected by Amount class
        self.payment_unit = settings.payment_unit
        
        if not self.agent_identifier:
            raise ValueError(f"No agent identifier configured for flow: {flow_key}")
        
        if not self.test_mode:
            self.config = Config(
                payment_service_url=settings.payment_service_url,
                payment_api_key=settings.payment_api_key
            )
            # Store active payment instances for monitoring
            self.payment_instances: Dict[str, Payment] = {}
        else:
            logger.info("Masumi client running in test mode - payments will be simulated")
    
    async def create_payment_request(
        self, 
        identifier_from_purchaser: str, 
        input_data: Dict[str, Any], 
        job_id: str
    ) -> Dict[str, Any]:
        """Create a payment request using the Masumi Payment service."""
        logger.info(f"Creating payment request for job {job_id}")
        
        if self.test_mode:
            # Simulate payment request creation matching masumi package format
            current_time = int(time.time())
            blockchain_identifier = f"test_block_{uuid.uuid4().hex[:12]}"
            input_hash = hashlib.md5(str(input_data).encode()).hexdigest()
            
            return {
                "data": {
                    "blockchainIdentifier": blockchain_identifier,
                    "payByTime": current_time + (12 * 60 * 60),  # 12 hours (as per masumi package)
                    "submitResultTime": current_time + (24 * 60 * 60),  # 24 hours
                    "unlockTime": current_time + (48 * 60 * 60),  # 48 hours
                    "externalDisputeUnlockTime": current_time + (72 * 60 * 60),  # 72 hours
                },
                "input_hash": input_hash
            }
        
        try:
            # Create amount object for the payment
            amount = Amount(amount=self.payment_amount, unit=self.payment_unit)
            
            # Create payment instance
            payment = Payment(
                agent_identifier=self.agent_identifier,
                amounts=[amount],
                config=self.config,
                identifier_from_purchaser=identifier_from_purchaser,
                input_data=input_data,
                network=self.network
            )
            
            # Store the payment instance for monitoring
            self.payment_instances[job_id] = payment
            
            # Create the payment request
            payment_request = await payment.create_payment_request()
            logger.info(f"Created payment request for job {job_id}: {payment_request['data']['blockchainIdentifier']}")
            
            # Add the input_hash from the payment instance to the response
            payment_request["input_hash"] = payment.input_hash
            print(f"DEBUG: Added input_hash to payment_request: {payment.input_hash}")
            
            return payment_request
            
        except Exception as e:
            logger.error(f"Failed to create payment request for job {job_id}: {str(e)}")
            raise
    
    async def start_payment_monitoring(self, job_id: str, callback) -> None:
        """Start monitoring payment status for a job."""
        if self.test_mode:
            # In test mode, simulate immediate payment confirmation after 5 seconds
            logger.info(f"Starting simulated payment monitoring for job {job_id}")
            
            async def simulate_payment():
                await asyncio.sleep(5)  # Simulate 5 second payment processing
                logger.info(f"Simulating payment confirmation for job {job_id}")
                await callback(f"test_payment_{job_id}")
            
            # Start the simulation task
            asyncio.create_task(simulate_payment())
            return
        
        if job_id not in self.payment_instances:
            raise ValueError(f"No payment instance found for job {job_id}")
        
        payment = self.payment_instances[job_id]
        logger.info(f"Starting payment monitoring for job {job_id}")
        
        try:
            await payment.start_status_monitoring(callback)
        except Exception as e:
            logger.error(f"Error starting payment monitoring for job {job_id}: {str(e)}")
            raise
    
    async def check_payment_status(self, job_id: str) -> Dict[str, Any]:
        """Check the current payment status for a job."""
        if self.test_mode:
            # In test mode, always return confirmed status
            return {
                "data": {
                    "status": "confirmed",
                    "payment_id": f"test_payment_{job_id}"
                }
            }
        
        if job_id not in self.payment_instances:
            raise ValueError(f"No payment instance found for job {job_id}")
        
        payment = self.payment_instances[job_id]
        
        try:
            status = await payment.check_payment_status()
            return status
        except Exception as e:
            logger.error(f"Error checking payment status for job {job_id}: {str(e)}")
            raise
    
    async def complete_payment(self, job_id: str, blockchain_identifier: str, result: Dict[str, Any]) -> None:
        """Complete the payment after successful job execution."""
        if self.test_mode:
            logger.info(f"Simulating payment completion for job {job_id}, blockchain_identifier {blockchain_identifier}")
            return
        
        if job_id not in self.payment_instances:
            raise ValueError(f"No payment instance found for job {job_id}")
        
        payment = self.payment_instances[job_id]
        logger.info(f"Completing payment {blockchain_identifier} for job {job_id}")
        
        try:
            await payment.complete_payment(blockchain_identifier, result)
            logger.info(f"Payment {blockchain_identifier} completed for job {job_id}")
        except Exception as e:
            logger.error(f"Error completing payment {blockchain_identifier} for job {job_id}: {str(e)}")
            raise
    
    def stop_payment_monitoring(self, job_id: str) -> None:
        """Stop payment monitoring and cleanup."""
        if self.test_mode:
            logger.info(f"Simulating stopping payment monitoring for job {job_id}")
            return
        
        if job_id in self.payment_instances:
            payment = self.payment_instances[job_id]
            payment.stop_status_monitoring()
            del self.payment_instances[job_id]
            logger.info(f"Stopped payment monitoring for job {job_id}")
    
    async def verify_payment(self, job_id: str) -> bool:
        """Verify if payment has been confirmed."""
        if self.test_mode:
            return True
        
        try:
            status_data = await self.check_payment_status(job_id)
            payment_status = status_data.get("data", {}).get("status", "")
            return payment_status == "confirmed"
        except Exception as e:
            logger.error(f"Error verifying payment for job {job_id}: {str(e)}")
            return False