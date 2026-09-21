import sys
import config
from scripts.gpio_diagnostic import run_gpio_diagnostic
from scripts.verify_calibration import run_calibration_verification
from read_eeprom import ReadEEPROM
from write_eeprom import WriteEEPROM
from verify_coefficients import VerifyCoefficients
from scan_mux_channels import ScanMuxChannels
from enable_owi import EnableOWI
from handle_uart import HandleUART
from read_control_registers import ReadControlRegisters
from sensor_output import sensor_output
from reset_eeprom import ResetEEPROM
from write_calibration import CalibrationWriter
from reset_coefficients import run as reset_coefficients
from dac_output_test import dac_output_test
from set_op_stage_ctrl import run as set_op_stage_ctrl


def print_header():
    print("\n" + "=" * 70)
    print(" " * 20 + "PGA305 SENSOR READER")
    print("=" * 70)


def print_menu():
    print("\nMAIN MENU:")
    print("-" * 70)
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
    print("  15. Sensor output (DMM / Compute DAC)")
    print("  16. Write Calibration Coefficients and Settings")
    print("  17. Clear Calibration")
    print("  18. DAC output test (manual code -> DMM)")
    print("  19. Set OP_STAGE_CTRL (channel range)")
    print("  c.  Reset EEPROM")
    print("  r.  Reset coefficients")
    print("  0.  Exit")
    print("-" * 70)


def main():
    while True:
        print_header()
        print_menu()

        choice = input("\nSelect option: ").strip().lower()

        if choice == '0':
            print("\nExiting...")
            sys.exit(0)
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
        elif choice == '15':
            sensor_output()
        elif choice == '16':
            CalibrationWriter().run()
        elif choice == '17':
            CalibrationWriter().clear_calibration()
        elif choice == '18':
            dac_output_test()
        elif choice == '19':
            set_op_stage_ctrl()
        elif choice == 'c':
            ResetEEPROM(channel=config.CHANNEL).run()
        elif choice == 'r':
            reset_coefficients()
        else:
            print("\nInvalid choice.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()