# payByTime Field Implementation

## ✅ CORRECTED: You were absolutely right!

Thank you for providing the masumi package source code! I was wrong in my investigation.

## 🔍 Corrected Investigation Results

**The `payByTime` field IS coming from the masumi pip package.**

### What the masumi package actually returns:
```python
# From masumi.payment.Payment.create_payment_request()
{
    "data": {
        "blockchainIdentifier": "...",
        "payByTime": "...",            # ✅ PROVIDED by masumi (12 hours default)
        "submitResultTime": "...",      # ✅ PROVIDED by masumi (24 hours default)
        "unlockTime": "...",           # ✅ PROVIDED by masumi  
        "externalDisputeUnlockTime": "..." # ✅ PROVIDED by masumi
    }
}
```

### From the masumi package source:
```python
# Set payByTime to 12 hours from now
pay_by_time = datetime.now(timezone.utc) + timedelta(hours=12)
pay_by_time_str = pay_by_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

# Set submitResultTime to 24 hours from now (after payByTime)
submit_result_time = datetime.now(timezone.utc) + timedelta(hours=24)
```

### What I corrected:
- **Extract field**: `payByTime = payment_data.get("payByTime")` (from masumi response)
- **Format handling**: Convert ISO timestamp to Unix timestamp if needed
- **Fallback**: Only calculate if somehow missing from masumi response

## 🛠️ Corrected Implementation

### In `mip003_service.py`:
```python
# Extract payByTime from Masumi payment response (masumi package provides this field)
pay_by_time = payment_data.get("payByTime")
if not pay_by_time:
    # Fallback: calculate as 1 hour before submitResultTime if somehow missing
    submit_result_time = int(payment_data["submitResultTime"])
    pay_by_time = submit_result_time - (60 * 60)
else:
    # Convert ISO format to timestamp if needed
    if isinstance(pay_by_time, str) and pay_by_time.endswith('Z'):
        from datetime import datetime
        pay_by_time = int(datetime.fromisoformat(pay_by_time.replace('Z', '+00:00')).timestamp())
    elif isinstance(pay_by_time, str):
        pay_by_time = int(pay_by_time)
```

### In test mode:
```python
return {
    "data": {
        "blockchainIdentifier": blockchain_identifier,
        "payByTime": current_time + (12 * 60 * 60),  # 12 hours (masumi default)
        "submitResultTime": current_time + (24 * 60 * 60),  # 24 hours
        "unlockTime": current_time + (48 * 60 * 60),  # 48 hours
        "externalDisputeUnlockTime": current_time + (72 * 60 * 60),  # 72 hours
    },
    "input_hash": input_hash
}
```

## 📋 Timeline Logic (Masumi Package Defaults)

```
Payment Created → payByTime (12h) → submitResultTime (24h) → unlockTime → externalDisputeUnlockTime
                    ↑                      ↑
                    |                      |
                 Pay deadline         Result deadline
                 (from masumi)        (from masumi)
                    |                      |
                    |------ 12 hours -----|
```

## ✅ Current Status

- **MIP-003 Compliant**: Includes required `payByTime` field
- **Extracted from Masumi**: Uses actual `payByTime` from masumi package
- **Masumi Defaults**: 12 hours to pay, 24 hours to submit results
- **Format Handling**: Converts ISO timestamps to Unix timestamps as needed
- **Fallback**: Only calculates if masumi somehow doesn't provide it

## 🎯 Example Response (Corrected)

```json
{
  "payByTime": "1750828575",           // FROM masumi package (12 hours)
  "submitResultTime": "1750871775",    // FROM masumi package (24 hours)
  "unlockTime": "1750958175",          // FROM masumi package
  "externalDisputeUnlockTime": "1751044575"  // FROM masumi package
}
```

Thank you for the correction! The implementation now properly uses the `payByTime` field provided by the masumi package, exactly as intended.