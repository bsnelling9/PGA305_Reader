import os
import sys
import config
from pga305_reader import PGA305Reader


def print_header():
    print(" "*20 + "PGA305 SENSOR READER")


def print_menu():
    """Print main menu options"""
    print("\nMAIN MENU:")
    print("  1. Read sensor data (Part Number, Serial Number, PRange)")
    print("  2. Scan all channels for programmed sensors")
    print("  3. Scan I2C addresses")
    print("  4. Dump EEPROM registers")
    print("  5. Full register scan")
    print("  6. STM32 command discovery")
    print("  0. Exit")


def read_single_sensor():
    print_header()
    print("READ SENSOR DATA")
    print("="*70)
    
    # Get channel from user
    channel_input = input(f"\nEnter channel number (0-7) [default: {config.CHANNEL}]: ").strip()
    channel = int(channel_input) if channel_input else config.CHANNEL
    
    if channel < 0 or channel > 7:
        print("ERROR: Channel must be between 0 and 7")
        return
    
    reader = PGA305Reader()
    
    try:
        # Connect to board
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()
        
        # Get board identity
        board_id = reader.get_board_identity()
        print(f"Board: {board_id}")
        
        # Read sensor data
        print(f"\nReading from channel {channel}...")
        print("-"*70)
        
        data = reader.read_sensor_data(channel)
        
        if data:
            print("\nRESULT:")
            print("="*70)
            print(f"Part Number:   {data['part_number']}")
            print(f"Serial Number: {data['serial_number']}")
            if data['prange'] is not None:
                print(f"PRange:        {data['prange']}")
            print("="*70)
            
            # Check if blank
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
        print("\nConnection closed.")


def run_diagnostic_script(script_name: str):
    """Run a diagnostic script from the scripts/ folder"""
    script_path = os.path.join('scripts', script_name)
    
    if not os.path.exists(script_path):
        print(f"ERROR: Script not found: {script_path}")
        return
    
    print(f"\nRunning {script_name}...")
    print("="*70)
    
    # Execute the script (it will load config.py)
    os.system(f"python {script_path}")


def main():
    """Main program loop"""
    while True:
        print_header()
        print_menu()
        
        choice = input("\nSelect option (0-6): ").strip()
        
        if choice == '0':
            print("\n Ending Script!")
            sys.exit(0)
        
        elif choice == '1':
            read_single_sensor()
        
        elif choice == '2':
            run_diagnostic_script('scan_channels.py')
        
        elif choice == '3':
            run_diagnostic_script('scan_i2c.py')
        
        elif choice == '4':
            run_diagnostic_script('dump_eeprom.py')
        
        elif choice == '5':
            run_diagnostic_script('full_register_scan.py')
        
        elif choice == '6':
            run_diagnostic_script('stm32_commands.py')
        
        else:
            print("\nInvalid choice. Please select 0-6.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()