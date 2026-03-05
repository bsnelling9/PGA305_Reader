import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from pga305_reader import PGA305Reader

print("RAW PGA305 EEPROM DUMP")

# Initialize reader
reader = PGA305Reader()
reader.connect()

# Select channel and prepare for reading
print(f"\nChannel {config.CHANNEL}")
reader.set_channel(config.CHANNEL)
reader.reset_i2c()
reader.enter_command_mode(config.PGA305_EEPROM_ADDR)

# Read entire EEPROM page E (registers 0x70-0x7F)
print("\nEEPROM Page E (0x70-0x7F):")

eeprom_data = {}
for reg in range(0x70, 0x80):
    value = reader.read_register(reg, config.PGA305_EEPROM_ADDR)
    eeprom_data[reg] = value
    
    if value is not None:
        print(f"Register 0x{reg:02X} = 0x{value:02X} ({value})")
    else:
        print(f"Register 0x{reg:02X} = No response")

print("\n")
print("EEPROM INTERPRETATION")

# Show the key registers
print(f"\nPart Number Registers:")
print(f"  PN_LSB (0x70): 0x{eeprom_data.get(0x70, 0):02X}")
print(f"  PN_MID (0x71): 0x{eeprom_data.get(0x71, 0):02X}")
print(f"  PN_MSB (0x72): 0x{eeprom_data.get(0x72, 0):02X}")

pn_lsb = eeprom_data.get(0x70, 0) or 0
pn_mid = eeprom_data.get(0x71, 0) or 0
pn_msb = eeprom_data.get(0x72, 0) or 0
pn_msb_quotient = pn_msb // 128
pn_msb_remainder = pn_msb % 128
part_number_prefix = "A" if pn_msb_remainder == 0 else "S"
part_number_numeric = pn_lsb + (pn_mid << 8) + (pn_msb_quotient << 16)
part_number = part_number_prefix + str(part_number_numeric)
print(f"  → Part Number: {part_number}")

print(f"\nSerial Number Registers:")
print(f"  SN_LSB (0x73): 0x{eeprom_data.get(0x73, 0):02X}")
print(f"  SN_MID (0x74): 0x{eeprom_data.get(0x74, 0):02X}")
print(f"  SN_MSB (0x75): 0x{eeprom_data.get(0x75, 0):02X}")

sn = (eeprom_data.get(0x73, 0) or 0) + ((eeprom_data.get(0x74, 0) or 0) << 8) + ((eeprom_data.get(0x75, 0) or 0) << 16)
print(f"  → Serial Number: {sn}")

print(f"\nPRange Registers:")
print(f"  PRANGE_LSB (0x76): 0x{eeprom_data.get(0x76, 0):02X}")
print(f"  PRANGE_MSB (0x77): 0x{eeprom_data.get(0x77, 0):02X}")

prange = (eeprom_data.get(0x76, 0) or 0) + ((eeprom_data.get(0x77, 0) or 0) << 8)
print(f"  → PRange: {prange}")

# Check if data looks valid
print("\n" + "="*70)
print("DIAGNOSIS")
print("="*70)

valid_values = [v for v in eeprom_data.values() if v is not None]
if all(v == 0 for v in valid_values):
    print("\n✗ All registers are 0x00 - EEPROM is BLANK/UNPROGRAMMED")
elif all(v == 0xFF for v in valid_values):
    print("\n✗ All registers are 0xFF - EEPROM is ERASED")
else:
    print("\n✓ EEPROM contains data")

reader.disconnect()