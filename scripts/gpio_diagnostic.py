import time
from pga305_reader import PGA305Reader


def run_gpio_diagnostic(): 
    print("\n" + "="*70)
    print("GPIO DIAGNOSTIC TEST - MANUAL MODE")
    print("="*70)
    
    print("\nSETUP:")
    print("  1. Multimeter: DC voltage mode")
    print("  2. Attach BLACK probe to GND pin")
    print("  3. To verify that the multimeter works, touch the RED probe to +3V3 pin (should read ~3.3V)")
    print("  4. RED probe Test pin (PA5, PA6, PA7, or PB4)")
    
    input("\nPress Enter to start test...")
    
    reader = PGA305Reader()
    
    try:
        reader.connect()
        print("Connected")
        
        # Start the test - set all pins to 0x00
        print("\n" + "="*70)
        print("STEP 1: Pattern 0x00 - ALL PINS LOW")
        print("="*70)
        print("Sending command: gpio_start")
        
        reader.inst.write_raw(b'gpio_start\n')
        time.sleep(0.2)
        
        # Check response
        if reader.inst.bytes_in_buffer > 0:
            
            response = reader.inst.read_bytes(reader.inst.bytes_in_buffer)
            print(f"Response: {response}")
            
            if b'\x06' in response:
                print("Command acknowledged")
            
            elif b'\x0f' in response or b'\x15' in response:
                print("ERROR: Command NOT recognized - firmware not updated!")
                print("   You need to flash the updated main.c to your STM32")
                
                return
            
            else:
                print("Unexpected response")
        
        else:
            print("No response from STM32")
        
        print("\nExpected voltage levels:")
        print("  • ALL pins (SEL0-SEL7) should be ~0.0V")
        input("Press Enter to continue...")
        
        # Pattern 2: 0xFF
        print("\n" + "="*70)
        print("STEP 2: Pattern 0xFF - ALL PINS HIGH")
        print("="*70)
        print("Sending command: gpio_next")
        
        reader.inst.write_raw(b'gpio_next\n')
        time.sleep(0.2)
        
        # Check response
        if reader.inst.bytes_in_buffer > 0:
            response = reader.inst.read_bytes(reader.inst.bytes_in_buffer)
            print(f"Response: {response}")
            if b'\x06' in response:
                print("Command acknowledged")
            else:
                print("Unexpected response")
        
        print("\nExpected voltage levels:")
        print("  • ALL pins (SEL0-SEL7) should be ~3.3V")
        print("If not the pin is damaged")
        input("Press Enter to continue to next pattern...")
        
        # Pattern 3: 0x03
        print("\n" + "="*70)
        print("STEP 3: Pattern 0x03 - ONLY SEL0 & SEL1 HIGH")
        print("="*70)
        print("Sending command: gpio_next")
        
        reader.inst.write_raw(b'gpio_next\n')
        time.sleep(0.2)
        
        # Check response
        if reader.inst.bytes_in_buffer > 0:
            response = reader.inst.read_bytes(reader.inst.bytes_in_buffer)
            print(f"Response: {response}")
        
        print("\nExpected voltage levels:")
        print("  • SEL0 (Pin: A0), SEL1 (Pin: A1) : ~3.3V (binary bits 0-1 = HIGH)")
        print("  • SEL2 (Pin: A2) -> SEL6 (Pin: A6), and SEL7 (Pin: D12) : ~0.0V (binary bits 2-7 = LOW)")
        print("\nIf testing PA5, PA6, PA7, or PB4 (SEL4-7):")
        print(" The pin should DROP to ~0.0V")
        input("Press Enter to finish test...")
        
        # Reset to 0x00
        print("\n" + "="*70)
        print("STEP 4: Pattern 0x00 - ALL PINS LOW (Reset)")
        print("="*70)
        print("Sending command: gpio_next")
        
        reader.inst.write_raw(b'gpio_next\n')
        time.sleep(0.2)
        
        # Check response
        if reader.inst.bytes_in_buffer > 0:
            response = reader.inst.read_bytes(reader.inst.bytes_in_buffer)
            print(f"Response: {response}")
        
        print("\nExpected voltage levels:")
        print("  • ALL pins (SEL0-SEL7): ~0.0V")
        print("\n The pin should read ~0.0V")
        
        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"\nError: {e}")
        
        import traceback
        
        traceback.print_exc()
        
    finally:
        reader.disconnect()