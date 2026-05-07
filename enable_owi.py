import time
import config
from pga305_reader import PGA305Reader


class EnableOWI:

    def __init__(self, channel=1):
        self.channel = channel
        self.reader = PGA305Reader()

    def run(self):
        print("\n" + "="*70)
        print(f"MAKE OWI PERMANENT — CHANNEL {self.channel}")
        print("="*70)

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            print(f"Switching to channel {self.channel}...")
            self.reader.set_channel(self.channel)

            print("Entering command mode...")
            if not self.reader.enter_command_mode():
                print("ERROR: Could not enter command mode")
                return False

            print("Command mode active")

            eeprom_val = self.reader.read_register(0x30, config.EEPROM_ADDR)
            print(f"DIG_IF_CTRL EEPROM (0x25/0x30): 0x{eeprom_val:02X}")

            current_dig = self.reader.read_register(0x06, config.I2C_CONTROL)
            current_owi_int = self.reader.read_register(0x0B, config.I2C_CONTROL)
            current_dlpwr = self.reader.read_register(0x54, config.I2C_CONTROL)

            print(f"\nDIG_IF_CTRL        volatile (0x22/0x06): 0x{current_dig:02X}")
            print(f"OWI_INTERRUPT_EN   volatile (0x22/0x0B): 0x{current_owi_int:02X}")
            print(f"DLPWR              volatile (0x22/0x54): 0x{current_dlpwr:02X}")

            new_dig = current_dig | 0x0C
            new_owi_int = current_owi_int | 0x01
            new_dlpwr = current_dlpwr | 0x01

            print(f"\nStep 1: Writing 0x{new_dig:02X} to DIG_IF_CTRL volatile (0x22/0x06)...")
            if not self.reader.write_register(0x06, new_dig, config.I2C_CONTROL):
                print("ERROR: DIG_IF_CTRL volatile write failed")
                return False
            readback = self.reader.read_register(0x06, config.I2C_CONTROL)
            print(f"DIG_IF_CTRL readback: 0x{readback:02X}")
            if readback != new_dig:
                print("ERROR: DIG_IF_CTRL volatile write did not stick")
                return False
            print("DIG_IF_CTRL volatile write verified")

            print(f"\nStep 2: Writing 0x{new_owi_int:02X} to OWI_INTERRUPT_EN volatile (0x22/0x0B)...")
            if not self.reader.write_register(0x0B, new_owi_int, config.I2C_CONTROL):
                print("ERROR: OWI_INTERRUPT_EN volatile write failed")
                return False
            
            readback_owi_int = self.reader.read_register(0x0B, config.I2C_CONTROL)
            print(f"OWI_INTERRUPT_EN readback: 0x{readback_owi_int:02X}")
            if readback_owi_int != new_owi_int:
                print("ERROR: OWI_INTERRUPT_EN volatile write did not stick")
                return False
            print("OWI_INTERRUPT_EN volatile write verified")

            print(f"\nStep 3: Writing 0x{new_dlpwr:02X} to DLPWR volatile (0x22/0x54)...")
            if not self.reader.write_register(0x54, new_dlpwr, config.I2C_CONTROL):
                print("ERROR: DLPWR volatile write failed")
                return False
            
            readback_dlpwr = self.reader.read_register(0x54, config.I2C_CONTROL)
            print(f"DLPWR readback: 0x{readback_dlpwr:02X}")
            
            if readback_dlpwr != new_dlpwr:
                print("ERROR: DLPWR volatile write did not stick")
                return False
            print("DLPWR volatile write verified ✓")

            print("\nStep 4: Reading current EEPROM page 6 (0x30-0x37)...")
            page = []
            for addr in range(0x30, 0x38):
                val = self.reader.read_register(addr, config.EEPROM_ADDR)
                if val is None:
                    print(f"ERROR: Could not read EEPROM address 0x{addr:02X}")
                    return False
                page.append(val)
                print(f"  0x{addr:02X} = 0x{val:02X}")

            page[0] = new_dig
            print(f"\nStep 5: Modified page[0] (DIG_IF_CTRL) to 0x{new_dig:02X}")
            print(f"  Page to write: {[f'0x{b:02X}' for b in page]}")

            print("\nStep 6: Setting EEPROM page address (0x88 = 0x06)...")
            if not self.reader.write_register(0x88, 0x06, config.EEPROM_ADDR):
                print("ERROR: EEPROM page address write failed")
                return False
            print("EEPROM page address set ")

            print("\nStep 7: Writing 8 bytes to EEPROM cache...")
            cache_addrs = [0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87]
            
            for i, addr in enumerate(cache_addrs):
                if not self.reader.write_register(addr, page[i], config.EEPROM_ADDR):
                    print(f"ERROR: EEPROM cache write failed at 0x{addr:02X}")
                    return False
                print(f"  Cache[{i}] (0x{addr:02X}) = 0x{page[i]:02X} ")


            print("\nStep 8: Triggering ERASE_AND_PROGRAM (0x89 = 0x04)...")
            if not self.reader.write_register(0x89, 0x04, config.EEPROM_ADDR):
                print("ERROR: EEPROM burn trigger failed")
                return False
            print("Burn trigger ACK received ")


            print("Step 9: Waiting for EEPROM burn to complete...")
            for _ in range(20):
                status = self.reader.read_register(0x8B, config.EEPROM_ADDR)
                if status is not None and (status & 0x06) == 0:
                    print(f"EEPROM burn complete (status=0x{status:02X}) ✓")
                    break
                time.sleep(0.1)
            else:
                print("WARNING: EEPROM burn status timed out")

            verify = self.reader.read_register(0x30, config.EEPROM_ADDR)
            if verify is None:
                print("ERROR: Could not verify EEPROM value")
                return False

            print(f"\nDIG_IF_CTRL EEPROM after: 0x{verify:02X} ({verify:08b}b)")
            print(f"  OWI_XCVR_EN (bit 3): {(verify >> 3) & 1}")
            print(f"  OWI_EN      (bit 2): {(verify >> 2) & 1}")
            print(f"  I2C_EN      (bit 1): {(verify >> 1) & 1}")


            print("\nFinal volatile register check:")
            dig_final = self.reader.read_register(0x06, config.I2C_CONTROL)
            owi_int_final = self.reader.read_register(0x0B, config.I2C_CONTROL)
            dlpwr_final = self.reader.read_register(0x54, config.I2C_CONTROL)

            print(f"  DIG_IF_CTRL      (0x22/0x06): 0x{dig_final:02X} — OWI_XCVR_EN: {(dig_final >> 3) & 1}, OWI_EN: {(dig_final >> 2) & 1}")
            print(f"  OWI_INTERRUPT_EN (0x22/0x0B): 0x{owi_int_final:02X} — OWI_INT_EN: {owi_int_final & 1}")
            print(f"  DLPWR            (0x22/0x54): 0x{dlpwr_final:02X} — OWI_CLK_EN: {dlpwr_final & 1}")

            if verify == new_dig:
                print("\nOWI permanently enabled! Power cycle to verify.")
                return True
            else:
                print(f"\nERROR: Verify failed — expected 0x{new_dig:02X}, got 0x{verify:02X}")
                return False

        except Exception as e:
            print(f"\nERROR: {e}")
            return False

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()