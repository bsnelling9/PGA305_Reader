import config
from pga305_reader import PGA305Reader
from eeprom_defaults import EEPROM_DEFAULTS
from eeprom_addresses import *
from helpers.calculate_crc import calculate_crc # type: ignore
import time

EEPROM_PAGE_SIZE = 8
PAGE_F_NUMBER    = 0x0F
PAGE_F_START     = 0x78


# Pages to reset (0x00-0x0D), page E (PN/SN/PRANGE) skipped
PAGES_TO_RESET = list(range(0x00, 0x0E))

class ResetEEPROM:

    def __init__(self, channel=None):
        self.channel = channel if channel is not None else config.CHANNEL
        self.reader  = PGA305Reader()

    def run(self):
        print("\n" + "=" * 70)
        print("  EEPROM RESET TO DEFAULTS")
        print("=" * 70)
        print(f"  Channel : {self.channel}")
        print("\n  This will reset ALL calibration coefficients to zero.")
        print("  PN, SN, and PRANGE will be preserved.")

        confirm = input("\n Type YES to proceed: ").strip()
        if confirm != "YES":
            print("  Cancelled.")
            return

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            print(f"Switching to channel {self.channel}...")
            self.reader.set_channel(self.channel)

            print("Entering command mode...")
            if not self.reader.enter_command_mode():
                print("ERROR: Could not enter command mode")
                return

            print("Command mode active\n")

            print("Step 1: Saving PN, SN, PRANGE...")
            preserved = self._read_preserved()
            if preserved is None:
                print("ERROR: Could not read PN/SN/PRANGE — aborting.")
                return
            self._print_preserved(preserved)

            print("\nStep 2: Resetting pages 0x00-0x0D...")
            for page in PAGES_TO_RESET:
                if not self._reset_page(page):
                    print(f"ERROR: Failed on page 0x{page:02X} — aborting.")
                    return

            print("\nStep 3: Verifying PN/SN/PRANGE preserved...")
            preserved_after = self._read_preserved()
            if preserved_after != preserved:
                print("WARNING: PN/SN/PRANGE changed — this should not have happened!")
                self._print_preserved(preserved_after)
            else:
                print("  PN/SN/PRANGE unchanged.")

            print("\nStep 4: Retriggering CRC...")
            if not calculate_crc(self.reader):
                print("WARNING: CRC retrigger failed.")
                return

            print("\n" + "=" * 70)

        except Exception as e:
            print(f"\nERROR: {e}")

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _read_preserved(self):
        preserved = {}
        for addr in range(0x70, 0x78):
            val = self.reader.read_register(addr, config.EEPROM_ADDR)
            if val is None:
                print(f"  ERROR: Could not read 0x{addr:02X}")
                return None
            preserved[addr] = val
        return preserved

    def _print_preserved(self, preserved):
        for addr, val in preserved.items():
            name = EEPROM_REGISTERS.get(addr, f"0x{addr:02X}")
            print(f"  0x{addr:02X}  {name:<20}  0x{val:02X}  ({val})")

    def _build_page_data(self, page):
        page_start = page * EEPROM_PAGE_SIZE
        
        return [EEPROM_DEFAULTS.get(page_start + i, 0x00) for i in range(EEPROM_PAGE_SIZE)]

    def _program_page(self, page, page_data):

        page_start = page * EEPROM_PAGE_SIZE

        if not self.reader.write_register(EEPROM_PAGE_ADDR_REG, page, config.EEPROM_ADDR):
            print(f"  ERROR: Could not set page address to 0x{page:02X}")
            return False

        for i, val in enumerate(page_data):
            if not self.reader.write_register(0x80 + i, val, config.EEPROM_ADDR):
                print(f"  ERROR: Cache write failed at 0x{0x80+i:02X}")
                return False

        if not self.reader.write_register(EEPROM_CTRL_REG, EEPROM_CTRL_ERASE_AND_PROGRAM, config.EEPROM_ADDR):
            print(f"  ERROR: Could not trigger program for page 0x{page:02X}")
            return False

        time_out = False
        for _ in range(20):
            time.sleep(0.1)
            status = self.reader.read_register(EEPROM_STATUS_REG, config.EEPROM_ADDR)
            
            if status is not None and (status & 0x06) == 0:
                time_out = True
                break

        if not time_out:
            print(f"  WARNING: Page 0x{page:02X} program timed out")
            return False

        all_ok = True
        for i, expected in enumerate(page_data):
            addr = page_start + i
            readback = self.reader.read_register(addr, config.EEPROM_ADDR)
            
            if readback != expected:
                name = EEPROM_REGISTERS.get(addr, f"0x{addr:02X}")
                print(f"  MISMATCH: 0x{addr:02X} {name:<20} expected 0x{expected:02X} got 0x{readback:02X}")
                all_ok = False

        return all_ok

    def _reset_page(self, page):
        page_start = page * EEPROM_PAGE_SIZE
        
        print(f"  Page 0x{page:02X} (0x{page_start:02X}-0x{page_start+7:02X})...", end=" ", flush=True)
        
        page_data = self._build_page_data(page)
        
        ok = self._program_page(page, page_data)
        
        print("OK" if ok else "FAILED")
        return ok