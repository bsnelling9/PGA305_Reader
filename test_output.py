import config
from pga305_reader import PGA305Reader
#import control_status_registers

def calculate_dac_output(reader):
    padc1 = reader.read_register(0x20, config.I2C_CONTROL)
    padc2 = reader.read_register(0x21, config.I2C_CONTROL)
    padc3 = reader.read_register(0x22, config.I2C_CONTROL)

    padc = (padc3 << 16) | (padc2 << 8) | padc1
    print(f"  PADC = 0x{padc:06X} ({padc})")

    tadc1 = reader.read_register(0x24, config.I2C_CONTROL)
    tadc2 = reader.read_register(0x25, config.I2C_CONTROL)
    tadc3 = reader.read_register(0x26, config.I2C_CONTROL)
    
    tadc = (tadc3 << 16) | (tadc2 << 8) | tadc1       
    print(f"  TADC = 0x{tadc:06X} ({tadc})")


def test_output():
    reader = PGA305Reader()
    enter_command = True
    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        print(f"Switching to channel {config.CHANNEL}...")
        reader.send_command(f"mx2{config.CHANNEL:02X}")

        print("\n Switching to DMM")
        reader.send_command(f"mx3{config.CHANNEL:02X}")
        print(f"mx3{config.CHANNEL:02X}")

        if (enter_command):
            print("Entering command mode...")
            if not reader.enter_command_mode():
                print("ERROR: Could not enter command mode")
                return

            print("Command mode active")

            print("\nStep 1: Enabling reference buffer (ALPWR)...")
            reader.write_register(0x50, 0x14, config.I2C_CONTROL)
            alpwr = reader.read_register(0x50, config.I2C_CONTROL)
            print(f"  ALPWR = 0x{alpwr:02X}")

            print("\nStep 2: Enabling DAC and output stage...")
            ##reader.write_register(0x38, 0xFF, config.I2C_CONTROL)  # DAC_ENABLE=0
            reader.write_register(0x3B, 0x11, config.I2C_CONTROL)  # DACCAP_EN=1, DAC_GAIN=10V/V
            reader.write_register(0x39, 0x00, config.I2C_CONTROL)  # DAC_RATIOMETRIC=0, ratiometic mode is 1
            reader.write_register(0x67, 0x00, config.I2C_CONTROL)  # TEST_MUX_DAC_EN=1

            dac_ctrl = reader.read_register(0x38, config.I2C_CONTROL)
            op_stage = reader.read_register(0x3B, config.I2C_CONTROL)
            amux     = reader.read_register(0x67, config.I2C_CONTROL)
            print(f"  DAC_CTRL_STATUS = 0x{dac_ctrl:02X}            {dac_ctrl}")
            print(f"  OP_STAGE_CTRL   = 0x{op_stage:02X}")
            print(f"  AMUX_CTRL       = 0x{amux:02X}")

            # Step 3 — Read ADC values
            print("\nReading ADC values...")
            calculate_dac_output(reader)
            
            print("\n" + "=" * 70)
            print("OUTPUT READY — Measure voltage with multimeter now")
            print("=" * 70)

            while True:
                user_input = input("\nAction [c/enter]: ").strip().lower()
                
                if user_input == 'c':
                    calculate_dac_output(reader)
                elif user_input == '':
                    break
                else:
                    print("Unknown command. Press 'c' to read data or 'Enter' to quit.")

        # Step 4 — Write a known DAC value to test output
        # 0x1999 = ~25% of full scale (~2.5V with 10V/V gain)
        # print("\nStep 4: Writing test DAC value 0x1999 (~25% full scale)...")
        #reader.write_register(0x30, 0x99, config.I2C_CONTROL)  # DAC_REG0 LSB
        #reader.write_register(0x31, 0x19, config.I2C_CONTROL)  # DAC_REG0 MSB
        #dac1 = reader.read_register(0x30, config.I2C_CONTROL)
        #dac2 = reader.read_register(0x31, config.I2C_CONTROL)
        # print(f"  DAC_REG0 = 0x{(dac2 << 8) | dac1:04X}")

        # Step 5 — Switch to DMM only, stay in command mode
        print("\n Switching to DMM only...")
        reader.send_command(f"mx3{config.CHANNEL:02X}")
     

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        print("Disconnected.")
