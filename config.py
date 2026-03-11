SERIAL_PORT = "ASRL4::INSTR"  # VISA resource name for STM32 board
BAUD_RATE = 115200            # Serial baud rate
TIMEOUT_MS = 2000             # Communication timeout in milliseconds

CHANNEL = 3 

REGISTER_MAP_PATH = "reference/PGA305 Control and Status Registers Map.csv"

# PGA305 I2C Addresses
# - 0x20: Runtime data (ADC values, compensated output)
# - 0x22: Control and Status registers
# - 0x25: EEPROM registers (Part Number, Serial Number, PRange)
PGA305_I2C_ADDR = 0x20 
EEPROM_ADDR = 0x25  

CM_COMMAND_DELAY = 2.5      # Delay after cm_ command (seconds) - STM32 needs 2+ seconds
I2C_RESET_DELAY = 1.0       # Delay after i2cr command (seconds)
CHANNEL_SWITCH_DELAY = 0.5  # Delay after changing multiplexer channel (seconds)

# Command mode retry configuration
CM_MAX_RETRIES = 5 