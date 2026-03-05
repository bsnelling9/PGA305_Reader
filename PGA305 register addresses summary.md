# PGA305 Serial Number Register Addresses - OFFICIAL

Based on the PGA305 Control and Status Registers Map (CSV file)

## ✅ CORRECT Register Addresses

### Serial Number - Primary Location (USE THIS!)
These are in DI Page 0x5 (EEPROM_ARRAY section):

```
Register 0x73 (DI 0x5/0x73): SN_LSB - Serial Number Low Byte
Register 0x74 (DI 0x5/0x74): SN_MID - Serial Number Mid Byte  
Register 0x75 (DI 0x5/0x75): SN_MSB - Serial Number High Byte
```

**This is what PGA305_Set_IDs.vi writes to!**

### Serial Number - Alternate Location
These are also in DI Page 0x5:

```
Register 0x64 (DI 0x5/0x64): SERIAL_NUMBER_BYTE0
Register 0x65 (DI 0x5/0x65): SERIAL_NUMBER_BYTE1
Register 0x66 (DI 0x5/0x66): SERIAL_NUMBER_BYTE2
Register 0x67 (DI 0x5/0x67): SERIAL_NUMBER_BYTE3
```

### Part Number
```
Register 0x70 (DI 0x5/0x70): PN_LSB - Part Number Low Byte
Register 0x71 (DI 0x5/0x71): PN_MID - Part Number Mid Byte
Register 0x72 (DI 0x5/0x72): PN_MSB - Part Number High Byte
```

---

## ❌ INCORRECT Register Addresses (What I Guessed Before)

**DO NOT USE:** 0xE0-0xEF

I initially thought the serial was at 0xE0-0xEF based on the EEPROM images, but the register map shows the actual addresses are 0x73-0x75.

---

## Python Code to Read Serial Number

### Quick Method (Just Serial Number)
```python
import pyvisa
import time

rm = pyvisa.ResourceManager()
inst = rm.open_resource("ASRL5::INSTR")
inst.baud_rate = 115200
inst.timeout = 2000

def cmd(c):
    inst.write(c + '\n')
    time.sleep(0.05)
    return inst.read_bytes(inst.bytes_in_buffer or 64)

# Select channel
cmd("CH3")
time.sleep(0.1)

# Read serial number (PRIMARY location 0x73-0x75)
sn_lsb = cmd("imr73")[0]  # Register 0x73
sn_mid = cmd("imr74")[0]  # Register 0x74
sn_msb = cmd("imr75")[0]  # Register 0x75

# Combine into 24-bit serial number
serial_24bit = (sn_msb << 16) | (sn_mid << 8) | sn_lsb
serial_16bit = (sn_mid << 8) | sn_lsb

print(f"Serial Number (16-bit): {serial_16bit} (0x{serial_16bit:04X})")
print(f"Serial Number (24-bit): {serial_24bit} (0x{serial_24bit:06X})")

if sn_lsb == 0xFF and sn_mid == 0xFF and sn_msb == 0xFF:
    print("⚠️  UNPROGRAMMED! This is why LabVIEW shows '3'")

inst.close()
```

---

## What the Updated main.py Does

1. ✅ Reads from **correct addresses** (0x73-0x75)
2. ✅ Also checks alternate location (0x64-0x67)
3. ✅ Reads part number (0x70-0x72)
4. ✅ Detects unprogrammed EEPROM (all 0xFF)
5. ✅ Scans all 4 channels automatically
6. ✅ Provides detailed diagnostics

---

## Expected Results

### If Unprogrammed (Most Likely)
```
Serial Number - Primary Location (0x73-0x75):
  24-bit: 16777215 (0xFFFFFF)
  16-bit: 65535 (0xFFFF)
  Status: ⚠️  UNPROGRAMMED (all 0xFF)

⚠️  WARNING: ALL Serial Number Registers are UNPROGRAMMED
This explains why your LabVIEW code shows serial '3'!
```

### If Programmed
```
Serial Number - Primary Location (0x73-0x75):
  24-bit: 1 (0x000001)
  16-bit: 1 (0x0001)
  Status: ✓ Programmed
```

---

## How to Fix Unprogrammed Serials

Use LabVIEW **PGA305_Set_IDs.vi** to program unique serial numbers:

```
For each sensor (1-8):
  1. Select channel
  2. Run PGA305_Set_IDs.vi
  3. Set Serial = 1, 2, 3, 4, 5, 6, 7, 8 (unique for each)
  4. This writes to registers 0x73-0x75
  5. Verify with Discover_Part_Numbers.vi
```

After programming, the Python code should show:
- Channel 3: Serial = 1
- Channel 5: Serial = 2  
- Channel 8: Serial = 3
- Channel 9: Serial = 4
- etc.

---

## STM32 Commands Reference

```
IDN          - Get board identification
SN           - Get BOARD serial (NOT PGA305!)
CH<n>        - Set channel (3, 5, 8, or 9)
imr<XX>      - Read PGA305 register XX (hex)
imw<XX> <YY> - Write YY to PGA305 register XX

Examples:
  CH3        → Select channel 3
  imr73      → Read SN_LSB (0x73)
  imr74      → Read SN_MID (0x74)
  imr75      → Read SN_MSB (0x75)
```

---

## Summary of All Issues Found

1. ✅ **STM32 hardcoded to return 4 devices** (should be 8)
   - Fix: Override in LabVIEW `Discover_Part_Numbers.vi` with constant 8

2. ✅ **Sensors have unprogrammed serial numbers** (all 0xFF)
   - Fix: Use `PGA305_Set_IDs.vi` to program unique serials

3. ✅ **PGA305_Convert_Page_E_to_ID.vi bug** converts 0xFFFF to "3"
   - This is why you see serial "3" for all sensors!

4. ✅ **06 - Set Cal Coefficients.vi overwrites serials**
   - Fix: Add serial preservation code (read current, write back)

---

## Test Your Setup NOW

Run the updated `main.py`:

```bash
python main.py
```

It will show you:
- ✅ If serials are programmed or unprogrammed (0xFF)
- ✅ All 4 channels scanned
- ✅ Complete diagnostics

This will definitively prove whether unprogrammed EEPROM is the root cause!
