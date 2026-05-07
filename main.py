import sys
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

def print_header():
    print("\n" + "="*70)
    print(" "*20 + "PGA305 SENSOR READER")
    print("="*70)


def print_menu():
    print("\nMAIN MENU:")
    print("-" * 70)
    print("  1. Read sensor data (Part Number, Serial Number, PRange)")
    print("  2. Scan all channels for programmed sensors")
    print("  3. Run GPIO diagnostic test (check for damaged STM32 pins)")
    print("  4. Verify PGA305 calibration")
    print("  5. Read TADC")
    print("  6. Read EEPROM configuration")
    print("  7. Verify coefficients against DUT file")
    print("  8. Timing diagnostic scan (all channels, multiple iterations)")
    print("  9. Enable OWI")
    print("  10. Handle UART")
    print("  11. Read Control Registers")
    print("  12. Write EEPROM register")
    print("  0. Exit")
    print("-" * 70)


def read_single_sensor():
    print_header()
    print("READ SENSOR DATA")
    print("="*70)

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
            print("\n" + "="*70)
            print("RESULT")
            print("="*70)
            print(f"Part Number:   {data['part_number']}")
            print(f"Serial Number: {data['serial_number']}")
            if data['prange'] is not None:
                print(f"PRange:        {data['prange']}")
            print("="*70)

            if data['serial_number'] == 0 and data['part_number'] in ['A0', 'S0']:
                print("\nNote: This sensor appears to be blank/unprogrammed")
        else:
            print("\n ERROR: Failed to read sensor data")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        reader.disconnect()


def scan_all_channels():
    print_header()
    print("SCANNING ALL CHANNELS")
    print("="*70)

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
                print(" No response")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")

    finally:
        reader.disconnect()
        print("\n" + "="*70)
        print("SCAN COMPLETE")
        print("="*70)


def main():
    while True:
        print_header()
        print_menu()

        choice = input("\nSelect option (0-11): ").strip()

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
            ReadTADC(channel=1).run()

        elif choice == '6':
            ReadEEPROM(channel=1).run()

        elif choice == '7':
            VerifyCoefficients(channel=1).run()
        
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
        
        else:
            print("\nInvalid choice. Please select 0-7.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()