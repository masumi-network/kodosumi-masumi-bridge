# Masumi Package Update to v0.1.35

## Changes Made

### 1. Updated requirements.txt
- Changed `masumi` to `masumi==0.1.35` for version pinning

### 2. Updated MasumiClient Constructor
**Changes in `/src/masumi_kodosuni_connector/clients/masumi_client.py`:**

#### Network Handling
- Added proper capitalization for network parameter
- Masumi package expects "Preprod" or "Mainnet" (not "preprod"/"mainnet")
- Added automatic conversion: `preprod` → `Preprod`, `mainnet` → `Mainnet`

#### Payment Amount Type
- Changed `self.payment_amount` from string to int
- Masumi `Amount` class expects integer values

#### Payment Creation
- Added `Amount` object creation with proper parameters
- Updated Payment constructor to include `amounts` parameter:
```python
# OLD:
payment = Payment(
    agent_identifier=self.agent_identifier,
    config=self.config,
    identifier_from_purchaser=identifier_from_purchaser,
    input_data=input_data,
    network=self.network
)

# NEW:
amount = Amount(amount=self.payment_amount, unit=self.payment_unit)
payment = Payment(
    agent_identifier=self.agent_identifier,
    amounts=[amount],
    config=self.config,
    identifier_from_purchaser=identifier_from_purchaser,
    input_data=input_data,
    network=self.network
)
```

### 3. Updated Payment Completion Method
**Method signature changed:**
- **OLD**: `complete_payment(payment_id: str, result: Dict[str, Any])`
- **NEW**: `complete_payment(blockchain_identifier: str, job_output: dict)`

Updated all calls to use `blockchain_identifier` instead of `payment_id`.

### 4. Fixed Agent Service Payment Completion
**In `/src/masumi_kodosuni_connector/services/agent_service.py`:**
- Fixed missing `MasumiClient` instance creation
- Added proper flow_key derivation for payment completion
- Added error handling for unconfigured agents

## API Changes Summary

### Payment Class Constructor
```python
Payment(
    agent_identifier: str,
    amounts: Optional[List[Amount]] = None,  # NEW: Required amounts list
    config: Config = None,
    network: str = 'Preprod',  # Expects proper capitalization
    preprod_address: Optional[str] = None,
    mainnet_address: Optional[str] = None,
    identifier_from_purchaser: str = 'default_purchaser_id',
    input_data: Optional[dict] = None
)
```

### Amount Class Constructor
```python
Amount(amount: int, unit: str)  # amount must be int, not string
```

### Method Changes
1. **start_status_monitoring**: Now accepts `interval_seconds: int = 60` parameter
2. **complete_payment**: Parameter changed from `payment_id` to `blockchain_identifier`
3. **check_payment_status**: Now accepts `limit: int = 10` parameter

## Configuration Updates Needed

### Environment Variables
No changes needed to environment variables, but ensure:
- `PAYMENT_AMOUNT` contains numeric values (will be converted to int)
- `NETWORK` can be `preprod` or `mainnet` (will be auto-capitalized)

### Agent Identifiers
No changes needed to agent identifier format.

## Testing

### Test the Update
1. **Install the new version:**
   ```bash
   pip install masumi==0.1.35
   ```

2. **Test import:**
   ```python
   from masumi_kodosuni_connector.clients.masumi_client import MasumiClient
   ```

3. **Test client creation:**
   ```python
   client = MasumiClient('your_flow_key')
   ```

### Compatibility
- ✅ Backward compatible with existing configuration
- ✅ Existing payment flow should work without changes
- ✅ Test mode functionality preserved
- ✅ All existing API endpoints remain functional

## Production Deployment

### For Docker Deployment
1. Rebuild Docker image to get new requirements
2. No configuration changes needed
3. Restart containers

### For Manual Deployment
1. Update requirements: `pip install -r requirements.txt`
2. Restart the service
3. Monitor logs for any issues

## Rollback Plan

If issues occur:
1. **Revert requirements.txt:** Change `masumi==0.1.35` back to `masumi==0.1.34`
2. **Revert code changes** in this commit
3. **Reinstall:** `pip install masumi==0.1.34`
4. **Restart service**

The changes are minimal and should not cause any breaking issues with existing functionality.