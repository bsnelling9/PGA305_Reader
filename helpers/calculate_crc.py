import config

EEPROM_PAGE_SIZE = 8
PAGE_F_NUMBER    = 0x0F
PAGE_F_START     = 0x78

def calculate_crc(reader):
    print("  Calculating CRC...")

    if not reader.write_register(0x8A, 0x01, config.EEPROM_ADDR):
        print("  ERROR: failed to recalculate CRC")
        return False

    crc_value = None
    for _ in range(50):
        val = reader.read_register(0x8D, config.EEPROM_ADDR)
        if val is not None and val != 0x00:
            crc_value = val
            break

    if crc_value is None:
        print("  ERROR: CRC calculation timed out")
        return False

    print(f"  Calculated CRC = 0x{crc_value:02X}")

    page_f_data = []
    for addr in range(PAGE_F_START, PAGE_F_START + EEPROM_PAGE_SIZE):
        if addr == 0x7F:
            page_f_data.append(crc_value)
        else:
            val = reader.read_register(addr, config.EEPROM_ADDR)
            if val is None:
                print(f"  ERROR: Could not read 0x{addr:02X}")
                return False
            page_f_data.append(val)

    if not reader.write_register(0x88, PAGE_F_NUMBER, config.EEPROM_ADDR):
        print("  ERROR: Could not set page address")
        return False

    for i, val in enumerate(page_f_data):
        if not reader.write_register(0x80 + i, val, config.EEPROM_ADDR):
            print(f"  ERROR: Cache write failed at 0x{0x80+i:02X}")
            return False

    if not reader.write_register(0x89, 0x04, config.EEPROM_ADDR):
        print("  ERROR: Could not trigger page F program")
        return False

    for _ in range(50):
        status = reader.read_register(0x8B, config.EEPROM_ADDR)
        if status is not None and (status & 0x06) == 0:
            break
    else:
        print("  WARNING: Page F program timed out")
        return False

    crc_status = reader.read_register(0x8C, config.EEPROM_ADDR)
    crc_good = (crc_status >> 1) & 1 if crc_status is not None else 0

    print(f"  EEPROM_CRC_STATUS = 0x{crc_status:02X}  CRC_GOOD = {crc_good}")
    print(f"  EEPROM_CRC_VALUE  = 0x{crc_value:02X}")

    if crc_good == 1:
        print("CRC value is correct")
        return True
    else:
        print(f"CRC check status: {crc_status:02X}")
        return False