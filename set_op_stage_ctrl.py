import config
from pga305_reader import PGA305Reader
from eeprom_addresses import *
from helpers.calculate_crc import calculate_crc
from reset_coefficients import process_flash_routine

OP_STAGE_CTRL_OPTIONS = {
    "1": (CURRENT_MODE,  "Current mode 4-20 mA (default)"),
    "2": (DAC_GAIN_4V,   "Voltage 4 V/V"),
    "3": (DAC_GAIN_667V, "Voltage 6.67 V/V"),
    "4": (DAC_GAIN_10V,  "Voltage 10 V/V"),
}


def set_channel_op_stage(channel, value):
    print("\n" + "=" * 70)
    print(f"SET OP_STAGE_CTRL = 0x{value:02X} — CHANNEL {channel}")
    print("=" * 70)

    reader = PGA305Reader()

    try:
        reader.connect()
        reader.set_channel(channel)

        if not reader.enter_command_mode():
            print("ERROR: failed to enter Command mode")
            return False

        before = reader.read_register(OP_STAGE_CTRL_ADDR, config.EEPROM_ADDR)
        if before is None:
            print("ERROR: could not read OP_STAGE_CTRL")
            return False
        print(f"OP_STAGE_CTRL before: 0x{before:02X}")

        if not process_flash_routine(reader, {OP_STAGE_CTRL_ADDR: value}):
            print("CRITICAL: page 6 write failed.")
            return False

        print("Calculating CRC...")
        calculate_crc(reader)

        after = reader.read_register(OP_STAGE_CTRL_ADDR, config.EEPROM_ADDR)
        if after != value:
            got = "no response" if after is None else f"0x{after:02X}"
            print(f"MISMATCH: expected 0x{value:02X}, got {got}")
            return False

        print(f"Channel {channel}: OP_STAGE_CTRL = 0x{after:02X} verified OK.")
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        return False

    finally:
        reader.disconnect_channel()
        reader.disconnect()


def run():
    try:
        start = int(input("\nStart channel: ").strip())
        end = int(input("End channel: ").strip())
    except ValueError:
        print("Invalid channel number")
        return

    if not (0 <= start <= end <= 7):
        print("Channels must be 0-7 and start <= end")
        return

    print("\nOP_STAGE_CTRL value:")
    for key, (val, label) in OP_STAGE_CTRL_OPTIONS.items():
        print(f"  {key}: 0x{val:02X}  {label}")
    choice = input("Select value: ").strip()
    if choice not in OP_STAGE_CTRL_OPTIONS:
        print("Invalid selection")
        return
    value = OP_STAGE_CTRL_OPTIONS[choice][0]

    results = {ch: set_channel_op_stage(ch, value) for ch in range(start, end + 1)}

    print("\nSummary:")
    for ch, ok in results.items():
        print(f"  Channel {ch}: {'OK' if ok else 'FAILED'}")


if __name__ == "__main__":
    run()