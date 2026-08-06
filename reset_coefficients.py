import config
from pga305_reader import PGA305Reader
from eeprom_addresses import *
from helpers.calculate_crc import calculate_crc


def build_coeff_reset_targets() -> dict:
    targets = {addr: 0x00 for addr in COEFF_RESET_ADDRS}
    targets.update(COEFF_RESET_OVERRIDES)
    return targets


def process_flash_routine(reader, target_updates):
    EEPROM_PAGE_SIZE = 8
    pages_to_update = sorted(set(addr // EEPROM_PAGE_SIZE for addr in target_updates.keys()))

    for page in pages_to_update:
        page_start = page * EEPROM_PAGE_SIZE
        print(f"Writing to Page 0x{page:02X} (Addresses 0x{page_start:02X}-0x{page_start+7:02X})...")

        page_data = []
        for a in range(page_start, page_start + EEPROM_PAGE_SIZE):
            current_val = reader.read_register(a, config.EEPROM_ADDR)
            if current_val is None:
                print(f"  ERROR: Safe back-read failed at address 0x{a:02X}. Process stopped.")
                return False
            page_data.append(current_val)

        for addr, new_byte in target_updates.items():
            if page_start <= addr < (page_start + EEPROM_PAGE_SIZE):
                page_data[addr - page_start] = new_byte

        if not _program_page(reader, page, page_data):
            print(f"  CRITICAL: Failed to write to page 0x{page:02X}")
            return False
        print(f"  Page 0x{page:02X} updated successfully.")
    return True


def _program_page(reader, page, page_data):
    if not reader.write_register(EEPROM_PAGE_ADDR_REG, page, config.EEPROM_ADDR):
        print(f"  ERROR: Failed to switch to page 0x{page:02X}")
        return False

    for cache_addr, value in zip(EEPROM_CACHE.keys(), page_data):
        if not reader.write_register(cache_addr, value, config.EEPROM_ADDR):
            print(f"  ERROR: Cache write failed at register 0x{cache_addr:02X}")
            return False

    if not reader.write_register(EEPROM_CTRL_REG, EEPROM_CTRL_ERASE_AND_PROGRAM, config.EEPROM_ADDR):
        print("  ERROR: Failed to trigger EEPROM write cycle execution.")
        return False

    for _ in range(20):
        status = reader.read_register(EEPROM_STATUS_REG, config.EEPROM_ADDR)
        if status is not None and (status & (EEPROM_STATUS_ERASE_IN_PROGRESS | EEPROM_STATUS_PROGRAM_IN_PROGRESS)) == 0:
            return True

    return False


def _verify_reset(reader, target_updates):
    print("\nVerifying reset values...")
    all_ok = True
    for addr, expected in sorted(target_updates.items()):
        readback = reader.read_register(addr, config.EEPROM_ADDR)
        name = EEPROM_REGISTERS.get(addr, f"0x{addr:02X}")
        if readback != expected:
            print(f"  MISMATCH: 0x{addr:02X} {name:<20} expected 0x{expected:02X} got 0x{readback:02X}")
            all_ok = False
    if all_ok:
        print("  All coefficient/gain/offset registers verified at default.")
    return all_ok


def reset_channel(channel):
    print("\n" + "=" * 70)
    print(f"RESET COEFFICIENTS TO DEFAULT — CHANNEL {channel}")
    print("=" * 70)

    reader = PGA305Reader()

    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        print(f"Switching to channel {channel}...")
        reader.set_channel(channel)

        print("Entering command mode...")
        if not reader.enter_command_mode():
            print("ERROR: failed to enter Command mode")
            return False

        print("Command mode active\n")

        target_updates = build_coeff_reset_targets()

        print("Resetting coefficients, PADC_GAIN/OFFSET, TADC_GAIN/OFFSET...")
        if not process_flash_routine(reader, target_updates):
            print("CRITICAL: Reset failed during flash routine.")
            return False

        print("\nCalculating CRC...")
        calculate_crc(reader)

        ok = _verify_reset(reader, target_updates)
        if ok:
            print(f"\nChannel {channel}: reset to default and verified OK.")
        else:
            print(f"\nChannel {channel}: reset written but verification found mismatches.")
        return ok

    except Exception as e:
        print(f"\nERROR: {e}")
        return False

    finally:
        reader.disconnect_channel()
        reader.disconnect()


def run():
    while True:
        raw = input("\nEnter channel number to reset (or 'x' to exit): ").strip()

        if raw.lower() == 'x':
            print("Exiting.")
            break

        try:
            channel = int(raw)
        except ValueError:
            print("Invalid channel number")
            continue

        reset_channel(channel)


if __name__ == "__main__":
    run()