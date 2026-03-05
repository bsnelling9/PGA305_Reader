SERIAL_PORT = "COM5"  # VISA resource name for STM32 board
BAUD_RATE = 115200             # Serial baud rate
TIMEOUT_MS = 2000              # Communication timeout in milliseconds


CHANNEL = 3  # Default multiplexer channel (0-7)

REGISTER_MAP_PATH = "reference/PGA305 Control and Status Registers Map.csv"

# PGA305 I2C Addresses
# The PGA305 uses different I2C addresses for different memory pages:
# - 0x20: Runtime data (ADC values, compensated output)
# - 0x22: Control and Status registers
# - 0x25: EEPROM registers (Part Number, Serial Number, PRange)
PGA305_EEPROM_ADDR = 0x25  # DO NOT CHANGE unless you know what you're doing