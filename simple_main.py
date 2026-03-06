import pyvisa
import time

SERIAL_PORT = "ASRL5::INSTR"
BAUD_RATE = 115200
TIMEOUT_MS = 2000
CHANNEL = 3
PGA305_I2C_ADDR = 0x20  # Slave address 32 (decimal) = 0x20 (hex) - matches LabVIEW
EEPROM_ADDR = 0x25

rm = pyvisa.ResourceManager()
inst = rm.open_resource(SERIAL_PORT)
inst.baud_rate = BAUD_RATE
inst.timeout = TIMEOUT_MS


def send_command(cmd: str):
    """Send command to STM32"""
    cmd_bytes = (cmd + '\n').encode('ascii')
    inst.write_raw(cmd_bytes)
    time.sleep(0.05)
    try:
        if inst.bytes_in_buffer > 0:
            return inst.read_bytes(inst.bytes_in_buffer)
        return inst.read_bytes(64)
    except:
        return b''


def read_register(reg_addr: int):
    """Read PGA305 register from address 0x20"""
    cmd = f"imr{PGA305_I2C_ADDR:02X}{reg_addr:02X}"
    raw = send_command(cmd)
    if len(raw) >= 2:
        try:
            return int(raw[0:2].decode('ascii'), 16)
        except:
            return None
    return None


def enter_command_mode(max_retries=5):
    """Enter command mode with retry - works around STM32 firmware bug"""
    print("\n" + "="*70)
    print("ENTERING COMMAND MODE")
    print("="*70)
    
    for attempt in range(max_retries):
        print(f"\nAttempt {attempt + 1}/{max_retries}: Sending cm_20...")
        
        # Send command - STM32 needs time to do TWO I2C writes (up to 2+ seconds!)
        cmd_bytes = ('cm_20\n').encode('ascii')
        inst.write_raw(cmd_bytes)
        
        # CRITICAL: Wait for STM32 to complete both I2C writes + 80ms delay
        # I was having issues with this as tere was not enough timepyt
        time.sleep(2.5)  
        
        try:
            if inst.bytes_in_buffer > 0:
                cm_response = inst.read_bytes(inst.bytes_in_buffer)
            else:
                cm_response = inst.read_bytes(64)
        except:
            cm_response = b''
        
        print(f" Response: {cm_response.hex() if cm_response else 'no response'}")
        
        if len(cm_response) >= 2 and cm_response[0:2] == b'\x06\x0a':
            # Got ACK - verify it actually worked
            verify = read_register(0x01)
            
            if verify == 0x03:
                print(f"✓ Command mode SUCCESS (reg 0x01 = 0x03)")
                return True
            else:
                print(f"✗ Got ACK but reg 0x01 = 0x{verify:02X} (STM32 firmware bug!)")
        else:
            print(f"✗ No ACK")
        
        if attempt < max_retries - 1:
            print("  Resetting I2C...")
            send_command("i2cr")
            time.sleep(1.0)
    
    print(f"\n✗ Command mode FAILED after {max_retries} attempts")
    
    return False


def read_eeprom_page():
    """Read EEPROM - try using address 0x25 directly after cm_20"""
    print("\nAttempting EEPROM read using I2C address 0x25 directly...")
    print("(After cm_20, EEPROM should be accessible at 0x25)")
    
    eeprom = {}
    registers = [
        ('PN_LSB', 0x70), ('PN_MID', 0x71), ('PN_MSB', 0x72),
        ('SN_LSB', 0x73), ('SN_MID', 0x74), ('SN_MSB', 0x75),
        ('PRANGE_LSB', 0x76), ('PRANGE_MSB', 0x77)
    ]
    
    # Try reading from 0x25 instead of 0x20
    
    
    for name, addr in registers:
        cmd = f"imr{EEPROM_ADDR:02X}{addr:02X}"
        raw = send_command(cmd)
        
        if len(raw) >= 2:
            try:
                val = int(raw[0:2].decode('ascii'), 16)
            except:
                val = None
        else:
            val = None
            
        if val is None:
            print(f"✗ Error reading {name}")
            return None
        eeprom[name] = val
        print(f"  {name:12} (0x{addr:02X}) = 0x{val:02X}")
    
    return eeprom


def convert_eeprom_to_id(eeprom):
    """Convert EEPROM bytes to Part Number/Serial Number - matches LabVIEW"""
    # Part Number
    pn_num = eeprom['PN_LSB'] + (eeprom['PN_MID'] << 8) + ((eeprom['PN_MSB'] // 128) << 16)
    pn_prefix = "A" if eeprom['PN_MSB'] % 128 == 0 else "S"
    part_number = pn_prefix + str(pn_num)
    
    # Serial Number
    serial_number = eeprom['SN_LSB'] + (eeprom['SN_MID'] << 8) + (eeprom['SN_MSB'] << 16)
    
    # PRange
    prange = eeprom['PRANGE_LSB'] + (eeprom['PRANGE_MSB'] << 8)
    
    return {
        'part_number': part_number,
        'serial_number': serial_number,
        'prange': prange
    }


def reset_i2c():
    """Reset I2C bus - matches LabVIEW MuxIOModule_ResetI2C.vi"""
    print("\nResetting I2C bus (thorough reset)...")
    
    # Send i2cr command
    reset_response = send_command("i2cr")
    
    if len(reset_response) >= 2 and reset_response[0:2] == b'\x06\x0a':
        print(" I2C reset ACK received")
    else:
        print(f" I2C reset response: {reset_response.hex() if reset_response else 'none'}")
    
    # Wait longer for bus to fully reset
    time.sleep(1.0)
    
    # Verify I2C is working by reading a known register
    print("  Verifying I2C bus is operational...")
    test_read = read_register(0x01)
    if test_read is not None:
        print(f"  ✓ I2C bus operational (test read = 0x{test_read:02X})")
    else:
        print("  ✗ I2C bus may not be working")


def main():
    print("PGA305 Serial Number Reader - FINAL VERSION")
    print("Matches LabVIEW with STM32 firmware bug workaround")
    print("="*70)
    
    try:
        # Thorough I2C reset (like LabVIEW)
        reset_i2c()
        
        # Select channel
        print(f"\nSelecting channel {CHANNEL}...")
        send_command(f"mx3{CHANNEL:02X}")
        time.sleep(0.5)  # Longer delay after channel switch
        
        # Enter command mode (with retry for STM32 bug)
        if not enter_command_mode():
            print("\nABORTED: Could not enter command mode")
            print("Try unplugging power for 60 seconds and run again immediately")
            return
        
        # Read EEPROM
        eeprom = read_eeprom_page()
        if not eeprom:
            print("\nERROR: Could not read EEPROM")
            return
        
        # Convert to Part Number/Serial Number
        result = convert_eeprom_to_id(eeprom)
        
        print("\n" + "="*70)
        print("RESULT")
        print("="*70)
        print(f"Part Number:   {result['part_number']}")
        print(f"Serial Number: {result['serial_number']}")
        print(f"PRange:        {result['prange']}")
        print("="*70)
        
    finally:
        inst.close()


if __name__ == "__main__":
    main()