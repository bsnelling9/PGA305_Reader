import pyvisa
import time
import csv
import os
import config
from typing import Optional, Dict


class PGA305Reader:

    def __init__(self, serial_port=None, baud_rate=None, timeout_ms=None):
        self.serial_port = serial_port or config.SERIAL_PORT
        self.baud_rate = baud_rate or config.BAUD_RATE
        self.timeout_ms = timeout_ms or config.TIMEOUT_MS
        self.inst = None
        self.register_map = None

        if config.REGISTER_MAP_PATH and os.path.exists(config.REGISTER_MAP_PATH):
            self._load_register_map(config.REGISTER_MAP_PATH)

    def connect(self):
        rm = pyvisa.ResourceManager()
        max_retries = 3

        for attempt in range(max_retries):
            try:
                self.inst = rm.open_resource(self.serial_port)
                self.inst.baud_rate = self.baud_rate
                self.inst.timeout = self.timeout_ms
                return True
            except pyvisa.errors.VisaIOError as e:
                if "RSRC_BUSY" in str(e) and attempt < max_retries - 1:
                    print(f"Port busy, retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    raise
        return False

    def disconnect(self):
        if self.inst:
            self.inst.close()
            self.inst = None

    # --- Low-level commands ---

    def send_command(self, cmd: str) -> bytes:
        """Send command to STM32 and return raw response."""
        self.inst.write_raw((cmd + '\n').encode('ascii'))
        time.sleep(0.05)

        try:
            if self.inst.bytes_in_buffer > 0:
                return self.inst.read_bytes(self.inst.bytes_in_buffer)
            else:
                return self.inst.read_bytes(64)
        except:
            return b''

    def set_channel(self, channel: int):
        """Connect I2C relays to the given sensor slot."""
        self.send_command(f"mx2{channel:02X}")
        time.sleep(config.CHANNEL_SWITCH_DELAY)

    def disconnect_channel(self):
        """Disconnect all relays (I2C and DMM off)."""
        self.send_command("mx001")
        time.sleep(config.CHANNEL_SWITCH_DELAY)

    def reset_i2c(self):
        """Toggle I2C peripheral to clear bus errors."""
        self.send_command("i2cr")
        time.sleep(config.I2C_RESET_DELAY)

    def read_register(self, reg_addr: int, i2c_addr: int = None) -> Optional[int]:
        """Read a single 8-bit register from the PGA305."""
        if i2c_addr is None:
            i2c_addr = config.PGA305_I2C_ADDR

        raw = self.send_command(f"imr{i2c_addr:02X}{reg_addr:02X}")

        if len(raw) >= 2:
            try:
                return int(raw[0:2].decode('ascii'), 16)
            except:
                return None
        return None

    def get_board_identity(self) -> str:
        response = self.send_command("IDN")
        return response.decode('ascii', errors='ignore').strip()

    # --- PGA305 command mode ---

    def enter_command_mode(self, max_retries=None) -> bool:
        """
        Enter PGA305 digital interface (command) mode.
        Retry logic works around an STM32 firmware timing issue
        where the first I2C write in cm_ can silently fail.
        """
        if max_retries is None:
            max_retries = config.CM_MAX_RETRIES

        for attempt in range(max_retries):
            self.inst.write_raw(b'cm_20\n')
            time.sleep(config.CM_COMMAND_DELAY)

            try:
                if self.inst.bytes_in_buffer > 0:
                    response = self.inst.read_bytes(self.inst.bytes_in_buffer)
                else:
                    response = self.inst.read_bytes(64)
            except:
                response = b''

            # Check ACK then verify register 0x01 reads 0x03
            if len(response) >= 2 and response[0:2] == b'\x06\x0a':
                if self.read_register(0x01, config.PGA305_I2C_ADDR) == 0x03:
                    return True

            if attempt < max_retries - 1:
                self.reset_i2c()

        return False

    # --- Sensor data ---

    def read_sensor_data(self, channel: int, verbose=True) -> Optional[Dict]:
        """Read Part Number, Serial Number, and PRange from a PGA305 sensor."""
        if verbose:
            print(f"\nReading channel {channel}...")

        self.set_channel(channel)

        if not self.enter_command_mode():
            if verbose:
                print("ERROR: Could not enter command mode")
                print("  Try power cycling the board")
            return None

        if verbose:
            print("Command mode active")

        # Register addresses (from CSV or hardcoded fallback)
        if self.register_map:
            pn_addrs = [self.register_map.get(f'EEPROM_ARRAY PN_{s}', d)
                        for s, d in [('LSB', 0x70), ('MID', 0x71), ('MSB', 0x72)]]
            sn_addrs = [self.register_map.get(f'EEPROM_ARRAY SN_{s}', d)
                        for s, d in [('LSB', 0x73), ('MID', 0x74), ('MSB', 0x75)]]
            pr_addrs = [self.register_map.get(f'EEPROM_ARRAY PRANGE_{s}', d)
                        for s, d in [('LSB', 0x76), ('MSB', 0x77)]]
        else:
            pn_addrs = [0x70, 0x71, 0x72]
            sn_addrs = [0x73, 0x74, 0x75]
            pr_addrs = [0x76, 0x77]

        # Read Part Number
        pn_bytes = [self.read_register(a, config.EEPROM_ADDR) for a in pn_addrs]
        if None in pn_bytes:
            if verbose:
                print("ERROR: Failed to read Part Number")
            self.disconnect_channel()
            return None

        pn_lsb, pn_mid, pn_msb = pn_bytes
        prefix = "A" if (pn_msb % 128) == 0 else "S"
        pn_numeric = pn_lsb + (pn_mid << 8) + ((pn_msb // 128) << 16)
        part_number = prefix + str(pn_numeric)

        # Read Serial Number
        sn_bytes = [self.read_register(a, config.EEPROM_ADDR) for a in sn_addrs]
        if None in sn_bytes:
            if verbose:
                print("ERROR: Failed to read Serial Number")
            self.disconnect_channel()
            return None

        serial_number = sn_bytes[0] + (sn_bytes[1] << 8) + (sn_bytes[2] << 16)

        # Read PRange
        pr_bytes = [self.read_register(a, config.EEPROM_ADDR) for a in pr_addrs]
        if None in pr_bytes:
            prange = None
        else:
            prange = pr_bytes[0] + (pr_bytes[1] << 8)

        self.disconnect_channel()

        return {
            'part_number': part_number,
            'serial_number': serial_number,
            'prange': prange
        }

    # --- Register map loader ---

    def _load_register_map(self, csv_path: str) -> bool:
        if not os.path.exists(csv_path):
            return False

        self.register_map = {}
        try:
            with open(csv_path, 'r') as f:
                for row in csv.DictReader(f):
                    name = row.get('REGISTER NAME', '').strip()
                    offset_str = row.get('DI Offset Address', '').strip()
                    if name and offset_str:
                        try:
                            self.register_map[name] = int(offset_str, 0)
                        except ValueError:
                            pass
            return len(self.register_map) > 0
        except:
            return False