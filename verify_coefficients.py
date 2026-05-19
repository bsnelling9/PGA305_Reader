import os
import configparser
import config
from pga305_reader import PGA305Reader
from eeprom_addresses import EEPROM_REGISTERS

# Coefficient names — order matches DUT file
COEFF_NAMES = ['h0','h1','h2','h3','g0','g1','g2','g3',
               'n0','n1','n2','n3','m0','m1','m2','m3']


def _build_coeff_map() -> dict:
    """Build coefficient address map from EEPROM_REGISTERS."""
    result = {}
    addr_by_label = {v: k for k, v in EEPROM_REGISTERS.items()}
    for name in COEFF_NAMES:
        lsb = f"{name.upper()}_LSB"
        mid = f"{name.upper()}_MID"
        msb = f"{name.upper()}_MSB"
        if lsb in addr_by_label and mid in addr_by_label and msb in addr_by_label:
            result[name] = (addr_by_label[lsb], addr_by_label[mid], addr_by_label[msb])
    return result


COEFFICIENTS = _build_coeff_map()


class VerifyCoefficients:
    """
    Uses PGA305Reader to read the sensor serial number and part number,
    locates the matching DUT file in DUTs/<part_number>/<serial_number>.txt,
    then compares every coefficient against the EEPROM.
    Addresses sourced from eeprom_addresses.py.
    """

    DUT_BASE_DIR = "DUTs"

    def __init__(self, channel=None):
        self.channel = channel or config.CHANNEL
        self.reader  = PGA305Reader()

    def run(self):
        
        failed_matches = []
        print("\n" + "="*70)
        print(f"VERIFY COEFFICIENTS — CHANNEL {self.channel}")
        print("="*70)

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            print(f"Reading sensor identity on channel {self.channel}...")
            sensor = self.reader.read_sensor_data(self.channel, verbose=False)

            if sensor is None:
                print(" ERROR: Could not read sensor identity")
                return

            part_number = sensor['part_number']
            serial_number = sensor['serial_number']
            serial_str = f"{serial_number:06d}"

            print(f"  Part Number:   {part_number}")
            print(f"  Serial Number: {serial_str}")

            dut_path = os.path.join(self.DUT_BASE_DIR, part_number, f"{serial_str}.txt")
            print(f"  DUT file:      {dut_path}")

            dut_coeffs = self._load_dut_coefficients(dut_path)
            if dut_coeffs is None:
                return

            print("\nEntering command mode...")
            self.reader.set_channel(self.channel)
            
            if not self.reader.enter_command_mode():
                print(" ERROR: Could not enter command mode")
                return

            print("Command mode active ")
            print("\nComparing coefficients...\n")

            all_match = True
            filename = os.path.basename(dut_path)

            for name, (lsb_addr, mid_addr, msb_addr) in COEFFICIENTS.items():
                dut_value = dut_coeffs.get(name, '').strip()

                print(f"--- {name} ---")
                print(f'  DUT file: {name} = "{dut_value}"')

                lsb = self.reader.read_register(lsb_addr, config.EEPROM_ADDR)
                mid = self.reader.read_register(mid_addr, config.EEPROM_ADDR)
                msb = self.reader.read_register(msb_addr, config.EEPROM_ADDR)

                if None in [lsb, mid, msb]:
                    print(f"  PGA305: READ FAILED")
                    all_match = False
                    continue

                print(f"  PGA305:")
                print(f"    0x{lsb_addr:02X}  {name.upper()}_LSB  0x{lsb:02X}  ({lsb:3d})")
                print(f"    0x{mid_addr:02X}  {name.upper()}_MID  0x{mid:02X}  ({mid:3d})")
                print(f"    0x{msb_addr:02X}  {name.upper()}_MSB  0x{msb:02X}  ({msb:3d})")

                eeprom_hex  = f"{msb:02X}{mid:02X}{lsb:02X}".upper()
                eeprom_zero = (lsb == 0 and mid == 0 and msb == 0)

                if dut_value == '':
                    if eeprom_zero:
                        print(f'  PGA305: {eeprom_hex} and DUT file: "" — both empty')
                    else:
                        print(f'  DUT file is empty but PGA305 has: {eeprom_hex}')
                        all_match = False
                else:
                    match  = eeprom_hex.upper() == dut_value.upper()
                    status = "MATCH" if match else "NO MATCH"
                    print(f"  PGA305: {eeprom_hex} and {filename}: {dut_value}")
                    print(f"  PGA305 and {filename} {status}")
                    
                    if not match:
                        all_match = False
                        failed_matches.append(name)
                print()

            print("="*70)
            
            if all_match:
                print("ALL COEFFICIENTS MATCH")
            else:
                print("COEFFICIENTS that do not match:")
                print(failed_matches)
            
            print("="*70)

        except Exception as e:
            print(f"\n ERROR: {e}")

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _load_dut_coefficients(self, dut_path: str) -> dict:
        """Load coefficient values from DUT file."""
        if not os.path.exists(dut_path):
            print(f" ERROR: DUT file not found: {dut_path}")
            return None

        parser = configparser.ConfigParser()
        parser.optionxform = str

        try:
            parser.read(dut_path)
        
        except Exception as e:
            print(f"ERROR reading DUT file: {e}")
            return None

        if 'Coefficients' not in parser:
            print(f" ERROR: No [Coefficients] section in {dut_path}")
            return None

        coeffs = {}
        
        for key, value in parser['Coefficients'].items():
            coeffs[key.lower()] = value.strip('"').strip()

        print(f"  [Coefficients loaded from {os.path.basename(dut_path)}]")
        
        return coeffs