import time
import config
from pga305_reader import PGA305Reader
from eeprom_addresses import (
    EEPROM_REGISTERS, EEPROM_PAGE_ADDR_REG, EEPROM_CTRL_REG,
    EEPROM_STATUS_REG, EEPROM_CTRL_ERASE_AND_PROGRAM
)

EEPROM_PAGE_SIZE = 8
PAGE_F_NUMBER    = 0x0F
PAGE_F_START     = 0x78

# Default EEPROM state — every register defaults to 0x00 unless listed here.
# Pages 0x00-0x0D only. Page E (PN/SN/PRANGE) is skipped. Page F (CRC) is retriggered.
DEFAULT_STATE = {
    0x02: 0x20,  # H0_MSB — matches TI factory default
    0x0E: 0x10,  # G0_MSB — matches TI factory default
    
    # PAGE 6
    0x30: 0x66,  # DIG_IF_CTRL
    0x31: 0x01,  # DAC_CTRL_STATUS
    0x33: 0x08,  # OP_STAGE_CTRL
    0x34: 0x01,  # BRDG_CTRL
    0x35: 0x80,  # P_GAIN_SELECT
    0x36: 0x02,  # T_GAIN_SELECT
    0x37: 0x43,  # TEMP_CTRL

    # PAGE 7
    0x39: 0x01,  # ADD_0x39
    0x3E: 0xFF,  # NORMAL_HIGH_LSB
    0x3F: 0x3F,  # NORMAL_HIGH_MSB

    # PAGE 8
    0x42: 0xFF,  # HIGH_CLAMP_LSB
    0x43: 0x3F,  # HIGH_CLAMP_MSB
    0x44: 0x01,  # PADC_GAIN_LSB  ← add this

    # PAGE B
    0x58: 0x07,
    0x59: 0x73,
    0x5A: 0xFF,
    0x5B: 0x3F,
    0x5C: 0xFF,
    0x5D: 0x3F,
    0x5E: 0x01,

    # PAGE D
    0x68: 0x01,
    0x6A: 0xFF,
    0x6B: 0xFF,
    0x6C: 0xFF,
    0x6D: 0xFF,
    0x6E: 0xFF,
    0x6F: 0xFF,
}

# Pages to reset (0x00-0x0D), page E (PN/SN/PRANGE) skipped
PAGES_TO_RESET = list(range(0x00, 0x0E))


class ResetEEPROM:

    def __init__(self, channel=None):
        self.channel = channel if channel is not None else config.CHANNEL
        self.reader = PGA305Reader()

    def run(self):
        print("\n" + "=" * 70)
        print("  EEPROM RESET TO DEFAULTS")
        print("=" * 70)
        print(f"  Channel : {self.channel}")
        print("\n  This will reset ALL calibration coefficients to zero.")
        print("  PN, SN, and PRANGE will be preserved.")
        print("  Analog config registers will be restored to power-on defaults.")

        confirm = input("\n  Are you sure? Type YES to proceed: ").strip()
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

            # Step 1 — Save PN, SN, PRANGE
            print("Step 1: Saving PN, SN, PRANGE...")
            preserved = self._read_preserved()
            if preserved is None:
                print("ERROR: Could not read PN/SN/PRANGE — aborting.")
                return
            self._print_preserved(preserved)

            # Step 2 — Reset pages 0x00-0x0D
            print("\nStep 2: Resetting pages 0x00-0x0D...")
            for page in PAGES_TO_RESET:
                if not self._reset_page(page):
                    print(f"ERROR: Failed on page 0x{page:02X} — aborting.")
                    return

            # Step 3 — Verify PN/SN/PRANGE still intact
            print("\nStep 3: Verifying PN/SN/PRANGE preserved...")
            preserved_after = self._read_preserved()
            if preserved_after != preserved:
                print("WARNING: PN/SN/PRANGE changed — this should not have happened!")
                self._print_preserved(preserved_after)
            else:
                print("  PN/SN/PRANGE unchanged. ✓")

            # Step 4 — Retrigger CRC
            print("\nStep 4: Retriggering CRC...")
            if not self._retrigger_crc():
                print("WARNING: CRC retrigger failed.")
                return

            print("\n" + "=" * 70)
            print("  RESET COMPLETE — Power cycle the board to reload from EEPROM.")
            print("=" * 70)

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
        return [DEFAULT_STATE.get(page_start + i, 0x00) for i in range(EEPROM_PAGE_SIZE)]

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

        for _ in range(20):
            time.sleep(0.1)
            status = self.reader.read_register(EEPROM_STATUS_REG, config.EEPROM_ADDR)
            if status is not None and (status & 0x06) == 0:
                break
        else:
            print(f"  WARNING: Page 0x{page:02X} program timed out")
            return False

        # Verify readback
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

    def _retrigger_crc(self):
        if not self.reader.write_register(0x8A, 0x01, config.EEPROM_ADDR):
            print("  ERROR: Could not trigger CRC calculation")
            return False

        time.sleep(0.5)

        crc_value = self.reader.read_register(0x8D, config.EEPROM_ADDR)
        if crc_value is None:
            print("  ERROR: Could not read calculated CRC from 0x8D")
            return False

        print(f"  Calculated CRC = 0x{crc_value:02X}")

        page_f_data = []
        for addr in range(PAGE_F_START, PAGE_F_START + EEPROM_PAGE_SIZE):
            if addr == 0x7F:
                page_f_data.append(crc_value)
            else:
                val = self.reader.read_register(addr, config.EEPROM_ADDR)
                if val is None:
                    print(f"  ERROR: Could not read 0x{addr:02X}")
                    return False
                page_f_data.append(val)

        if not self._program_page(PAGE_F_NUMBER, page_f_data):
            print("  ERROR: Could not program CRC to page F")
            return False

        crc_status = self.reader.read_register(0x8C, config.EEPROM_ADDR)
        crc_good = (crc_status >> 1) & 1 if crc_status is not None else 0

        print(f"  EEPROM_CRC_STATUS = 0x{crc_status:02X}  CRC_GOOD = {crc_good}")
        print(f"  EEPROM_CRC_VALUE  = 0x{crc_value:02X}")

        if crc_good == 1:
            print("  CRC OK")
            return True
        else:
            print("  WARNING: CRC bad after reset.")
            return False