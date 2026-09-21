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
    print("  1.  Run GPIO diagnostic test (check for damaged STM32 pins)")
    print("  2.  Verify PGA305 calibration")
    print("  3.  Read EEPROM configuration")
    print("  4.  Verify coefficients against DUT file")
    print("  5.  Timing diagnostic scan (all channels, multiple iterations)")
    print("  6.  Enable OWI")
    print("  7.  Handle UART")
    print("  8.  Read Control Registers")
    print("  9.  Write EEPROM register")
    print("  10. Sensor output (DMM / Compute DAC)")
    print("  11. Write Calibration Coefficients and Settings")
    print("  12. Clear Calibration")
    print("  13. DAC output test (manual code -> DMM)")
    print("  14. Set OP_STAGE_CTRL (channel range)")
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
        elif choice == '1':
            run_gpio_diagnostic()
        elif choice == '2':
            run_calibration_verification()
        elif choice == '3':
            ReadEEPROM(channel=config.CHANNEL).run()
        elif choice == '4':
            VerifyCoefficients(channel=config.CHANNEL).run()
        elif choice == '5':
            ScanMuxChannels(iterations=config.SCAN_ITERATIONS).run()
        elif choice == '6':
            EnableOWI(channel=config.CHANNEL).run()
        elif choice == '7':
            HandleUART(channel=config.CHANNEL).run()
        elif choice == '8':
            ReadControlRegisters(channel=config.CHANNEL).run()
        elif choice == '9':
            WriteEEPROM(channel=config.CHANNEL).run()
        elif choice == '10':
            sensor_output()
        elif choice == '11':
            CalibrationWriter().run()
        elif choice == '12':
            CalibrationWriter().clear_calibration()
        elif choice == '13':
            dac_output_test()
        elif choice == '14':
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