import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pga305_reader import PGA305Reader

print("="*70)
print("SCANNING ALL CHANNELS FOR PROGRAMMED PGA305 SENSORS")
print("="*70)

# Initialize reader (loads config automatically)
reader = PGA305Reader()
reader.connect()

for channel in range(8):
    print(f"\n--- Channel {channel} ---")
    
    try:
        # Read sensor data using the class
        data = reader.read_sensor_data(channel)
        
        if data:
            print(f"  Part Number:   {data['part_number']}")
            print(f"  Serial Number: {data['serial_number']}")
            if data['prange'] is not None:
                print(f"  PRange:        {data['prange']}")
            
            # Check if programmed
            if data['serial_number'] != 0 or data['part_number'] not in ['A0', 'S0']:
                print(f"  ✓ PROGRAMMED SENSOR FOUND!")
            else:
                print(f"  (blank/unprogrammed)")
        else:
            print("  No response")
    
    except Exception as e:
        print(f"  ERROR: {e}")

reader.disconnect()
print("\n" + "="*70)
print("SCAN COMPLETE")
print("="*70)