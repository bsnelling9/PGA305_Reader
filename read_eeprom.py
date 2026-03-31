import config
from pga305_reader import PGA305Reader
from eeprom_addresses import EEPROM_REGISTERS, EEPROM_PAGES, I2C_EEPROM


class ReadEEPROM:
    """
    Reads and displays all EEPROM configuration registers from a PGA305.

    Register addresses are loaded from the CSV register map if available
    (same path used by PGA305Reader). Falls back to eeprom_addresses.py
    if the CSV is not found.
    """

    def __init__(self, channel=1):
        self.channel = channel
        self.reader = PGA305Reader()
        self.registers = self._load_registers()

    def _load_registers(self) -> dict:
        """
        Load EEPROM register addresses from CSV if available,
        otherwise use eeprom_addresses.py as fallback.
        """
        import os
        import csv

        csv_path = config.REGISTER_MAP_PATH

        if csv_path and os.path.exists(csv_path):
            registers = {}
            try:
                with open(csv_path, 'r') as f:
                    for row in csv.DictReader(f):
                        name = row.get('REGISTER NAME', '').strip()
                        offset_str = row.get('DI Offset Address', '').strip()

                        # Only load EEPROM array entries (DI Page 0x5)
                        if name.startswith('EEPROM_ARRAY') and offset_str:
                            try:
                                label = name.replace('EEPROM_ARRAY ', '').strip()
                                addr = int(offset_str, 0)
                                registers[addr] = label
                            except ValueError:
                                pass

                if registers:
                    print(f"  [Register map loaded from CSV: {len(registers)} entries]")
                    return dict(sorted(registers.items()))

            except Exception as e:
                print(f"  [CSV load failed: {e} — using fallback addresses]")

        print("  [Using eeprom_addresses.py]")
        return EEPROM_REGISTERS

    def run(self):
        print("\n" + "="*70)
        print(f"READ EEPROM — CHANNEL {self.channel}")
        print("="*70)

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            print(f"Switching to channel {self.channel}...")
            self.reader.set_channel(self.channel)

            print("Entering command mode...")
            if not self.reader.enter_command_mode():
                print("✗ ERROR: Could not enter command mode")
                return

            print("Command mode active ✓")
            print("\nReading EEPROM registers...\n")

            self._print_registers()

            print("\n" + "="*70)
            print("EEPROM READ COMPLETE")
            print("="*70)

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _print_registers(self):
        """Read and print all EEPROM registers grouped by page."""
        current_page_start = None

        for addr, label in self.registers.items():

            page_start = self._get_page_start(addr)
            if page_start != current_page_start:
                if current_page_start is not None:
                    print()
                print("-" * 70)
                print(EEPROM_PAGES.get(page_start, f"PAGE 0x{page_start:02X}"))
                print("-" * 70)
                current_page_start = page_start

            value = self.reader.read_register(addr, I2C_EEPROM)

            if value is None:
                print(f"  0x{addr:02X}  {label:<30} ✗ READ FAILED")
            else:
                print(f"  0x{addr:02X}  {label:<30} 0x{value:02X}  ({value:3d})")

    def _get_page_start(self, addr: int) -> int:
        """Return the page boundary address for a given register address."""
        for page_start in sorted(EEPROM_PAGES.keys(), reverse=True):
            if addr >= page_start:
                return page_start
        return 0x00