import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from pga305_reader import PGA305Reader

print("="*70)
print("FULL REGISTER SCAN - Looking for NON-ZERO values")
print("="*70)

# Initialize reader
reader = PGA305Reader()
reader.connect()

# Select channel and prepare
reader.set_channel(config.CHANNEL)
reader.reset_i2c()
reader.enter_command_mode(config.PGA305_EEPROM_ADDR)

print(f"\nScanning ALL registers (0x00-0xFF) on channel {config.CHANNEL}...")
print("This may take a minute...\n")

non_zero_regs = []

for reg in range(0x00, 0x100):
    val = reader.read_register(reg, config.PGA305_EEPROM_ADDR)
    
    if val is not None and val != 0x00:
        print(f"Register 0x{reg:02X} = 0x{val:02X} ({val})")
        non_zero_regs.append((reg, val))
    
    # Progress indicator
    if reg % 16 == 15:
        print(f"  Scanned 0x00-0x{reg:02X}...", end='\r')

print("RESULTS")

if non_zero_regs:
    print(f"\nFound {len(non_zero_regs)} non-zero registers:")
    for reg, val in non_zero_regs:
        print(f"  0x{reg:02X} = 0x{val:02X} ({val})")
else:
    print("\n✗ ALL registers are 0x00!")
    print("\nPossible issues:")
    print("  1. PGA305 EEPROM is actually blank")
    print("  2. PGA305 needs different access sequence")
    print("  3. Wrong I2C address (check config.py)")
    print("  4. Sensor not connected to this channel")

reader.disconnect()