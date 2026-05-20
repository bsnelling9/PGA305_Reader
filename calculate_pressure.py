import config
from pga305_reader import PGA305Reader


def labview_padc(p1, p2, p3):
    """This follows the same conversion that is in labview"""
    multiplier = -1 if (p3 // 128) > 0 else 1
    magnitude = ((p3 % 128) << 16) | (p2 << 8) | p1
    return magnitude * multiplier


def to_signed_24(v):
    """Convert unsigned 24-bit value to signed integer (for PADC_OFFSET)."""
    return v - 0x1000000 if v & 0x800000 else v


def read_and_calculate(reader, padc_gain, padc_offset, tadc_gain, tadc_offset, off_en):
    
    p_bytes = reader.read_registers_sequentially(0x20, 3, config.I2C_CONTROL)
    p1, p2, p3 = p_bytes[0], p_bytes[1], p_bytes[2]

    if None in (p1, p2, p3):
        print("  ERROR: Could not read PADC")
        return

    print(f" p1=0x{p1:02X} p2=0x{p2:02X} p3=0x{p3:02X}")
    print(f" Raw: p1={p1} p2={p2} p3={p3}")

    t_bytes = reader.read_registers_sequentially(0x24, 3, config.I2C_CONTROL)
    t1, t2, t3 = t_bytes[0], t_bytes[1], t_bytes[2]

    print(f" t1=0x{t1:02X} t2=0x{t2:02X} t3=0x{t3:02X}")
    print(f" Raw: t1={t1} t2={t2} t3={t3}")

    padc_raw = labview_padc(p1, p2, p3)
    tadc_raw = labview_padc(t1, t2, t3)

    if off_en:
        P = padc_gain * (padc_raw + padc_offset)
        T = tadc_gain * (tadc_raw + tadc_offset)
        P_normalized = P / 4194304
        T_normalized = T / 4194304
        
        print(f"  P = {padc_gain} x ({padc_raw} + {padc_offset})")
        print(f"    = {padc_gain} x {padc_raw + padc_offset}")
        print(f"  T = {tadc_gain} x ({tadc_raw} + {tadc_offset})")
        print(f"    = {tadc_gain} x {tadc_raw + tadc_offset}")
    else:
        P = padc_gain * padc_raw + padc_offset
        T = tadc_gain * tadc_raw + tadc_offset
        P_normalized = P / 4194304
        T_normalized = T / 4194304
        
        print(f"  P = {padc_gain} x {padc_raw} + {padc_offset}")
        print(f"  T = {tadc_gain} x {tadc_raw} + {tadc_offset}")

    dac_bytes = reader.read_registers_sequentially(0x30, 2, config.I2C_CONTROL)
    if dac_bytes and len(dac_bytes) == 2:
        dac_code = (dac_bytes[1] << 8) | dac_bytes[0]
    else:
        dac_code = None

    print(f"\n  PADC_RAW     = {padc_raw} (0x{padc_raw & 0xFFFFFF:06X})")
    print(f"  PADC_GAIN    = {padc_gain}")
    print(f"  PADC_OFFSET  = {padc_offset}")
    print(f"  P            = {P}")
    print(f"  P_normalized = {P_normalized:.6f}")
    print(f"\n  TADC_RAW     = {tadc_raw} (0x{tadc_raw & 0xFFFFFF:06X})")
    print(f"  TADC_GAIN    = {tadc_gain}")
    print(f"  TADC_OFFSET  = {tadc_offset}")
    print(f"  T            = {T}")
    print(f"  T_normalized = {T_normalized:.6f}")
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

        tgain_lsb = reader.read_register(0x5E, config.EEPROM_ADDR)
        tgain_mid = reader.read_register(0x5F, config.EEPROM_ADDR)
        tgain_msb = reader.read_register(0x60, config.EEPROM_ADDR)

        if None in (tgain_lsb, tgain_mid, tgain_msb):
            print("ERROR: Could not read TADC_GAIN")
            return

        tadc_gain = (tgain_msb << 16) | (tgain_mid << 8) | tgain_lsb

        toff_lsb = reader.read_register(0x61, config.EEPROM_ADDR)
        toff_mid = reader.read_register(0x62, config.EEPROM_ADDR)
        toff_msb = reader.read_register(0x63, config.EEPROM_ADDR)

        if None in (toff_lsb, toff_mid, toff_msb):
            print("ERROR: Could not read TADC_OFFSET")
            return

        tadc_offset = to_signed_24((toff_msb << 16) | (toff_mid << 8) | toff_lsb)

        off_en_reg = reader.read_register(0x69, config.EEPROM_ADDR)
        if off_en_reg is None:
            print("ERROR: Could not read OFFSET_ENABLE")
            return
        
        off_en = off_en_reg & 1

        print(f"\n PADC_GAIN   = {padc_gain} (0x{padc_gain:06X})")
        print(f"  PADC_OFFSET = {padc_offset} (0x{padc_offset & 0xFFFFFF:06X})")
        print(f"  TADC_GAIN   = {tadc_gain} (0x{tadc_gain:06X})")
        print(f"  TADC_OFFSET = {tadc_offset} (0x{tadc_offset & 0xFFFFFF:06X})")
        print(f"  OFF_EN      = {off_en}")
        
        if off_en:
            print(f"  Equation:   P = PGAIN x (PADC + POFFSET)  [Eq. 4]")
            print(f"  Equation:   T = TGAIN x (TADC + TOFFSET)  [Eq. 5]")
        else:
            print(f"  Equation:   P = PGAIN x PADC + POFFSET    [Eq. 2]")
            print(f"  Equation:   T = TGAIN x TADC + TOFFSET    [Eq. 3]")

        print("\n" + "=" * 70)
        read_and_calculate(reader, padc_gain, padc_offset, tadc_gain, tadc_offset, off_en)
        print("\n" + "=" * 70)
        print("  r = read again   x = exit")
        print("=" * 70)

        while True:
            user_input = input("\nAction [r/x]: ").strip().lower()
            if user_input == 'x':
                break
            elif user_input == 'r':
                read_and_calculate(reader, padc_gain, padc_offset, tadc_gain, tadc_offset, off_en)
            else:
                print("  Type 'r' to read again or 'x' to exit.")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect_channel()
        reader.disconnect()
        print("\nDisconnected.")