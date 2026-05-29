import config
from pga305_reader import PGA305Reader


def test_output():
    reader = PGA305Reader()
    try:
        print(f"Connecting to {config.SERIAL_PORT}...")
        reader.connect()

        print(f"Switching to channel {config.CHANNEL}...")

        print("\nMode: (1) DMM output  (2) Manual DAC drive")
        mode = input("Select [1/2]: ").strip()

        if mode == '1':
            response = reader.send_command(f"mx1{config.CHANNEL:02X}")
            print(f"Response:  {response}")
            print("Record output voltage from the DMM")
            input("Press enter to exit...")

        elif mode == '2':
            reader.send_command(f"mx1{config.CHANNEL:02X}")

            print("Entering command mode...")
            if not reader.enter_command_mode():
                print("ERROR: Could not enter command mode")
                return
            print("Command mode active")

            print("\nEnabling reference buffer (ALPWR only)...")
            reader.write_register(0x50, 0x14, config.I2C_CONTROL)

            print("\nDAC full scale = 12928 (0x3280) = 10V")
            print("Enter DAC code (0-12928) or hex (e.g. 0x1999), x to exit\n")

            while True:
                user_input = input("DAC code: ").strip().lower()

                if user_input == 'x':
                    break

                try:
                    if user_input.startswith('0x'):
                        dac_code = int(user_input, 16)
                    else:
                        dac_code = int(user_input)

                    if dac_code < 0 or dac_code > 12928:
                        print("  ERROR: Value must be 0-12928")
                        continue

                    reader.write_register(0x30, dac_code & 0xFF, config.I2C_CONTROL)
                    reader.write_register(0x31, (dac_code >> 8) & 0xFF, config.I2C_CONTROL)

                    dac1 = reader.read_register(0x30, config.I2C_CONTROL)
                    dac2 = reader.read_register(0x31, config.I2C_CONTROL)
                    readback = (dac2 << 8) | dac1

                    voltage = (dac_code / 12928) * 10.0
                    print(f"  Written:  0x{dac_code:04X} ({dac_code})")
                    print(f"  Readback: 0x{readback:04X} ({readback})")
                    print(f"  Expected: ~{voltage:.3f}V")

                except ValueError:
                    print("  ERROR: Invalid input")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect()
        print("Disconnected.")