import time
import config
from pga305_reader import PGA305Reader
from helpers.select_channel import select_channel


def labview_padc(lsb, mid, msb):
    multiplier = -1 if (msb // 128) > 0 else 1
    magnitude = ((msb % 128) << 16) | (mid << 8) | lsb
    return magnitude * multiplier

def to_signed_24(v):
    return v - 0x1000000 if v & 0x800000 else v

def read_dmm_voltage(reader, channel):
    response = reader.send_command(f"mx1{channel:02X}")
    print(f"Response: {response}")
    print("Record output voltage from the DMM")
    input("Press enter to continue...")


def read_and_calculate(reader, padc_gain, padc_offset, tadc_gain, tadc_offset, off_en):
    reader.write_register(0x09, 0x00, config.PGA305_I2C_ADDR)
    padc_msb = reader.read_register(0x04, config.PGA305_I2C_ADDR)
    reader.write_register(0x09, 0x70, config.PGA305_I2C_ADDR)
    time.sleep(0.1)
    padc_mid = reader.read_register(0x05, config.PGA305_I2C_ADDR)
    padc_lsb = reader.read_register(0x04, config.PGA305_I2C_ADDR)
 
    reader.write_register(0x09, 0x02, config.PGA305_I2C_ADDR)
    tadc_msb = reader.read_register(0x04, config.PGA305_I2C_ADDR)
    reader.write_register(0x09, 0x70, config.PGA305_I2C_ADDR)
    time.sleep(0.1)
    tadc_mid = reader.read_register(0x05, config.PGA305_I2C_ADDR)
    tadc_lsb = reader.read_register(0x04, config.PGA305_I2C_ADDR)
 
    reader.write_register(0x09, 0x04, config.PGA305_I2C_ADDR)
    data_msb = reader.read_register(0x04, config.PGA305_I2C_ADDR)
    reader.write_register(0x09, 0x70, config.PGA305_I2C_ADDR)
    time.sleep(0.1)
    data_mid = reader.read_register(0x05, config.PGA305_I2C_ADDR)
    data_lsb = reader.read_register(0x04, config.PGA305_I2C_ADDR)
 
    if None in (padc_msb, padc_mid, padc_lsb, tadc_msb, tadc_mid, tadc_lsb, data_msb, data_mid, data_lsb):
        print("ERROR: Failed to read core sensor data.")
        return
 
    padc_raw = labview_padc((padc_msb << 16) | (padc_mid << 8) | padc_lsb)
    tadc_raw = labview_padc((tadc_msb << 16) | (tadc_mid << 8) | tadc_lsb)
    data_out_raw = (data_msb << 16) | (data_mid << 8) | data_lsb
    data_out = to_signed_24(data_out_raw)
    dac = data_out / 1024
 
    if off_en:
        P = padc_gain * (padc_raw + padc_offset)
        T = tadc_gain * (tadc_raw + tadc_offset)
    else:
        P = padc_gain * padc_raw + padc_offset
        T = tadc_gain * tadc_raw + tadc_offset
 
    P_normalized = P / config.P_NORM
    T_normalized = T / config.T_NORM
 
    print(f"PADC     = {padc_raw} (0x{padc_raw & 0xFFFFFF:06X})  LSB=0x{padc_lsb:02X} MID=0x{padc_mid:02X} MSB=0x{padc_msb:02X}")
    print(f"TADC     = {tadc_raw} (0x{tadc_raw & 0xFFFFFF:06X})  LSB=0x{tadc_lsb:02X} MID=0x{tadc_mid:02X} MSB=0x{tadc_msb:02X}")
    print(f"DATA_OUT = {data_out}  LSB=0x{data_lsb:02X} MID=0x{data_mid:02X} MSB=0x{data_msb:02X}")
    print(f"DAC      = {dac:.4f}")
    print(f"\nP = {P} ({P_normalized:.6f})")
    print(f"T = {T} ({T_normalized:.6f})")


def compute_dac(reader, channel):
    print(f"Switching to I2C mode on channel {channel}...")
    reader.send_command(f"mx2{channel:02X}")

    print("Entering command mode...")
    if not reader.enter_command_mode():
        print("ERROR: Could not enter command mode")
        return

    comp_ctrl = reader.read_register(0x0C, config.PGA305_I2C_ADDR)
    print(f"COMPENSATION_CONTROL = 0x{comp_ctrl:02X}")

    print("Reading EEPROM settings...")

    gain_lsb = reader.read_register(0x44, config.EEPROM_ADDR)
    gain_mid = reader.read_register(0x45, config.EEPROM_ADDR)
    gain_msb = reader.read_register(0x46, config.EEPROM_ADDR)
    
    if None in (gain_lsb, gain_mid, gain_msb):
        print("ERROR: Could not read PADC_GAIN")
        return
    padc_gain = (gain_msb << 16) | (gain_mid << 8) | gain_lsb

    off_lsb = reader.read_register(0x47, config.EEPROM_ADDR)
    off_mid = reader.read_register(0x48, config.EEPROM_ADDR)
    off_msb = reader.read_register(0x49, config.EEPROM_ADDR)
    
    if None in (off_lsb, off_mid, off_msb):
        print("ERROR: Could not read PADC_OFFSET")
        return
    padc_offset = to_signed_24((off_msb << 16) | (off_mid << 8) | off_lsb)

    tgain_lsb = reader.read_register(0x5E, config.EEPROM_ADDR)
    tgain_mid = reader.read_register(0x5F, config.EEPROM_ADDR)
    tgain_msb = reader.read_register(0x60, config.EEPROM_ADDR)
    if None in (tgain_lsb, tgain_mid, tgain_msb):
        print("ERROR: Could not read TADC_GAIN")
        return
    tadc_gain = (tgain_msb << 16) | (tgain_mid << 8) | tgain_lsb

    toff_lsb = reader.read_register(0x61, config.EEPROM_ADDR)
    toff_mid = reader.read_register(0x62, config.EEPROM_ADDR)
    toff_msb = reader.read_register(0x63, config.EEPROM_ADDR)
    if None in (toff_lsb, toff_mid, toff_msb):
        print("ERROR: Could not read TADC_OFFSET")
        return
    tadc_offset = to_signed_24((toff_msb << 16) | (toff_mid << 8) | toff_lsb)

    off_en_reg = reader.read_register(0x69, config.EEPROM_ADDR)
    if off_en_reg is None:
        print("ERROR: Could not read OFFSET_ENABLE")
        return
    off_en = off_en_reg & 1

    print(f"\nPADC_GAIN   = {padc_gain} (0x{padc_gain:06X})")
    print(f"PADC_OFFSET = {padc_offset} (0x{padc_offset & 0xFFFFFF:06X})")
    print(f"TADC_GAIN   = {tadc_gain} (0x{tadc_gain:06X})")
    print(f"TADC_OFFSET = {tadc_offset} (0x{tadc_offset & 0xFFFFFF:06X})")
    print(f"OFF_EN      = {off_en}")

    if off_en:
        print("Equation:   P = PGAIN x (PADC + POFFSET)  [Eq. 4]")
        print("Equation:   T = TGAIN x (TADC + TOFFSET)  [Eq. 5]")
    else:
        print("Equation:   P = PGAIN x PADC + POFFSET    [Eq. 2]")
        print("Equation:   T = TGAIN x TADC + TOFFSET    [Eq. 3]")

    reader.write_register(0x0C, 0x00, config.PGA305_I2C_ADDR)

    print("\n" + "=" * 70)
    read_and_calculate(reader, padc_gain, padc_offset, tadc_gain, tadc_offset, off_en)
    print("\n" + "=" * 70)
    print("  r = read again   x = back to sensor menu")
    print("=" * 70)

    while True:
        user_input = input("\nAction [r/x]: ").strip().lower()
        if user_input == 'x':
            break
        elif user_input == 'r':
            read_and_calculate(reader, padc_gain, padc_offset, tadc_gain, tadc_offset, off_en)
        else:
            print("  Type 'r' to read again or 'x' to go back.")


def print_sensor_menu(channel):
    print("\n" + "=" * 70)
    print(" " * 25 + "SENSOR OUTPUT")
    print("=" * 70)
    print(f"  Current channel: {channel}")
    print("-" * 70)
    print("  1.  Read voltage on DMM")
    print("  2.  Compute DAC")
    print("  3.  Switch channel")
    print("  x.  Back to main menu")
    print("-" * 70)


def sensor_output():
    reader = PGA305Reader()
    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        channel = select_channel(reader)
        if channel is None:
            return

        while True:
            print_sensor_menu(channel)
            choice = input("\nSelect option: ").strip().lower()

            if choice == 'x':
                break
            elif choice == '1':
                read_dmm_voltage(reader, channel)
            elif choice == '2':
                compute_dac(reader, channel)
            elif choice == '3':
                new_channel = select_channel(reader)
                if new_channel is not None:
                    channel = new_channel
            else:
                print("Invalid option.")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        reader.disconnect_channel()
        reader.disconnect()
        print("\nDisconnected.")