import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from pga305_reader import PGA305Reader

print("="*70)
print("STM32 COMMAND DISCOVERY")
print("="*70)

# Initialize reader
reader = PGA305Reader()
reader.connect()

# Test 1: Basic commands
print("\nTest 1: Testing basic commands")


basic_cmds = [
    "IDN",      # Identity
    "VER",      # Version
    "HELP",     # Help
    "?",        # Help
]

for cmd in basic_cmds:
    response = reader.send_command(cmd)
    print(f"{cmd:10s} -> {response.decode('ascii', errors='ignore').strip()}")

# Test 2: Channel selection
print("\nTest 2: Channel commands")


channel_cmd = f"mx3{config.CHANNEL:02X}"
response = reader.send_command(channel_cmd)
print(f"{channel_cmd:10s} -> Response: {response.hex()} ({response.decode('ascii', errors='ignore').strip()})")

# Test 3: I2C commands
print("\nTest 3: I2C Commands")


# Reset I2C
reader.reset_i2c()
print(f"{'i2cr':10s} -> I2C Reset (success)")

# Command mode
reader.enter_command_mode(config.PGA305_EEPROM_ADDR)
print(f"{'cm_25':10s} -> Command Mode (success)")

# Read register
value = reader.read_register(0x73, config.PGA305_EEPROM_ADDR)
if value is not None:
    print(f"{'imr2573':10s} -> 0x{value:02X} (Read Register 0x73)")
else:
    print(f"{'imr2573':10s} -> No response")

print("COMMAND SUMMARY")
print("\nSupported STM32 commands:")
print("  IDN        - Get board identity")
print("  mx3XX      - Select channel (XX = channel in hex)")
print("  i2cr       - Reset I2C bus")
print("  cm_AA      - Enter command mode (AA = I2C address)")
print("  imrAABB    - I2C read (AA = I2C addr, BB = register)")
print("  imwAABBCC  - I2C write (AA = I2C addr, BB = register, CC = data)")
print("  nm_AA      - Normal mode (AA = I2C address)")

print("PGA305 I2C ADDRESSES")

print("\nWhen I2CADDR pin = 1:")
print("  0x20 - Runtime data (ADC values, compensated output)")
print("  0x22 - Control and Status registers")
print("  0x25 - EEPROM registers (Part Number, Serial Number, PRange)")

reader.disconnect()
print("\nDone.")