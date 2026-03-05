# PGA305 Sensor Reader

Python tool for reading Part Number, Serial Number, and PRange from PGA305 pressure sensors via STM32 I2C bridge.

## Features

- Read sensor data (Part Number, Serial Number, PRange)
- Scan all channels for programmed sensors
- I2C address scanning and diagnostics
- EEPROM register dump
- Full register scan
- STM32 command discovery

## Requirements

- Python 3.8+ (32-bit) - Required for NI-VISA compatibility
- NI-VISA Runtime
- STM32 board with PGA305 multiplexer

## Setup

**Important:** Must use 32-bit Python for NI-VISA compatibility.
```bash
# Verify 32-bit Python
python -c "import struct; print('32-bit' if struct.calcsize('P') == 4 else '64-bit')"

# Create virtual environment
python -m venv .venv

# Activate (Git Bash)
source .venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config.py`:
```python
SERIAL_PORT = "ASRL5::INSTR"  # Your COM port
BAUD_RATE = 115200
CHANNEL = 3                    # Default channel (0-7)
```

## Usage
```bash
# Interactive menu
python main.py

# Direct scripts
python scripts/scan_channels.py
python scripts/scan_i2c.py
python scripts/dump_eeprom.py
```

## Project Structure
```
PGA305_Reader/
├── main.py              # Interactive menu
├── pga305_reader.py     # Core library
├── config.py            # Configuration
├── requirements.txt     # Dependencies
└── scripts/             # Diagnostic tools
```

## Troubleshooting

**Wrong Python version:**
```bash
python -c "import struct; print('32-bit' if struct.calcsize('P') == 4 else '64-bit')"
```
Must show "32-bit". Download 32-bit Python from python.org.

**Port busy:**
Close other programs using the port, then unplug/replug USB.

## Technical Details

PGA305 I2C addresses (I2CADDR pin = 1):
- 0x20 - Runtime data
- 0x22 - Control registers
- 0x25 - EEPROM (Part Number, Serial, PRange)

Part numbers: A##### or S##### format
Serial numbers: 24-bit integers (0 to 16,777,215)
