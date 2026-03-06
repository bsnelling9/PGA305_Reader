"""
PGA305 Reader - Main Menu Application
======================================
Interactive menu for reading sensors and running diagnostics
"""

import os
import sys
import config
from pga305_reader import PGA305Reader


def print_header():
    """Print application header"""
    print("\n" + "="*70)
    print(" "*20 + "PGA305 SENSOR READER")
    print("="*70)


def print_menu():
    """Print main menu options"""
    print("\nMAIN MENU:")
    print("-" * 70)
    print("  1. Read sensor data (Part Number, Serial Number, PRange)")
    print("  2. Scan all channels for programmed sensors")
    print("  0. Exit")
    print("-" * 70)


def read_single_sensor():
    """Read Part Number, Serial Number, and PRange from a single sensor"""
    print_header()
    print("READ SENSOR DATA")
    print("="*70)
    
    # Get channel from user
    channel_input = input(f"\nEnter channel number (0-7) [default: {config.CHANNEL}]: ").strip()
    channel = int(channel_input) if channel_input else config.CHANNEL
    
    if channel < 0 or channel > 7:
        print("ERROR: Channel must be between 0 and 7")
        return
    
    # Initialize reader
    reader = PGA305Reader()
    
    try:
        # Connect to board
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()
        
        # Get board identity
        board_id = reader.get_board_identity()
        print(f"Board: {board_id}")
        
        # Read sensor data
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
            
            # Check if blank
            if data['serial_number'] == 0 and data['part_number'] in ['A0', 'S0']:
                print("\nNote: This sensor appears to be blank/unprogrammed")
        else:
            print("\n✗ ERROR: Failed to read sensor data")
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        reader.disconnect()


def scan_all_channels():
    """Scan all channels for programmed sensors"""
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
                
                # Check if programmed
                if data['serial_number'] != 0 or data['part_number'] not in ['A0', 'S0']:
                    print(f"  ✓ PROGRAMMED SENSOR")
                else:
                    print(f"  (blank/unprogrammed)")
            else:
                print("  ✗ No response")
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
    
    finally:
        reader.disconnect()
        print("\n" + "="*70)
        print("SCAN COMPLETE")
        print("="*70)


def main():
    """Main program loop"""
    while True:
        print_header()
        print_menu()
        
        choice = input("\nSelect option (0-2): ").strip()
        
        if choice == '0':
            print("\nGoodbye!")
            sys.exit(0)
        
        elif choice == '1':
            read_single_sensor()
        
        elif choice == '2':
            scan_all_channels()
        
        else:
            print("\nInvalid choice. Please select 0-2.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()