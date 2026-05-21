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

    def write_then_read_sequential(self, write_reg: int, write_val: int, i2c_addr: int, read_reg: int, read_count: int) -> Optional[list]:
        write_cmd = f"imw{i2c_addr:02X}{write_reg:02X}{write_val:02X}"
        read_cmds = [f"imr{i2c_addr:02X}{read_reg + i:02X}" for i in range(read_count)]
        full_cmd = "\\".join([write_cmd] + read_cmds)

        self.inst.write_raw((full_cmd + '\n').encode('ascii'))
        time.sleep(0.15)
        if self.inst.bytes_in_buffer > 0:
            self.inst.read_bytes(self.inst.bytes_in_buffer)

        self.inst.write_raw((full_cmd + '\n').encode('ascii'))
        time.sleep(0.15)
        raw = self.inst.read_bytes(self.inst.bytes_in_buffer)

        try:
            response_str = raw.decode('ascii', errors='ignore').strip()
            parts = [p.strip() for p in response_str.replace('\\', '\n').split() if len(p.strip()) == 2]
            if len(parts) >= read_count:
                return [int(p, 16) for p in parts[-read_count:]]
        except Exception:
            return None
        return None

    def read_registers_sequentially(self, start_reg: int, count: int, i2c_addr: int = None) -> Optional[list]:
        if i2c_addr is None:
            i2c_addr = config.PGA305_I2C_ADDR

        cmd_list = [f"imr{i2c_addr:02X}{start_reg + i:02X}" for i in range(count)]
        full_cmd = "\\".join(cmd_list)
        
        self.inst.write_raw((full_cmd + '\n').encode('ascii'))
        time.sleep(0.15)
        if self.inst.bytes_in_buffer > 0:
            self.inst.read_bytes(self.inst.bytes_in_buffer)

        self.inst.write_raw((full_cmd + '\n').encode('ascii'))
        time.sleep(0.15)
        raw = self.inst.read_bytes(self.inst.bytes_in_buffer)

        try:
            response_str = raw.decode('ascii', errors='ignore').strip()
            parts = [p.strip() for p in response_str.replace('\\', '\n').split() if len(p.strip()) == 2]
            if len(parts) >= count:
                return [int(p, 16) for p in parts[:count]]
        except Exception:
            return None
        return None

    def send_command(self, cmd: str) -> bytes:
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
        self.send_command(f"mx2{channel:02X}")
        time.sleep(config.CHANNEL_SWITCH_DELAY)

    def disconnect_channel(self):
        self.send_command("mx001")
        time.sleep(config.CHANNEL_SWITCH_DELAY)

    def reset_i2c(self):
        self.send_command("i2cr")
        time.sleep(config.I2C_RESET_DELAY)

    def read_register(self, reg_addr: int, i2c_addr: int = None) -> Optional[int]:
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

    def read_dig_if_ctrl(self) -> Optional[int]:
        # I2C address for page 0x2 = 0x40 + 0x02 = 0x42
        value = self.read_register(0x06, config.I2C_CONTROL)
        if value is not None:
            print(f"DIG_IF_CTRL (0x22/0x06) = 0x{value:02X} ({value:08b})")
            print(f"  OWI_XCVR_EN (bit 3): {(value >> 3) & 1}")
            print(f"  OWI_EN      (bit 2): {(value >> 2) & 1}")
            print(f"  I2C_EN      (bit 1): {(value >> 1) & 1}")
            print(f"  SPI_EN      (bit 0): {value & 1}")
        return value

    def write_register(self, reg_addr: int, value: int, i2c_addr: int) -> bool:
        
        response = self.send_command(f"imw{i2c_addr:02X}{reg_addr:02X}{value:02X}")
        
        return len(response) > 0 and response[0] == 6

    def enter_command_mode(self, max_retries=None) -> bool:
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

            if len(response) >= 2 and response[0:2] == b'\x06\x0a':
                if self.read_register(0x01, config.PGA305_I2C_ADDR) == 0x03:
                    return True

            if attempt < max_retries - 1:
                self.reset_i2c()

        return False


    def read_sensor_data(self, channel: int, verbose=True) -> Optional[Dict]:
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

        comp_ctrl = self.read_register(0x0C, config.PGA305_I2C_ADDR)
        print(f"COMPENSATION_CONTROL (0x20/0x0C): 0x{comp_ctrl:02X}")
        print(f"  IF_SEL      (bit 1): {(comp_ctrl >> 1) & 1}")
        print(f"  MICRO_RESET (bit 0): {comp_ctrl & 1}")
               

        self.read_dig_if_ctrl()

        owi_int_check = self.read_register(0x0B, config.I2C_CONTROL)
        print(f"OWI_INTERRUPT_EN (0x22/0x0B) = 0x{owi_int_check:02X} — OWI_INT_EN: {owi_int_check & 1}")

        dlpwr_check = self.read_register(0x54, config.I2C_CONTROL)
        print(f"DLPWR            (0x22/0x54) = 0x{dlpwr_check:02X} — OWI_CLK_EN: {dlpwr_check & 1}")

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

        pn_bytes = [self.read_register(a, config.EEPROM_ADDR) for a in pn_addrs]
        if None in pn_bytes:
            if verbose:
                print("ERROR: Failed to read Part Number")
            self.disconnect_channel()
            return None

        pn_lsb, pn_mid, pn_msb = pn_bytes

        print(f"DEBUG [Ch {channel}]: pn_lsb={hex(pn_lsb)}, pn_mid={hex(pn_mid)}, pn_msb={hex(pn_msb)}")

        prefix = "A" if (pn_msb % 128) == 0 else "S"
        pn_numeric = pn_lsb + (pn_mid << 8) + ((pn_msb // 128) << 16)
        part_number = prefix + str(pn_numeric)

        sn_bytes = [self.read_register(a, config.EEPROM_ADDR) for a in sn_addrs]
        if None in sn_bytes:
            if verbose:
                print("ERROR: Failed to read Serial Number")
            self.disconnect_channel()
            return None

        serial_number = sn_bytes[0] + (sn_bytes[1] << 8) + (sn_bytes[2] << 16)

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