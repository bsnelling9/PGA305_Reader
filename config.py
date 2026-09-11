## NOTE: Clean this up a lot of the variables here are not needed anymore
SERIAL_PORT = "ASRL5::INSTR"  
BAUD_RATE = 115200            
TIMEOUT_MS = 2000             

CHANNEL = 1 

# T = normalized temperature ADC value
# P = normalized pressure ADC value
# All values are normalized by dividing by 2^(ADC_resolution - 2)
# ADC_resolution is 24
T_NORM = 4194304
P_NORM = 4194304

# PGA305 I2C Addresses
# - 0x20: Runtime data (ADC values, compensated output)
# - 0x22: Control and Status registers
# - 0x25: EEPROM registers (Part Number, Serial Number, PRange)
# I need to clean this up because they are part of the PGA305
PGA305_I2C_ADDR = 0x20
I2C_CONTROL = 0x22 
EEPROM_ADDR = 0x25  
COMPENSATION_CNTRL_ADDR = 0x0C
COMMAND_MODE = 0x03

CM_COMMAND_DELAY = 2.5   
I2C_RESET_DELAY = 1.0      
CHANNEL_SWITCH_DELAY = 0.5 
# Command mode retry configuration
CM_MAX_RETRIES = 5 

# Scan channels configuration
SCAN_NUM_CHANNELS = 1   # Number of channels to scan (0 to N-1)
SCAN_ITERATIONS = 2  # Number of times to repeat the full scan