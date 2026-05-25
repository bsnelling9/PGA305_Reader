import config
from pga305_reader import PGA305Reader
import time

#clean this up as it has similar functions to calculate_pressure
def labview_style_conversion(p1, p2, p3):
    multiplier = -1 if (p3 // 128) > 0 else 1
    magnitude = ((p3 % 128) << 16) | (p2 << 8) | p1
    return magnitude * multiplier


def calculate_dac_output(reader):
    padc_samples = []
    tadc_samples = []

    for i in range(12):
        p_bytes = reader.read_registers_sequentially(0x20, 3, config.I2C_CONTROL)
        if p_bytes and len(p_bytes) == 3:
            padc_samples.append(labview_style_conversion(p_bytes[0], p_bytes[1], p_bytes[2]))

        t_bytes = reader.read_registers_sequentially(0x24, 3, config.I2C_CONTROL)
        if t_bytes and len(t_bytes) == 3:
            tadc_samples.append(labview_style_conversion(t_bytes[0], t_bytes[1], t_bytes[2]))

        time.sleep(0.02)

    if len(padc_samples) > 0:
        avg_padc = sum(padc_samples) / len(padc_samples)
        avg_tadc = sum(tadc_samples) / len(tadc_samples)

        p_variance = sum((x - avg_padc) ** 2 for x in padc_samples) / len(padc_samples)
        p_std_dev = p_variance ** 0.5

        print(f"  Final PADC (Mean of 12): {avg_padc:.2f}")
        print(f"  PADC Sigma: {p_std_dev:.2f}")

        if p_std_dev > 4000:
            print("  Warning: Signal noise exceeds LabVIEW threshold of 4000")

        print(f"  Final TADC (Mean of 12): {avg_tadc:.2f}")
    else:
        print("  ERROR: Failed to collect samples")
    
def read_dac_passive(reader):

    print("Entering command mode...")
    
    if not reader.enter_command_mode():
        print("ERROR: Could not enter command mode")
        return

    print("Command mode active")

    print("\nEnabling reference buffer (ALPWR only)...")
    reader.write_register(0x50, 0x14, config.I2C_CONTROL)
    alpwr = reader.read_register(0x50, config.I2C_CONTROL)
    print(f"  ALPWR = 0x{alpwr:02X}")

    print("\nReading DAC_REG0 (what M0 last wrote)...")
    dac1 = reader.read_register(0x30, config.I2C_CONTROL)
    dac2 = reader.read_register(0x31, config.I2C_CONTROL)
    if dac1 is not None and dac2 is not None:
        dac_code = (dac2 << 8) | dac1
        print(f"  DAC_REG0_LSB = 0x{dac1:02X}")
        print(f"  DAC_REG0_MSB = 0x{dac2:02X}")
        print(f"  DAC code     = 0x{dac_code:04X} ({dac_code})")
        if dac_code == 0:
            print("  --> M0 wrote zero to DAC — compensation producing no output")
        else:
            print(f"  --> M0 computed a non-zero DAC value!")
    else:
        print("  READ FAILED")

    print("\nReading ADC values...")
    calculate_dac_output(reader)
    
    while True:
        user_input = input("\nEnter r to read data of x to exit: ").strip().lower()

        if user_input == 'r':
            calculate_dac_output(reader)
        elif user_input == 'x':
            break
        else:
            print("Unknown command. Press 'r' to read data or 'x' to quit.")


def test_output():
    reader = PGA305Reader()
    try:
        print(f"Connecting to {config.SERIAL_PORT}...")
        reader.connect()

        print(f"Switching to channel {config.CHANNEL}...")

        print("\nMode: (1) DMM output  (2) passive DAC read")
        mode = input("Select [1/2]: ").strip()

        if mode == '1':
            response = reader.send_command(f"mx1{config.CHANNEL:02X}")
            print(f"Response:  {response}")
            print("Record outout voltage from the DMM")
            # Maybe add script to pull the data from the DMM
            input("Press enter to exit...")

        elif mode == '2':
            reader.send_command(f"mx3{config.CHANNEL:02X}")
            read_dac_passive(reader)

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect()
        print("Disconnected.")


# Step 4 — Write a known DAC value to test output
# 0x1999 = ~25% of full scale (~2.5V with 10V/V gain)
# print("\nStep 4: Writing test DAC value 0x1999 (~25% full scale)...")
# reader.write_register(0x30, 0x99, config.I2C_CONTROL)  # DAC_REG0 LSB
# reader.write_register(0x31, 0x19, config.I2C_CONTROL)  # DAC_REG0 MSB
# dac1 = reader.read_register(0x30, config.I2C_CONTROL)
# dac2 = reader.read_register(0x31, config.I2C_CONTROL)
# print(f"  DAC_REG0 = 0x{(dac2 << 8) | dac1:04X}")
