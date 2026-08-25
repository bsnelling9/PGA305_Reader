import time
import config
from pga305_reader import PGA305Reader

ALPWR_REG = 0x50
ALPWR_VALUE = 0x14

DAC_REG0_LSB = 0x30
DAC_REG0_MSB = 0x31

DRIFT_CHECK_DELAY_S = 0.3
DRIFT_CHECK_SAMPLES = 3

AMUX_CTRL_REG = 0x67
AMUX_CTRL_DAC_OUTPUT_VALUE = 0x07  # from the original NI trace's "imw226707"


def enable_reference_buffer(reader) -> bool:
    """
    Enables the reference buffer (ALPWR). Confirmed against a real NI trace:
    imw225014 (0x22/0x50 = 0x14), read back as 0x14 via imr2250.
    """
    if not reader.write_register(ALPWR_REG, ALPWR_VALUE, config.I2C_CONTROL):
        print("ERROR: Failed to enable reference buffer (ALPWR)")
        return False
    alpwr = reader.read_register(ALPWR_REG, config.I2C_CONTROL)
    print(f"  ALPWR = 0x{alpwr:02X}")
    return True


def set_amux_ctrl(reader, value: int = AMUX_CTRL_DAC_OUTPUT_VALUE) -> bool:
    """
    Writes AMUX_CTRL (0x22/0x67) — the analog mux control register that
    routes internal signals, including the DAC output, to the measurable
    pin. Present in the original NI trace right after every DAC code write
    and before switching to the DMM channel, but missing entirely from the
    later confirmed-working trace — plausible explanation for a fixed
    voltage that doesn't track the code: DAC_REG0 is being written
    correctly, but the mux isn't routing it anywhere the DMM can see.

    The value (0x07) is taken directly from the trace; the actual bit
    meaning isn't confirmed. Reads back before/after so you can see if it's
    already at 0x07 by default (in which case this isn't the fix) or if it
    changes something.
    """
    before = reader.read_register(AMUX_CTRL_REG, config.I2C_CONTROL)
    print(f"  AMUX_CTRL before = 0x{before:02X}" if before is not None else "  AMUX_CTRL before = READ FAILED")

    if not reader.write_register(AMUX_CTRL_REG, value, config.I2C_CONTROL):
        print("ERROR: Failed to write AMUX_CTRL")
        return False

    after = reader.read_register(AMUX_CTRL_REG, config.I2C_CONTROL)
    print(f"  AMUX_CTRL after  = 0x{after:02X}" if after is not None else "  AMUX_CTRL after  = READ FAILED")

    return after is not None


def write_dac_test_code(reader, code: int) -> bool:
    """
    Writes a raw 16-bit test code to DAC_REG0 (0x30 = LSB, 0x31 = MSB).

    Confirmed against a real NI trace (mx302 / cm_20 / imw225014 / imw2230E0
    / imw223125 / imr2230 / imr2231 for code 9696 = 0x25E0): the write holds
    and reads back exactly what was written, immediately, with no drift at
    the register level. So if the DMM voltage isn't tracking the code, the
    problem is downstream of this write (output stage routing/config or the
    measurement path), not the register write itself.
    """
    if not (0 <= code <= 0xFFFF):
        print(f"ERROR: DAC test code {code} out of 16-bit range (0-65535)")
        return False

    lsb = code & 0xFF
    msb = (code >> 8) & 0xFF

    if not reader.write_register(DAC_REG0_LSB, lsb, config.I2C_CONTROL):
        print(f"ERROR: Failed to write DAC_REG0_LSB for code {code}")
        return False

    if not reader.write_register(DAC_REG0_MSB, msb, config.I2C_CONTROL):
        print(f"ERROR: Failed to write DAC_REG0_MSB for code {code}")
        return False

    rb_lsb = reader.read_register(DAC_REG0_LSB, config.I2C_CONTROL)
    rb_msb = reader.read_register(DAC_REG0_MSB, config.I2C_CONTROL)

    if rb_lsb is None or rb_msb is None:
        print(f"DAC test code {code} (0x{code:04X}) written — readback FAILED")
        return True

    rb_code = (rb_msb << 8) | rb_lsb
    print(f"DAC test code {code} (0x{code:04X}) written — "
          f"readback = 0x{rb_code:04X} ({rb_code})")

    if rb_code != code:
        print("  WARNING: readback does not match what was written.")

    print("Setting AMUX_CTRL to route DAC output...")
    if not set_amux_ctrl(reader):
        print("ERROR: Failed to set AMUX_CTRL")
        return False

    # Diagnostic only: confirms register-level stability over a short
    # window. Does not diagnose the output stage — if this holds steady
    # but the DMM voltage still doesn't move, look elsewhere (DAC output
    # routing/enable, OP_STAGE_CTRL, or which physical node mx1 measures).
    for i in range(DRIFT_CHECK_SAMPLES):
        time.sleep(DRIFT_CHECK_DELAY_S)
        chk_lsb = reader.read_register(DAC_REG0_LSB, config.I2C_CONTROL)
        chk_msb = reader.read_register(DAC_REG0_MSB, config.I2C_CONTROL)
        if chk_lsb is None or chk_msb is None:
            continue
        chk_code = (chk_msb << 8) | chk_lsb
        print(f"  [check {i+1}] DAC_REG0 = 0x{chk_code:04X} ({chk_code})")

    return True


def dac_output_test():
    reader = PGA305Reader()

    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        channel = config.CHANNEL
        print(f"Using channel {channel} (edit config.CHANNEL to change)")

        print(f"\nSwitching to channel {channel}, mode 3 (I2C write path)...")
        reader.send_command(f"mx3{channel:02X}")

        if not reader.enter_command_mode():
            print("ERROR: Could not enter command mode")
            return

        print("Command mode active")
        print("\nEnabling reference buffer (ALPWR)...")
        if not enable_reference_buffer(reader):
            return

        print("\n" + "=" * 70)
        print(" " * 20 + "DAC OUTPUT TEST (manual code -> DMM)")
        print("=" * 70)
        print("Enter a raw DAC test code (0-65535). It writes the code to the")
        print("DAC, then switches to the DMM channel so you can read the")
        print("output voltage. Type 'x' to exit.")
        print("-" * 70)

        while True:
            user_input = input(f"\n[Ch {channel}] DAC test code (or x): ").strip().lower()

            if user_input == 'x':
                break

            try:
                code = int(user_input)
            except ValueError:
                print("  Enter an integer code or 'x' to exit.")
                continue

            if not write_dac_test_code(reader, code):
                continue

            print("Switching to DMM channel...")
            reader.send_command(f"mx1{channel:02X}")
            input("Record the output voltage, then press Enter for the next code...")

            reader.send_command(f"mx3{channel:02X}")
            if not reader.enter_command_mode():
                print("ERROR: Could not re-enter command mode after DMM switch")
                break
            if not enable_reference_buffer(reader):
                break

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        if reader.inst:
            reader.disconnect_channel()
            reader.disconnect()
        print("\nDisconnected.")