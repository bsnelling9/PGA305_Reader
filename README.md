PGA305 Sensor Reader
Python tool for reading Part Number, Serial Number, and PRange from PGA305 pressure sensors via STM32 I2C bridge.
Features:
 Read sensor data (Part Number, Serial Number, PRange)
 Scan all channels for programmed sensors
 I2C address scanning and diagnostics
 EEPROM register dump
 Full register scan
 STM32 command discovery

Requirements

Python 3.8+ (32-bit) - Required for NI-VISA compatibility
NI-VISA Runtime
STM32 board with PGA305 multiplexer

Important: You MUST install the 32-bit version for NI-VISA compatibility, even on 64-bit Windows.
To verify you have 32-bit Python:
bashpython -c "import struct; print('32-bit' if struct.calcsize('P') == 4 else '64-bit')"
2. Create Virtual Environment (32-bit)
CRITICAL: You must use 32-bit Python for NI-VISA compatibility!
Windows:

bash# Navigate to project directory
cd path\to\PGA305_Reader

# Verify you have 32-bit Python
python -c "import struct; print('32-bit' if struct.calcsize('P') == 4 else '64-bit')"
# Must show "32-bit"

# Create 32-bit virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/Scripts/activate

# Activate virtual environment
deactivate

# Verify venv is 32-bit
python -c "import struct; print('32-bit' if struct.calcsize('P') == 4 else '64-bit')"

To run the script:
python main.py