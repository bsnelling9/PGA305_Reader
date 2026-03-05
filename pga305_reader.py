import pyvisa
import time
import csv
import os
import config
from typing import Optional, Dict


class PGA305Reader:
    """Class for reading PGA305 sensor data via STM32 I2C bridge"""
    
    def __init__(self, serial_port: str = None, baud_rate: int = None, timeout_ms: int = None):
        """
        Initialize PGA305 reader
        
        Args:
            serial_port: VISA resource name (default: from config.py)
            baud_rate: Serial baud rate (default: from config.py)
            timeout_ms: Communication timeout in milliseconds (default: from config.py)
        """
        # Load from config.py if not provided
        self.serial_port = serial_port or config.SERIAL_PORT
        self.baud_rate = baud_rate or config.BAUD_RATE
        self.timeout_ms = timeout_ms or config.TIMEOUT_MS
        self.inst = None
        
        # Automatically load register map
        self.register_map = None
        if config.REGISTER_MAP_PATH and os.path.exists(config.REGISTER_MAP_PATH):
            self._load_register_map(config.REGISTER_MAP_PATH)
        
    def connect(self):
        """Open serial connection to STM32 board"""
        rm = pyvisa.ResourceManager()
        
        # Try to open with retry if port is busy
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
                    print("\nERROR: Cannot open serial port!")
                    print("Possible causes:")
                    print("  - Another program is using the port")
                    print("  - Previous Python instance still running")
                    print("Solutions:")
                    print("  1. Close all programs using the port")
                    print("  2. Unplug and replug the USB cable")
                    raise
        return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.inst:
            self.inst.close()
            self.inst = None
    
    def _load_register_map(self, csv_path: str) -> bool:
        """
        Load PGA305 register definitions from CSV file (private method)
        
        Args:
            csv_path: Path to register map CSV
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if not os.path.exists(csv_path):
            return False
        
        self.register_map = {}
        
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    reg_name = row.get('REGISTER NAME', '').strip()
                    di_offset = row.get('DI Offset Address', '').strip()
                    
                    if reg_name and di_offset:
                        try:
                            offset = int(di_offset, 16) if di_offset.startswith('0x') else int(di_offset, 0)
                            self.register_map[reg_name] = offset
                        except:
                            pass
            
            return len(self.register_map) > 0
        except:
            return False
    
    def send_command(self, cmd: str) -> bytes:
        """
        Send command to STM32 and return raw response
        
        Args:
            cmd: Command string (without newline)
            
        Returns:
            Raw response bytes
        """
        cmd_bytes = (cmd + '\n').encode('ascii')
        self.inst.write_raw(cmd_bytes)
        time.sleep(0.05)
        
        try:
            if self.inst.bytes_in_buffer > 0:
                return self.inst.read_bytes(self.inst.bytes_in_buffer)
            else:
                return self.inst.read_bytes(64)
        except:
            return b''
    
    def set_channel(self, channel: int):
        """
        Select multiplexer channel
        
        Args:
            channel: Channel number (0-7)
        """
        # Command format: mx3XX where 3 = enable both relays, XX = channel in hex
        cmd = f"mx3{channel:02X}"
        response = self.send_command(cmd)
        time.sleep(0.1)
        
        if response[0:1] != b'\x06':  # ACK
            print(f"WARNING: Channel select may have failed (response: {response.hex()})")
    
    def reset_i2c(self):
        """Reset I2C bus (clears stuck state from previous sensor)"""
        self.send_command("i2cr")
        time.sleep(0.2)
    
    def enter_command_mode(self, i2c_addr: int = 0x25):
        """
        Put PGA305 into command mode
        
        Args:
            i2c_addr: I2C address for command mode (default: 0x25 for EEPROM)
        """
        cmd = f"cm_{i2c_addr:02X}"
        self.send_command(cmd)
        time.sleep(0.1)
    
    def read_register(self, reg_addr: int, i2c_addr: int = 0x25) -> Optional[int]:
        """
        Read single PGA305 register
        
        Args:
            reg_addr: Register address (8-bit)
            i2c_addr: I2C slave address (default: 0x25 for EEPROM page)
            
        Returns:
            Register value (0-255) or None if read failed
        """
        # STM32 command format: imrAABB
        # where AA = I2C slave address (hex, 2 digits)
        # where BB = Register address (hex, 2 digits)
        cmd = f"imr{i2c_addr:02X}{reg_addr:02X}"
        raw = self.send_command(cmd)
        
        if len(raw) >= 2:
            # STM32 returns ASCII hex string (2 characters)
            # e.g., "1E" is returned as bytes 0x31 0x45 (ASCII "1E")
            try:
                hex_str = raw[0:2].decode('ascii')
                value = int(hex_str, 16)
                return value
            except:
                return None
        return None
    
    def read_sensor_data(self, channel: int) -> Optional[Dict[str, any]]:
        """
        Read Part Number, Serial Number, and PRange from PGA305 sensor
        
        Args:
            channel: Multiplexer channel number (0-7)
            
        Returns:
            Dictionary with 'part_number', 'serial_number', 'prange' or None if failed
        """
        # Reset I2C and select channel
        self.reset_i2c()
        self.set_channel(channel)
        
        # Enter command mode for EEPROM access
        self.enter_command_mode(0x25)
        
        # Get register addresses (use register map if available, otherwise hardcoded)
        if self.register_map:
            pn_lsb_addr = self.register_map.get('EEPROM_ARRAY PN_LSB', 0x70)
            pn_mid_addr = self.register_map.get('EEPROM_ARRAY PN_MID', 0x71)
            pn_msb_addr = self.register_map.get('EEPROM_ARRAY PN_MSB', 0x72)
            
            sn_lsb_addr = self.register_map.get('EEPROM_ARRAY SN_LSB', 0x73)
            sn_mid_addr = self.register_map.get('EEPROM_ARRAY SN_MID', 0x74)
            sn_msb_addr = self.register_map.get('EEPROM_ARRAY SN_MSB', 0x75)
            
            prange_lsb_addr = self.register_map.get('EEPROM_ARRAY PRANGE_LSB', 0x76)
            prange_msb_addr = self.register_map.get('EEPROM_ARRAY PRANGE_MSB', 0x77)
        else:
            pn_lsb_addr, pn_mid_addr, pn_msb_addr = 0x70, 0x71, 0x72
            sn_lsb_addr, sn_mid_addr, sn_msb_addr = 0x73, 0x74, 0x75
            prange_lsb_addr, prange_msb_addr = 0x76, 0x77
        
        # Read Part Number bytes
        pn_lsb = self.read_register(pn_lsb_addr)
        pn_mid = self.read_register(pn_mid_addr)
        pn_msb = self.read_register(pn_msb_addr)
        
        if pn_lsb is None or pn_mid is None or pn_msb is None:
            print("ERROR: Failed to read Part Number registers")
            return None
        
        # LabVIEW conversion logic for Part Number:
        # 1. PN_MSB / 128 → quotient and remainder
        pn_msb_quotient = pn_msb // 128
        pn_msb_remainder = pn_msb % 128
        
        # 2. Determine prefix based on remainder
        if pn_msb_remainder == 0:
            part_number_prefix = "A"
        else:
            part_number_prefix = "S"
        
        # 3. Calculate numeric part: LSB + (MID << 8) + (quotient << 16)
        part_number_numeric = pn_lsb + (pn_mid << 8) + (pn_msb_quotient << 16)
        
        # 4. Concatenate: "A10619" or "S12345"
        part_number = part_number_prefix + str(part_number_numeric)
        
        # Read Serial Number bytes
        sn_lsb = self.read_register(sn_lsb_addr)
        sn_mid = self.read_register(sn_mid_addr)
        sn_msb = self.read_register(sn_msb_addr)
        
        if sn_lsb is None or sn_mid is None or sn_msb is None:
            print("ERROR: Failed to read Serial Number registers")
            return None
        
        # LabVIEW conversion logic for Serial Number:
        # Simple 24-bit combination: LSB + (MID << 8) + (MSB << 16)
        serial_number = sn_lsb + (sn_mid << 8) + (sn_msb << 16)
        
        # Read PRange bytes
        prange_lsb = self.read_register(prange_lsb_addr)
        prange_msb = self.read_register(prange_msb_addr)
        
        if prange_lsb is None or prange_msb is None:
            print("WARNING: Failed to read PRange")
            prange = None
        else:
            # LabVIEW conversion logic for PRange (16-bit):
            # LSB + (MSB << 8)
            prange = prange_lsb + (prange_msb << 8)
        
        return {
            'part_number': part_number,
            'serial_number': serial_number,
            'prange': prange
        }
    
    def get_board_identity(self) -> str:
        """Get STM32 board identity string"""
        response = self.send_command("IDN")
        return response.decode('ascii', errors='ignore').strip()






















































