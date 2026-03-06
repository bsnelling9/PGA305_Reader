import pyvisa
import time
import csv
import os
import config
from typing import Optional, Dict


class PGA305Reader:
   
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
                    raise
        return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.inst:
            self.inst.close()
            self.inst = None
    
    def _load_register_map(self, csv_path: str) -> bool:
        """Load PGA305 register definitions from CSV file"""
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
        """Send command to STM32 and return raw response"""
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
        """Select multiplexer channel"""
        cmd = f"mx3{channel:02X}"
        response = self.send_command(cmd)
        time.sleep(config.CHANNEL_SWITCH_DELAY)
    
    def reset_i2c(self):
        """Reset I2C bus"""
        self.send_command("i2cr")
        time.sleep(config.I2C_RESET_DELAY)
    
    def read_register(self, reg_addr: int, i2c_addr: int = None) -> Optional[int]:
        """
        Read single PGA305 register
        
        Args:
            reg_addr: Register address (8-bit)
            i2c_addr: I2C slave address (default: config.PGA305_I2C_ADDR)
            
        Returns:
            Register value (0-255) or None if read failed
        """
        if i2c_addr is None:
            i2c_addr = config.PGA305_I2C_ADDR
        
        cmd = f"imr{i2c_addr:02X}{reg_addr:02X}"
        raw = self.send_command(cmd)
        
        if len(raw) >= 2:
            try:
                hex_str = raw[0:2].decode('ascii')
                value = int(hex_str, 16)
                return value
            except:
                return None
        return None
    
    def enter_command_mode(self, max_retries: int = None) -> bool:
        """
        Enter PGA305 command mode with retry logic
        
        This is the CRITICAL step that unlocks EEPROM access.
        Uses retry logic to work around STM32 firmware bug.
        
        Args:
            max_retries: Maximum retry attempts (default: from config.CM_MAX_RETRIES)
            
        Returns:
            True if command mode entered successfully
        """
        if max_retries is None:
            max_retries = config.CM_MAX_RETRIES
        
        for attempt in range(max_retries):
            # Send cm_20 command
            # CRITICAL: Must wait for STM32 to complete TWO I2C writes
            cmd_bytes = ('cm_20\n').encode('ascii')
            self.inst.write_raw(cmd_bytes)
            time.sleep(config.CM_COMMAND_DELAY)  # 2.5+ seconds for STM32
            
            # Read response
            try:
                if self.inst.bytes_in_buffer > 0:
                    cm_response = self.inst.read_bytes(self.inst.bytes_in_buffer)
                else:
                    cm_response = self.inst.read_bytes(64)
            except:
                cm_response = b''
            
            # Check for ACK
            if len(cm_response) >= 2 and cm_response[0:2] == b'\x06\x0a':
                # Got ACK - verify it actually worked (STM32 firmware bug!)
                verify = self.read_register(0x01, config.PGA305_I2C_ADDR)
                
                if verify == 0x03:
                    # Command mode SUCCESS!
                    return True
                # else: STM32 lied - first write failed, retry
            
            # Retry - reset I2C first
            if attempt < max_retries - 1:
                self.reset_i2c()
        
        # All retries failed
        return False
    
    def read_sensor_data(self, channel: int, verbose: bool = True) -> Optional[Dict[str, any]]:
        """
        Read Part Number, Serial Number, and PRange from PGA305 sensor
        
        Args:
            channel: Multiplexer channel number (0-7)
            verbose: Print progress messages (default: True)
            
        Returns:
            Dictionary with 'part_number', 'serial_number', 'prange' or None if failed
        """
        if verbose:
            print(f"\nReading channel {channel}...")
        
        self.reset_i2c()
        
        self.set_channel(channel)
        
        # Step 3: Enter command mode (CRITICAL!)
        if not self.enter_command_mode():
            if verbose:
                print("✗ ERROR: Could not enter command mode")
                print("  Try power cycling the board")
            return None
        
        if verbose:
            print("✓ Command mode active")
        
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
            print("Unable to read from csv file, using hardcoded values")
            pn_lsb_addr, pn_mid_addr, pn_msb_addr = 0x70, 0x71, 0x72
            sn_lsb_addr, sn_mid_addr, sn_msb_addr = 0x73, 0x74, 0x75
            prange_lsb_addr, prange_msb_addr = 0x76, 0x77
        
        # Read Part Number from EEPROM_ADDR (0x25)
        pn_lsb = self.read_register(pn_lsb_addr, config.EEPROM_ADDR)
        pn_mid = self.read_register(pn_mid_addr, config.EEPROM_ADDR)
        pn_msb = self.read_register(pn_msb_addr, config.EEPROM_ADDR)
        
        if pn_lsb is None or pn_mid is None or pn_msb is None:
            if verbose:
                print("✗ ERROR: Failed to read Part Number")
            return None
        
        # Convert Part Number
        pn_msb_quotient = pn_msb // 128
        pn_msb_remainder = pn_msb % 128
        part_number_prefix = "A" if pn_msb_remainder == 0 else "S"
        part_number_numeric = pn_lsb + (pn_mid << 8) + (pn_msb_quotient << 16)
        part_number = part_number_prefix + str(part_number_numeric)
        
        # Read Serial Number from EEPROM_ADDR (0x25)
        sn_lsb = self.read_register(sn_lsb_addr, config.EEPROM_ADDR)
        sn_mid = self.read_register(sn_mid_addr, config.EEPROM_ADDR)
        sn_msb = self.read_register(sn_msb_addr, config.EEPROM_ADDR)
        
        if sn_lsb is None or sn_mid is None or sn_msb is None:
            if verbose:
                print("✗ ERROR: Failed to read Serial Number")
            return None
        
        serial_number = sn_lsb + (sn_mid << 8) + (sn_msb << 16)
        
        # Read PRange from EEPROM_ADDR (0x25)
        prange_lsb = self.read_register(prange_lsb_addr, config.EEPROM_ADDR)
        prange_msb = self.read_register(prange_msb_addr, config.EEPROM_ADDR)
        
        if prange_lsb is None or prange_msb is None:
            prange = None
        else:
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