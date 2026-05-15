import config
from pga305_reader import PGA305Reader


def labview_padc(p1, p2, p3):
    """LabVIEW-style sign-magnitude conversion for 24-bit PADC."""
    multiplier = -1 if (p3 // 128) > 0 else 1
    magnitude = ((p3 % 128) << 16) | (p2 << 8) | p1
    return magnitude * multiplier


def to_signed_24(v):
    """Convert unsigned 24-bit value to signed integer (for PADC_OFFSET)."""
    return v - 0x1000000 if v & 0x800000 else v


def read_and_calculate(reader, padc_gain, padc_offset, off_en):
    for _ in range(2):
        p1 = reader.read_register(0x20, config.I2C_CONTROL)
        p2 = reader.read_register(0x21, config.I2C_CONTROL)
        p3 = reader.read_register(0x22, config.I2C_CONTROL)

    if None in (p1, p2, p3):
        print("  ERROR: Could not read PADC")
        return

    print(f"  Raw bytes: p1=0x{p1:02X} p2=0x{p2:02X} p3=0x{p3:02X}")

    padc_raw = labview_padc(p1, p2, p3)

    if off_en:
        P = padc_gain * (padc_raw + padc_offset)
        P_normalized = P / 4194304
        print(f"  P = {padc_gain} x ({padc_raw} + {padc_offset})")
        print(f"    = {padc_gain} x {padc_raw + padc_offset}")
    else:
        P = padc_gain * padc_raw + padc_offset
        P_normalized = P / 4194304
        print(f"  P = {padc_gain} x {padc_raw} + {padc_offset}")

    dac1 = reader.read_register(0x30, config.I2C_CONTROL)
    dac2 = reader.read_register(0x31, config.I2C_CONTROL)
    dac_code = ((dac2 << 8) | dac1) if None not in (dac1, dac2) else None

    print(f"\n  PADC_RAW     = {padc_raw} (0x{padc_raw & 0xFFFFFF:06X})")
    print(f"  PADC_GAIN    = {padc_gain}")
    print(f"  PADC_OFFSET  = {padc_offset}")
    print(f"  P            = {P}")
    print(f"  P_normalized = {P_normalized:.6f}")
    if dac_code is not None:
        print(f"  DAC_REG0     = {dac_code} (0x{dac_code:04X})")


def calculate_pressure():
    reader = PGA305Reader()

    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        print(f"Switching to channel {config.CHANNEL}...")
        reader.set_channel(config.CHANNEL)

        print("Entering command mode...")
        if not reader.enter_command_mode():
            print("ERROR: Could not enter command mode")
            return

        print("Command mode active\n")
        print("Reading EEPROM settings (read once)...")

        gain_lsb = reader.read_register(0x44, config.EEPROM_ADDR)
        gain_mid = reader.read_register(0x45, config.EEPROM_ADDR)
        gain_msb = reader.read_register(0x46, config.EEPROM_ADDR)
        if None in (gain_lsb, gain_mid, gain_msb):
            print("ERROR: Could not read PADC_GAIN")
            return
        padc_gain = (gain_msb << 16) | (gain_mid << 8) | gain_lsb

        off_lsb = reader.read_register(0x47, config.EEPROM_ADDR)
        off_mid = reader.read_register(0x48, config.EEPROM_ADDR)
        off_msb = reader.read_register(0x49, config.EEPROM_ADDR)
        if None in (off_lsb, off_mid, off_msb):
            print("ERROR: Could not read PADC_OFFSET")
            return
        padc_offset = to_signed_24((off_msb << 16) | (off_mid << 8) | off_lsb)

        off_en_reg = reader.read_register(0x69, config.EEPROM_ADDR)
        if off_en_reg is None:
            print("ERROR: Could not read OFFSET_ENABLE")
            return
        off_en = off_en_reg & 1

        print(f"\n  PADC_GAIN   = {padc_gain} (0x{padc_gain:06X})")
        print(f"  PADC_OFFSET = {padc_offset} (0x{padc_offset & 0xFFFFFF:06X})")
        print(f"  OFF_EN      = {off_en}")
        if off_en:
            print(f"  Equation:   P = PGAIN x (PADC + POFFSET)  [Eq. 4]")
        else:
            print(f"  Equation:   P = PGAIN x PADC + POFFSET    [Eq. 2]")

        print("\n" + "=" * 70)
        read_and_calculate(reader, padc_gain, padc_offset, off_en)
        print("\n" + "=" * 70)
        print("  r = read again   q = quit")
        print("=" * 70)

        while True:
            user_input = input("\nAction [r/q]: ").strip().lower()
            if user_input == 'q':
                break
            elif user_input == 'r':
                read_and_calculate(reader, padc_gain, padc_offset, off_en)
            else:
                print("  Type 'r' to read again or 'q' to quit.")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect_channel()
        reader.disconnect()
        print("\nDisconnected.")