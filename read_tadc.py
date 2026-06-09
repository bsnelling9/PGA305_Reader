import config
from pga305_reader import PGA305Reader

## this will be removed as its in another function
class ReadTADC:

    def __init__(self, channel=1):
        self.channel = channel
        self.reader = PGA305Reader()

    def run(self):
        print("\n" + "="*70)
        print("READ TADC - CHANNEL", self.channel)
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

            tadc = self._read_tadc()

            if tadc is None:
                print("✗ ERROR: Failed to read TADC registers")
                return

            print("\n" + "="*70)
            print("RESULT")
            print("="*70)
            print(f"TADC bytes: LSB=0x{tadc['lsb']:02X}  MID=0x{tadc['mid']:02X}  MSB=0x{tadc['msb']:02X}")
            print(f"TADC value: {tadc['value']}")

            if 1400000 < tadc['value'] < 3000000:
                print("TADC: Valid range")
            else:
                print("TADC: Outside expected range (1,400,000 to 3,000,000)")

            print("="*70)

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _read_tadc(self):
        lsb = self.reader.read_register(0x24, config.I2C_CONTROL)
        mid = self.reader.read_register(0x25, config.I2C_CONTROL)
        msb = self.reader.read_register(0x26, config.I2C_CONTROL)

        if None in [lsb, mid, msb]:
            return None

        raw = (msb << 16) | (mid << 8) | lsb
        if raw > 8388607:
            raw -= 16777216

        return {'lsb': lsb, 'mid': mid, 'msb': msb, 'value': raw}