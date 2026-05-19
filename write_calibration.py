import os
import config
from pga305_reader import PGA305Reader
from eeprom_addresses import *
from helpers.calculate_crc import calculate_crc

EEPROM_PAGE_SIZE = 8

class CalibrationWriter:
    def __init__(self):
        self.reader = PGA305Reader()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.DUT_BASE_DIR = os.path.abspath(os.path.join(current_dir, "..", "Calibration_data"))
        
    def parse_dut_file(self, file_path):
        """Parses the calibration text file and extracts targeted byte updates."""
        updates = {}
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Missing calibration file: {file_path}")

        current_section = None
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].strip()
                    continue

                if current_section in ("CalibrationSettings", "Coefficients"):
                    if '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip().upper()
                        val = val.strip().replace('"', '')

                        if not val:
                            continue

                        if key in COEFFICIENTS_MAP:
                            reg_addrs = COEFFICIENTS_MAP[key]
                            
                            try:
                                int_val = int(val, 16)
                            except ValueError:
                                int_val = int(val)

                            # Distribute value across registers (LSB first)
                            for i, addr in enumerate(reg_addrs):
                                updates[addr] = (int_val >> (8 * i)) & 0xFF
        return updates

    def _program_page(self, page, page_data):
        """Sets the active page register, fills the 8-byte cache, and triggers the burn."""
        if not self.reader.write_register(EEPROM_PAGE_ADDR_REG, page, config.EEPROM_ADDR):
            print(f"  ERROR: Failed to switch to page 0x{page:02X}")
            return False

        for cache_addr, value in zip(EEPROM_CACHE.keys(), page_data):
            if not self.reader.write_register(cache_addr, value, config.EEPROM_ADDR):
                print(f"  ERROR: Cache write failed at register 0x{cache_addr:02X}")
                return False

        if not self.reader.write_register(EEPROM_CTRL_REG, EEPROM_CTRL_ERASE_AND_PROGRAM, config.EEPROM_ADDR):
            print("  ERROR: Failed to trigger EEPROM write cycle execution.")
            return False

        # Poll the status register until the busy bits clear
        for _ in range(20):
            status = self.reader.read_register(EEPROM_STATUS_REG, config.EEPROM_ADDR)
            if status is not None and (status & (EEPROM_STATUS_ERASE_IN_PROGRESS | EEPROM_STATUS_PROGRAM_IN_PROGRESS)) == 0:
                return True
        return False

    def process_flash_routine(self, target_updates):
        """Groups addresses into pages, merges updates with existing data, and writes."""

        pages_to_update = sorted(list(set(addr // EEPROM_PAGE_SIZE for addr in target_updates.keys())))

        for page in pages_to_update:
            page_start = page * EEPROM_PAGE_SIZE
            print(f"Flashing Page 0x{page:02X} (Addresses 0x{page_start:02X}-0x{page_start+7:02X})...")
            

            page_data = []
            for a in range(page_start, page_start + EEPROM_PAGE_SIZE):
                current_val = self.reader.read_register(a, config.EEPROM_ADDR)
                if current_val is None:
                    print(f"  ERROR: Safe back-read failed at address 0x{a:02X}. Process halted.")
                    return False
                page_data.append(current_val)


            for addr, new_byte in target_updates.items():
                if page_start <= addr < (page_start + EEPROM_PAGE_SIZE):
                    page_data[addr - page_start] = new_byte


            if not self._program_page(page, page_data):
                print(f"  CRITICAL: Write execution failed at page 0x{page:02X}")
                return False
            print(f"  Page 0x{page:02X} updated successfully.")
        return True

    def run(self):
        print("\n" + "=" * 70)
        print("PGA305 AUTOMATED CALIBRATION LOADER")
        print("=" * 70)

        part_num = input("Enter Part Number (e.g., A10619): ").strip()
        serial_num = input("Enter Serial Number (e.g., 000001): ").strip()

        file_path = os.path.join(self.DUT_BASE_DIR, part_num, f"{serial_num}.txt")
        
        try:
            target_updates = self.parse_dut_file(file_path)
            if not target_updates:
                print("No parameters extracted from configuration targets. Aborting.")
                return

            print(f"\nConnecting to sensor assembly on Channel {config.CHANNEL}...")
            self.reader.connect()
            self.reader.set_channel(config.CHANNEL)

            if not self.reader.enter_command_mode():
                print("ERROR: Device rejected Command Mode transaction query state.")
                return

            print("Command Mode active. Executing write routines...")
            if self.process_flash_routine(target_updates):
                print("\nCalculating and validating new checksum value...")
                calculate_crc(self.reader)
                print("\nCalibration successfully deployed. Cycle board power.")

        except Exception as e:
            print(f"\nCRITICAL SCRIPT FAULT: {e}")
        finally:
            if hasattr(self.reader, 'inst') and self.reader.inst is not None:
                try:
                    self.reader.disconnect_channel()
                    self.reader.disconnect()
                except Exception:
                    pass

if __name__ == "__main__":
    writer = CalibrationWriter()
    writer.run()