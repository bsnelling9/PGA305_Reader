import sys
import time
import config
from pga305_reader import PGA305Reader
from scripts.gpio_diagnostic import run_gpio_diagnostic
from scripts.verify_calibration import run_calibration_verification
from read_tadc import ReadTADC
from read_eeprom import ReadEEPROM
from write_eeprom import WriteEEPROM
from verify_coefficients import VerifyCoefficients
from scan_mux_channels import ScanMuxChannels
from enable_owi import EnableOWI
from handle_uart import HandleUART
from read_control_registers import ReadControlRegisters
from test_output import test_output
from calculate_pressure import calculate_pressure
from reset_eeprom import ResetEEPROM
from write_calibration import CalibrationWriter
from helpers.calculate_crc import calculate_crc

def print_header():
    print("\n" + "="*70)
    print(" "*20 + "PGA305 SENSOR READER")
    print("="*70)


def print_menu():
    print("\nMAIN MENU:")
    print("-" * 70)
    print("  1.  Read sensor data (Part Number, Serial Number, PRange)")
    print("  2.  Scan all channels for programmed sensors")
    print("  3.  Run GPIO diagnostic test (check for damaged STM32 pins)")
    print("  4.  Verify PGA305 calibration")
    print("  5.  Read TADC")
    print("  6.  Read EEPROM configuration")
    print("  7.  Verify coefficients against DUT file")
    print("  8.  Timing diagnostic scan (all channels, multiple iterations)")
    print("  9.  Enable OWI")
    print("  10. Handle UART")
    print("  11. Read Control Registers")
    print("  12. Write EEPROM register")
    print("  13. Read passive (compensation control + DAC)")
    print("  14. Read AMUX_CTRL")
    print("  15. Test standalone output")
    print("  16. Write Calibration Coefficients and Settings")
    print("  a.  Calculate/verify EEPROM CRC")
    print("  b.  Calculate pressure (P)")
    print("  0.  Exit")
    print("-" * 70)

def read_passive():
    reader = PGA305Reader()

    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        print(f"Switching to channel {config.CHANNEL}...")
        reader.set_channel(config.CHANNEL)

        crc_status = reader.read_register(0x8C, config.I2C_CONTROL)
        print(f"EEPROM_CRC_STATUS = 0x{crc_status:02X}")

        comp_ctrl = reader.read_register(0x0C, config.PGA305_I2C_ADDR)
        if comp_ctrl is not None:
            print(f"\nBEFORE command mode:")
            print(f"COMPENSATION_CONTROL = 0x{comp_ctrl:02X}")
            print(f"  IF_SEL      (bit 1): {(comp_ctrl >> 1) & 1}")
            print(f"  MICRO_RESET (bit 0): {comp_ctrl & 1}")
        else:
            print("READ FAILED before command mode")

        dac_reg0_1 = reader.read_register(0x30, config.I2C_CONTROL)
        dac_reg0_2 = reader.read_register(0x31, config.I2C_CONTROL)
        
        if dac_reg0_1 is not None and dac_reg0_2 is not None:
            dac_code = (dac_reg0_2 << 8) | dac_reg0_1
            print(f"\nDAC_REG0_1 (0x22/0x30) = 0x{dac_reg0_1:02X}")
            print(f"DAC_REG0_2 (0x22/0x31) = 0x{dac_reg0_2:02X}")
            print(f"DAC code = 0x{dac_code:04X} ({dac_code})")
        
        else:
            print("READ FAILED")

        print("\nEntering command mode...")
        
        if not reader.enter_command_mode():
            print("ERROR: Could not enter command mode")
            return

        comp_ctrl = reader.read_register(0x0C, config.PGA305_I2C_ADDR)
        
        if comp_ctrl is not None:
            print(f"\nAFTER command mode:")
            print(f"COMPENSATION_CONTROL = 0x{comp_ctrl:02X}")
            print(f"  IF_SEL      (bit 1): {(comp_ctrl >> 1) & 1}")
            print(f"  MICRO_RESET (bit 0): {comp_ctrl & 1}")
        
        else:
            print("READ FAILED after command mode")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect_channel()
        reader.disconnect()


