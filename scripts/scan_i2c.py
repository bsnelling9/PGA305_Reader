import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyvisa
import time

SERIAL_PORT = "ASRL5::INSTR"
BAUD_RATE = 115200
TIMEOUT_MS = 2000
CHANNEL = 3

rm = pyvisa.ResourceManager()
inst = rm.open_resource(SERIAL_PORT)
inst.baud_rate = BAUD_RATE
inst.timeout = TIMEOUT_MS

def send_command(cmd: str):
    """Send command and return raw response"""
    cmd_bytes = (cmd + '\n').encode('ascii')
    inst.write_raw(cmd_bytes)
    time.sleep(0.05)
    
    try:
        if inst.bytes_in_buffer > 0:
            return inst.read_bytes(inst.bytes_in_buffer)
        else:
            return inst.read_bytes(64)
    except:
        return b''

# Select channel
print("Setting channel 3...")
response = send_command("mx303")
print(f"Channel select response: {response.hex()}")
time.sleep(0.2)

print("\n" + "="*70)
print("I2C ADDRESS SCANNER")
print("="*70)
print("\nScanning I2C addresses 0x00 to 0x7F...")
print("Testing register 0x01 read for each address\n")

found_devices = []

for addr in range(0x00, 0x80):
    # Try to read register 0x01 from this address
    cmd = f"imr{addr:02X}01"
    raw = send_command(cmd)
    
    if len(raw) > 0:
        val = raw[0]
        # Error codes: 30 (0x1E) = I2C failed, 15 (0x0F) = command error
        if val != 0x1E and val != 0x0F:
            print(f"  0x{addr:02X}: Response = 0x{val:02X} ✓ DEVICE FOUND!")
            found_devices.append((addr, val))
        elif addr % 16 == 0:
            print(f"  0x{addr:02X} - 0x{addr+15:02X}: No response...", end='\r')
    
    time.sleep(0.01)

print("\n\n" + "="*70)
print("SCAN RESULTS")
print("="*70)

if found_devices:
    print(f"\nFound {len(found_devices)} device(s):\n")
    for addr, val in found_devices:
        print(f"  I2C Address: 0x{addr:02X}")
        print(f"  Register 0x01 value: 0x{val:02X}")
        print()
    
    print("="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\nUpdate your Python code to use the correct I2C address:")
    for addr, _ in found_devices:
        print(f"  PGA305_I2C_ADDR = 0x{addr:02X}")
else:
    print("\nNo I2C devices found!")
    print("\nPossible issues:")
    print("  1. PGA305 not powered")
    print("  2. I2C wiring problem")
    print("  3. Wrong channel selected")
    print("  4. PGA305 in wrong mode (might need 'command mode' first)")
    print("\nTrying to put PGA305 in command mode...")
    
    # Try command mode for address 0x50
    print("\nSending command mode for I2C address 0x50...")
    response = send_command("cm_50")
    print(f"Command mode response: {response.hex()}")
    time.sleep(0.1)
    
    # Try reading again
    print("\nRetrying read after command mode...")
    cmd = "imr5001"
    raw = send_command(cmd)
    if len(raw) > 0:
        val = raw[0]
        print(f"Register 0x01 = 0x{val:02X}")
        if val != 0x1E and val != 0x0F:
            print("✓ PGA305 responded! It needed command mode first.")
        else:
            print("✗ Still no response. Check hardware connections.")

inst.close()
print("\nDone.")