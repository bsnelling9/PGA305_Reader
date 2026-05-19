import config
from pga305_reader import PGA305Reader
from eeprom_addresses import EEPROM_REGISTERS, EEPROM_PAGES


class ReadEEPROM:
    def __init__(self, channel=1):
        self.channel = channel
        self.reader = PGA305Reader()

    def run(self):
        print("\n" + "=" * 70)
        print(f"READ EEPROM — CHANNEL {self.channel}")
        print("=" * 70)

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            print(f"Switching to channel {self.channel}...")
            self.reader.set_channel(self.channel)

            print("Entering command mode...")
            if not self.reader.enter_command_mode():
                print("  ERROR: Could not enter command mode")
                return

            print("Command mode active")
            print("\nReading EEPROM registers...\n")

            self._print_registers()

            print("\n" + "=" * 70)
            print("EEPROM READ COMPLETE")
            print("=" * 70)

        except Exception as e:
            print(f"\n  ERROR: {e}")

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _print_registers(self):
        current_page_start = None

        for addr, label in sorted(EEPROM_REGISTERS.items()):

            page_start = self._get_page_start(addr)

            if page_start != current_page_start:
                if current_page_start is not None:
                    print()
                print("-" * 70)
                print(EEPROM_PAGES.get(page_start, f"PAGE 0x{page_start:02X}"))
                print("-" * 70)
                current_page_start = page_start

            value = self.reader.read_register(addr, config.EEPROM_ADDR)

            if value is None:
                print(f"  0x{addr:02X}  {label:<30}  READ FAILED")
            else:
                print(f"  0x{addr:02X}  {label:<30}  0x{value:02X}  ({value:3d})")

    def _get_page_start(self, addr: int) -> int:
        for page_start in sorted(EEPROM_PAGES.keys(), reverse=True):
            if addr >= page_start:
                return page_start
        return 0x00