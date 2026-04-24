import config
from pga305_reader import PGA305Reader


def write_register(reader: PGA305Reader, page: int, addr: int, val: int) -> bool:
    if page == 0:
        i2c_addr = config.PGA305_I2C_ADDR
    elif page == 2:
        i2c_addr = config.I2C_CONTROL
    else:
        print(f"ERROR: Invalid page {page} — must be 0 or 2")
        return False

    current = reader.read_register(addr, i2c_addr)
    print(f"  0x{addr:02X} current: 0x{current:02X}")

    if not reader.write_register(addr, val, i2c_addr):
        print(f"ERROR: Write failed for 0x{addr:02X}")
        return False

    readback = reader.read_register(addr, i2c_addr)
    print(f"  0x{addr:02X} after:   0x{readback:02X}")

    if readback != val:
        print(f"ERROR: Write did not stick — expected 0x{val:02X} got 0x{readback:02X}")
        return False

    print(f"  0x{addr:02X} persisted: 0x{readback:02X} ✓")
    return True