def read_amux_ctrl():
    reader = PGA305Reader()

    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        print(f"Switching to channel {config.CHANNEL}...")
        reader.set_channel(config.CHANNEL)

        amux_ctrl = reader.read_register(0x67, config.I2C_CONTROL)
        if amux_ctrl is not None:
            print(f"\nAMUX_CTRL (0x22/0x67) = 0x{amux_ctrl:02X} ({amux_ctrl:08b}b)")
            print(f"  TEST_MUX_DAC_EN (bit 0): {amux_ctrl & 1}")
            print(f"  TEST_MUX_P_EN   (bit 1): {(amux_ctrl >> 1) & 1}")
            print(f"  TEST_MUX_T_EN   (bit 2): {(amux_ctrl >> 2) & 1}")
            print(f"  TSEM_N          (bit 3): {(amux_ctrl >> 3) & 1}")
        else:
            print("READ FAILED")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect_channel()
        reader.disconnect()


def read_single_sensor():
    print_header()
    print("READ SENSOR DATA")
    print("=" * 70)

    channel = config.CHANNEL
    if channel < 0 or channel > 7:
        print("ERROR: Channel must be between 0 and 7")
        return

    reader = PGA305Reader()

    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        board_id = reader.get_board_identity()
        print(f"Board: {board_id}")

        data = reader.read_sensor_data(channel)

        if data:
            print("\n" + "=" * 70)
            print("RESULT")
            print("=" * 70)
            print(f"Part Number:   {data['part_number']}")
            print(f"Serial Number: {data['serial_number']}")
            if data['prange'] is not None:
                print(f"PRange:        {data['prange']}")
            print("=" * 70)

            if data['serial_number'] == 0 and data['part_number'] in ['A0', 'S0']:
                print("\nNote: This sensor appears to be blank/unprogrammed")
        else:
            print("\nERROR: Failed to read sensor data")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        reader.disconnect()


def scan_all_channels():
    print_header()
    print("SCANNING ALL CHANNELS")
    print("=" * 70)

    reader = PGA305Reader()

    try:
        reader.connect()

        for channel in range(8):
            print(f"\n--- Channel {channel} ---")
            data = reader.read_sensor_data(channel, verbose=False)

            if data:
                print(f"  Part Number:   {data['part_number']}")
                print(f"  Serial Number: {data['serial_number']}")
                if data['prange'] is not None:
                    print(f"  PRange:        {data['prange']}")
                if data['serial_number'] != 0 or data['part_number'] not in ['A0', 'S0']:
                    print(f"  PROGRAMMED SENSOR")
                else:
                    print(f"  (blank/unprogrammed)")
            else:
                print("  No response")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect()
        print("\n" + "=" * 70)
        print("SCAN COMPLETE")
        print("=" * 70)


def main():
    while True:
        print_header()
        print_menu()

        choice = input("\nSelect option (0-16): ").strip()

        if choice == '0':
            print("\nExiting...")
            sys.exit(0)
        elif choice == '1':
            read_single_sensor()
        elif choice == '2':
            scan_all_channels()
        elif choice == '3':
            run_gpio_diagnostic()
        elif choice == '4':
            run_calibration_verification()
        elif choice == '5':
            ReadTADC(channel=config.CHANNEL).run()
        elif choice == '6':
            ReadEEPROM(channel=config.CHANNEL).run()
        elif choice == '7':
            VerifyCoefficients(channel=config.CHANNEL).run()
        elif choice == '8':
            ScanMuxChannels(iterations=config.SCAN_ITERATIONS).run()
        elif choice == '9':
            EnableOWI(channel=config.CHANNEL).run()
        elif choice == '10':
            HandleUART(channel=config.CHANNEL).run()
        elif choice == '11':
            ReadControlRegisters(channel=config.CHANNEL).run()
        elif choice == '12':
            WriteEEPROM(channel=config.CHANNEL).run()
        elif choice == '13':
            read_passive()
        elif choice == '14':
            read_amux_ctrl()
        elif choice == '15':
            test_output()
        #this will not pass the channel as it will always be channel 1
        # This function will only be on my computer and not on the cal stations
        elif choice == '16':
            CalibrationWriter().run()
        elif choice == 'a':
            calculate_crc()
        elif choice == 'b':
            calculate_pressure()
        elif choice == 'c':
            ResetEEPROM(channel=config.CHANNEL).run()
        else:
            print("\nInvalid choice. Please select 0-15.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()