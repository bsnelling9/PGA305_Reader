import time
import config
from pga305_reader import PGA305Reader
from eeprom_addresses import *

EEPROM_PAGE_SIZE = 8
PAGE_F_START     = 0x78   # Last page, contains 0x7F (CRC byte)
PAGE_F_NUMBER    = 0x0F


class WriteEEPROM:

    def __init__(self, channel=1):
        self.channel = channel
        self.reader = PGA305Reader()

    def run(self):
        print("\n" + "=" * 70)
        print(f"WRITE EEPROM — CHANNEL {self.channel}")
        print("=" * 70)
        print("\nWARNING: Changes written here are permanent and survive power cycles.")

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
            self._write_menu()

        except Exception as e:
            print(f"\nERROR: {e}")

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _write_menu(self):
        while True:
            print("\n" + "-" * 70)
            print("  W. Write and program a register")
            print("  R. Read a register")
            print("  C. Retrigger CRC only")
            print("  X. Exit")
            print("-" * 70)
            choice = input("Select option: ").strip().upper()

            if choice == 'X':
                break
            elif choice == 'R':
                self._read_register()
            elif choice == 'W':
                self._write_register()
            elif choice == 'C':
                self._retrigger_crc()
            else:
                print("Invalid choice.")

    def _read_register(self):
        try:
            addr = int(input("Register address (e.g. 0x33): ").strip(), 16)
            name = EEPROM_REGISTERS.get(addr, f"0x{addr:02X}")
            value = self.reader.read_register(addr, config.EEPROM_ADDR)

            if value is None:
                print(f"  READ FAILED: {name} at 0x{addr:02X}")
            else:
                print(f"  0x{addr:02X}  {name:<30}  0x{value:02X}  ({value:3d})")

        except ValueError:
            print("ERROR: Invalid address")

    def _read_page(self, page_start):
        page_data = []

        for a in range(page_start, page_start + EEPROM_PAGE_SIZE):
            v = self.reader.read_register(a, config.EEPROM_ADDR)
            if v is None:
                print(f"  ERROR: Could not read 0x{a:02X}")
                return None
            page_data.append(v)

        return page_data

    def _write_page(self, page, page_data):
        if not self.reader.write_register(EEPROM_PAGE_ADDR_REG, page, config.EEPROM_ADDR):
            print("  ERROR: Could not set page address")
            return False

        for addr, v in zip(EEPROM_CACHE, page_data):
            if not self.reader.write_register(addr, v, config.EEPROM_ADDR):
                print(f"  ERROR: Cache write failed at 0x{addr:02X}")
                return False
            print(f"    0x{addr:02X} = 0x{v:02X}")

        if not self.reader.write_register(EEPROM_CTRL_REG, 0x04, config.EEPROM_ADDR):
            print("  ERROR: Could not trigger EEPROM program")
            return False

        for _ in range(20):
            status = self.reader.read_register(EEPROM_STATUS_REG, config.EEPROM_ADDR)
            if status is not None and (status & 0x06) == 0:
                print(f"  Program complete (status=0x{status:02X})")
                return True
            time.sleep(0.1)

        print("  WARNING: EEPROM burn timed out")
        return False

    def _retrigger_crc(self):
        """Reprogram page F (0x78-0x7F) to trigger automatic CRC recalculation.
        The PGA305 recalculates CRC automatically whenever 0x7F is programmed."""
        print(f"\n  Retriggering CRC by reprogramming page F (0x78-0x7F)...")

        page_f_data = self._read_page(PAGE_F_START)
        if page_f_data is None:
            print("  ERROR: Could not read page F")
            return False

        print(f"  Current page F contents:")
        for i, v in enumerate(page_f_data):
            a = PAGE_F_START + i
            n = EEPROM_REGISTERS.get(a, f"0x{a:02X}")
            print(f"    0x{a:02X}  {n:<30}  0x{v:02X}")

        if not self._write_page(PAGE_F_NUMBER, page_f_data):
            print("  ERROR: Could not reprogram page F")
            return False

        # Wait for CRC calculation (datasheet says 340us after digital core starts)
        time.sleep(0.05)

        crc_status = self.reader.read_register(0x8C, config.EEPROM_ADDR)
        if crc_status is None:
            print("  ERROR: Could not read CRC status")
            return False

        crc_good       = (crc_status >> 1) & 1
        crc_in_prog    = crc_status & 1
        crc_value      = self.reader.read_register(0x7F, config.EEPROM_ADDR)

        print(f"\n  EEPROM_CRC_STATUS = 0x{crc_status:02X}")
        print(f"    CRC_CHECK_IN_PROGRESS = {crc_in_prog}")
        print(f"    CRC_GOOD              = {crc_good}")
        print(f"  EEPROM_CRC_VALUE (0x7F) = 0x{crc_value:02X}" if crc_value is not None else "  EEPROM_CRC_VALUE read failed")

        if crc_good == 1:
            print("\n  CRC OK — EEPROM is valid. Power cycle to reload coefficients.")
            return True
        else:
            print("\n  WARNING: CRC still bad. EEPROM contents may be corrupt.")
            return False

    def _write_register(self):
        try:
            addr = int(input("Register address (e.g. 0x33): ").strip(), 16)
            val  = int(input("New value (e.g. 0x12): ").strip(), 16)

            if addr > 0x7F:
                print("ERROR: Address must be in EEPROM array range 0x00-0x7F")
                return

            name       = EEPROM_REGISTERS.get(addr, f"0x{addr:02X}")
            page       = addr // EEPROM_PAGE_SIZE
            page_start = page * EEPROM_PAGE_SIZE

            print(f"\n  Register : {name} (0x{addr:02X})")
            print(f"  Page     : 0x{page:02X} (0x{page_start:02X}-0x{page_start + 7:02X})")
            print(f"  New value: 0x{val:02X} ({val})")

            print(f"\n  Step 1: Reading page 0x{page:02X}...")
            page_data = self._read_page(page_start)
            if page_data is None:
                return

            print("  Current page contents:")
            for i, v in enumerate(page_data):
                a = page_start + i
                n = EEPROM_REGISTERS.get(a, f"0x{a:02X}")
                marker = " <- changing" if a == addr else ""
                print(f"    0x{a:02X}  {n:<30}  0x{v:02X}{marker}")

            page_data[addr - page_start] = val

            if input("\n  Confirm write and program? (yes/no): ").strip().lower() != 'yes':
                print("  Cancelled.")
                return

            print(f"\n  Step 2: Writing page 0x{page:02X} to cache and programming...")
            if not self._write_page(page, page_data):
                return

            print("\n  Step 3: Verifying...")
            all_ok = True
            for i in range(EEPROM_PAGE_SIZE):
                a        = page_start + i
                expected = page_data[i]
                readback = self.reader.read_register(a, config.EEPROM_ADDR)
                ok       = readback == expected
                if not ok:
                    all_ok = False
                n = EEPROM_REGISTERS.get(a, f"0x{a:02X}")
                print(f"    0x{a:02X}  {n:<30}  expected 0x{expected:02X}  got 0x{readback:02X}  {'OK' if ok else 'MISMATCH'}")

            if not all_ok:
                print("\n  WARNING: Some registers did not program correctly. Aborting CRC step.")
                return

            print(f"\n  SUCCESS: {name} permanently set to 0x{val:02X}")

            # Step 4 — Always retrigger CRC after any EEPROM change
            # Skip if we just wrote page F (0x78-0x7F) — it already retriggered CRC
            if page != PAGE_F_NUMBER:
                print("\n  Step 4: Retriggering CRC...")
                self._retrigger_crc()
            else:
                # We just programmed page F — just check CRC status
                time.sleep(0.05)
                crc_status = self.reader.read_register(0x8C, config.EEPROM_ADDR)
                crc_good   = (crc_status >> 1) & 1 if crc_status is not None else -1
                print(f"\n  CRC_STATUS = 0x{crc_status:02X}  CRC_GOOD = {crc_good}")
                if crc_good == 1:
                    print("  CRC OK — EEPROM is valid.")
                else:
                    print("  WARNING: CRC bad after page F write.")

            print("\n  Power cycle the board to reload from EEPROM.")

        except ValueError:
            print("ERROR: Invalid input")