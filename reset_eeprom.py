import config
from pga305_reader import PGA305Reader
from eeprom_addresses import *
from helpers.calculate_crc import calculate_crc
import time


class ResetEEPROM:

    def __init__(self):
        self.reader = PGA305Reader()

    def run(self):
        mode = self._ask_mode()
        if mode == "single":
            self._run_single()
        elif mode == "multiple":
            self._run_multiple()
        else:
            print("Cancelled.")

    def _ask_mode(self):
        print("\n" + "=" * 70)
        print("  EEPROM RESET TO DEFAULTS")
        print("=" * 70)
        while True:
            choice = input("\n  [S]ingle channel or [M]ultiple channels? ").strip().lower()
            if choice in ("s", "single"):
                return "single"
            if choice in ("m", "multiple"):
                return "multiple"
            if choice in ("", "q", "quit", "cancel"):
                return None
            print("  Please enter S or M.")

    def _run_single(self):
        default_channel = config.CHANNEL
        raw = input(f"\n  Channel number [{default_channel}]: ").strip()
        if raw == "":
            channel = default_channel
        else:
            try:
                channel = int(raw)
            except ValueError:
                print("  Invalid channel number — cancelled.")
                return

        confirm = input(f"\n  Channel {channel}. Type YES to proceed: ").strip()
        if confirm != "YES":
            print("  Cancelled.")
            return

        print(f"\nConnecting to {config.SERIAL_PORT}...")
        self.reader.connect()

        try:
            status = self._reset_channel(channel, require_sensor=True)
        finally:
            self.reader.disconnect()

        self._print_summary({channel: status})

    def _run_multiple(self):
        confirm = input("\n  Channels 0-15. Type YES to proceed: ").strip()
        if confirm != "YES":
            print("  Cancelled.")
            return

        print(f"\nConnecting to {config.SERIAL_PORT}...")
        self.reader.connect()

        results = {}
        try:
            for channel in range(16):
                results[channel] = self._reset_channel(channel, require_sensor=False)
        finally:
            self.reader.disconnect()

        self._print_summary(results)

    def _reset_channel(self, channel, require_sensor):
        print(f"\n{'-' * 70}")
        print(f"  Channel {channel}")
        print('-' * 70)

        no_sensor_status = "failed" if require_sensor else "skipped"
        no_sensor_msg = "ERROR: No sensor detected." if require_sensor else "No sensor detected — skipping."

        try:
            self.reader.set_channel(channel)

            if not self.reader.enter_command_mode():
                print(f"  {no_sensor_msg}")
                return no_sensor_status

            sn_hi = self.reader.read_register(0x64, config.EEPROM_ADDR)
            sn_lo = self.reader.read_register(0x65, config.EEPROM_ADDR)
            if sn_hi is None or sn_lo is None:
                print(f"  {no_sensor_msg}")
                return no_sensor_status

            pages = sorted({addr // len(EEPROM_CACHE) for addr in COEFF_RESET_ADDRS})
            for page in pages:
                if not self._reset_page(page):
                    print(f"  ERROR: Failed on page 0x{page:02X} — aborting channel.")
                    return "failed"

            if not calculate_crc(self.reader):
                print("  WARNING: CRC retrigger failed.")
                return "failed"

            print(f"  Channel {channel}: DONE")
            return "ok"

        except Exception as e:
            print(f"  ERROR on channel {channel}: {e}")
            return "failed"

        finally:
            self.reader.disconnect_channel()

    def _build_page_data(self, page):
        page_size = len(EEPROM_CACHE)
        page_start = page * page_size
        data = []
        for i in range(page_size):
            addr = page_start + i
            if addr in COEFF_RESET_ADDRS:
                data.append(COEFF_RESET_OVERRIDES.get(addr, 0x00))
            else:
                val = self.reader.read_register(addr, config.EEPROM_ADDR)
                if val is None:
                    return None
                data.append(val)
        return data

    def _program_page(self, page, page_data):
        page_size = len(EEPROM_CACHE)
        page_start = page * page_size

        if not self.reader.write_register(EEPROM_PAGE_ADDR_REG, page, config.EEPROM_ADDR):
            print(f"  ERROR: Could not set page address to 0x{page:02X}")
            return False

        for i, val in enumerate(page_data):
            if not self.reader.write_register(EEPROM_CACHE_BASE + i, val, config.EEPROM_ADDR):
                print(f"  ERROR: Cache write failed at 0x{EEPROM_CACHE_BASE + i:02X}")
                return False

        if not self.reader.write_register(EEPROM_CTRL_REG, EEPROM_CTRL_ERASE_AND_PROGRAM, config.EEPROM_ADDR):
            print(f"  ERROR: Could not trigger program for page 0x{page:02X}")
            return False

        timed_out = True
        busy_mask = EEPROM_STATUS_ERASE_IN_PROGRESS | EEPROM_STATUS_PROGRAM_IN_PROGRESS
        for _ in range(20):
            time.sleep(0.1)
            status = self.reader.read_register(EEPROM_STATUS_REG, config.EEPROM_ADDR)
            if status is not None and (status & busy_mask) == 0:
                timed_out = False
                break

        if timed_out:
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
        page_size = len(EEPROM_CACHE)
        page_start = page * page_size
        print(f"    Page 0x{page:02X} (0x{page_start:02X}-0x{page_start + page_size - 1:02X})...", end=" ", flush=True)
        page_data = self._build_page_data(page)
        if page_data is None:
            print("FAILED")
            return False
        ok = self._program_page(page, page_data)
        print("OK" if ok else "FAILED")
        return ok

    def _print_summary(self, results):
        print("\n" + "=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        ok = sum(1 for s in results.values() if s == "ok")
        skipped = sum(1 for s in results.values() if s == "skipped")
        failed = sum(1 for s in results.values() if s == "failed")
        for channel, status in results.items():
            print(f"  Channel {channel:2d}: {status.upper()}")
        print("-" * 70)
        print(f"  Reset: {ok}   Skipped: {skipped}   Failed: {failed}")
        print("=" * 70)


if __name__ == "__main__":
    ResetEEPROM().run()