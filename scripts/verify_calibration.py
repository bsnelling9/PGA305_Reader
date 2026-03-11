import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pga305_reader import PGA305Reader
import config


# =============================================================================
# PGA305 EEPROM Register Map (from PGA305 Control and Status Registers Map.csv)
# All accessed via I2C address 0x25 (EEPROM_ADDR)
#
# Calibration Coefficients (Pages 0-5):
#   H0-H3: Offset coefficients (24-bit, 3 bytes each)
#   G0-G3: Gain coefficients (24-bit, 3 bytes each)
#   N0-N3: Nonlinearity coefficients (24-bit, 3 bytes each)
#   M0-M3: Temperature coefficients (24-bit, 3 bytes each)
#
# The PGA305 uses a 3rd-order polynomial with up to 16 coefficients
# for temperature and nonlinearity compensation.
# =============================================================================

NORM_FACTOR_24BIT = 2**22  # 4,194,304 - normalization for 24-bit ADC
NORM_FACTOR_16BIT = 2**14  # 16,384 - normalization for 16-bit ADC

# Calibration coefficient addresses (Pages 0-5)
CAL_COEFFICIENTS = {
    "H0_LSB": 0x00, "H0_MID": 0x01, "H0_MSB": 0x02,
    "H1_LSB": 0x03, "H1_MID": 0x04, "H1_MSB": 0x05,
    "H2_LSB": 0x06, "H2_MID": 0x07, "H2_MSB": 0x08,
    "H3_LSB": 0x09, "H3_MID": 0x0A, "H3_MSB": 0x0B,
    "G0_LSB": 0x0C, "G0_MID": 0x0D, "G0_MSB": 0x0E,
    "G1_LSB": 0x0F, "G1_MID": 0x10, "G1_MSB": 0x11,
    "G2_LSB": 0x12, "G2_MID": 0x13, "G2_MSB": 0x14,
    "G3_LSB": 0x15, "G3_MID": 0x16, "G3_MSB": 0x17,
    "N0_LSB": 0x18, "N0_MID": 0x19, "N0_MSB": 0x1A,
    "N1_LSB": 0x1B, "N1_MID": 0x1C, "N1_MSB": 0x1D,
    "N2_LSB": 0x1E, "N2_MID": 0x1F, "N2_MSB": 0x20,
    "N3_LSB": 0x21, "N3_MID": 0x22, "N3_MSB": 0x23,
    "M0_LSB": 0x24, "M0_MID": 0x25, "M0_MSB": 0x26,
    "M1_LSB": 0x27, "M1_MID": 0x28, "M1_MSB": 0x29,
    "M2_LSB": 0x2A, "M2_MID": 0x2B, "M2_MSB": 0x2C,
    "M3_LSB": 0x2D, "M3_MID": 0x2E, "M3_MSB": 0x2F,
}

# Supporting calibration registers - these MUST match the coefficient calculation
SUPPORT_REGISTERS = {
    # Digital gain/offset applied to ADC data before polynomial (Pages 8-9, B-C)
    "PADC_GAIN_LSB":    0x44, "PADC_GAIN_MID":    0x45, "PADC_GAIN_MSB":    0x46,
    "PADC_OFFSET_LSB":  0x47, "PADC_OFFSET_MID":  0x48, "PADC_OFFSET_MSB":  0x49,
    "TADC_GAIN_LSB":    0x5E, "TADC_GAIN_MID":    0x5F, "TADC_GAIN_MSB":    0x60,
    "TADC_OFFSET_LSB":  0x61, "TADC_OFFSET_MID":  0x62, "TADC_OFFSET_MSB":  0x63,
    # Control bits that affect how compensation engine uses the coefficients
    "ADC_24BIT_ENABLE":  0x68,
    "OFFSET_ENABLE":     0x69,
}

# AFE hardware configuration (Page 6)
AFE_REGISTERS = {
    "P_GAIN_SELECT":  0x35,
    "T_GAIN_SELECT":  0x36,
    "BRDG_CTRL":      0x34,
    "OP_STAGE_CTRL":  0x33,
    "DAC_CTRL_STATUS": 0x31,
    "DAC_CONFIG":     0x32,
    "TEMP_CTRL":      0x37,
}

# DAC output range (Page 7)
RANGE_REGISTERS = {
    "NORMAL_LOW_LSB":  0x3C, "NORMAL_LOW_MSB":  0x3D,
    "NORMAL_HIGH_LSB": 0x3E, "NORMAL_HIGH_MSB": 0x3F,
    "LOW_CLAMP_LSB":   0x40, "LOW_CLAMP_MSB":   0x41,
    "HIGH_CLAMP_LSB":  0x42, "HIGH_CLAMP_MSB":  0x43,
}

# DAC linearization (Pages 9-A)
DAC_LIN_REGISTERS = {
    "A0_LSB": 0x4A, "A0_MSB": 0x4B,
    "A1_LSB": 0x4C, "A1_MSB": 0x4D,
    "A2_LSB": 0x4E, "A2_MSB": 0x4F,
    "B0_LSB": 0x50, "B0_MSB": 0x51,
    "B1_LSB": 0x52, "B1_MSB": 0x53,
    "B2_LSB": 0x54, "B2_MSB": 0x55,
}

# Sensor identity (Page E)
IDENTITY_REGISTERS = {
    "PN_LSB": 0x70, "PN_MID": 0x71, "PN_MSB": 0x72,
    "SN_LSB": 0x73, "SN_MID": 0x74, "SN_MSB": 0x75,
    "PRANGE_LSB": 0x76, "PRANGE_MSB": 0x77,
}

# PGA305 pressure gain lookup (P_GAIN_SELECT[4:0] -> gain value)
P_GAIN_TABLE = {
    0: 2.67, 1: 3, 2: 3.2, 3: 3.56, 4: 4, 5: 4.5, 6: 5.33, 7: 6,
    8: 6.4, 9: 7.11, 10: 8, 11: 10, 12: 12, 13: 13.33, 14: 16, 15: 20,
    16: 24, 17: 30, 18: 32, 19: 40, 20: 48, 21: 60, 22: 80, 23: 100,
    24: 120, 25: 133, 26: 160, 27: 200, 28: 240, 29: 266, 30: 320, 31: 400,
}

# PGA305 temperature gain lookup (T_GAIN_SELECT[1:0] -> gain value)
T_GAIN_TABLE = {0: 5, 1: 10, 2: 20, 3: 40}

# Bridge voltage lookup (VBRDG_CTRL[1:0])
VBRDG_TABLE = {0: "1.0V", 1: "1.5V", 2: "2.0V", 3: "2.5V"}

# DAC gain lookup (DAC_GAIN[2:0])
DAC_GAIN_TABLE = {
    0: "1 V/V", 1: "1.375 V/V", 2: "1.75 V/V", 3: "2.5 V/V",
    4: "5 V/V", 5: "7.5 V/V", 6: "10 V/V", 7: "Reserved",
}


def combine_24bit(lsb, mid, msb):
    """Combine 3 bytes into a 24-bit unsigned value"""
    if lsb is None or mid is None or msb is None:
        return None
    return lsb + (mid << 8) + (msb << 16)


def to_signed_24bit(value):
    """Convert unsigned 24-bit to signed"""
    if value is None:
        return None
    if value >= 0x800000:
        return value - 0x1000000
    return value


def combine_16bit(lsb, msb):
    """Combine 2 bytes into a 16-bit value"""
    if lsb is None or msb is None:
        return None
    return lsb + (msb << 8)


def read_register_block(reader, register_map):
    """Read a block of registers and return raw values dict"""
    raw = {}
    for name, addr in register_map.items():
        raw[name] = reader.read_register(addr, config.EEPROM_ADDR)
    return raw


def verify_calibration(reader, channel, verbose=True):
    """
    Read and verify all calibration-related data from a PGA305 sensor.

    Reads:
      - 16 polynomial coefficients (H0-H3, G0-G3, N0-N3, M0-M3)
      - Supporting registers (PADC/TADC gain/offset, OFF_EN, ADC mode)
      - AFE hardware config (analog gains, bridge voltage, DAC settings)
      - DAC linearization coefficients
      - Sensor identity (PN, SN, PRange)

    Performs consistency checks to verify the calibration is complete
    and all registers are set correctly as a matched set.

    Args:
        reader: PGA305Reader instance (already connected)
        channel: Multiplexer channel (0-7)
        verbose: Print detailed output

    Returns:
        dict with all calibration data, or None if communication failed
    """
    if verbose:
        print(f"\nReading calibration data from channel {channel}...")

    reader.reset_i2c()
    reader.set_channel(channel)

    if not reader.enter_command_mode():
        if verbose:
            print("✗ ERROR: Could not enter command mode")
            print("  Try power cycling the board")
        return None

    if verbose:
        print("✓ Command mode active")

    # =========================================================================
    # 1. Read sensor identity (Page E)
    # =========================================================================
    id_raw = read_register_block(reader, IDENTITY_REGISTERS)

    pn_val = combine_24bit(id_raw.get("PN_LSB"), id_raw.get("PN_MID"), id_raw.get("PN_MSB"))
    sn_val = combine_24bit(id_raw.get("SN_LSB"), id_raw.get("SN_MID"), id_raw.get("SN_MSB"))
    prange_val = combine_16bit(id_raw.get("PRANGE_LSB"), id_raw.get("PRANGE_MSB"))

    # Decode part number
    part_number = None
    serial_number = None
    if pn_val is not None:
        pn_msb_byte = id_raw.get("PN_MSB", 0)
        pn_prefix = "A" if (pn_msb_byte % 128) == 0 else "S"
        pn_numeric = id_raw.get("PN_LSB", 0) + (id_raw.get("PN_MID", 0) << 8) + ((pn_msb_byte // 128) << 16)
        part_number = f"{pn_prefix}{pn_numeric}"
        serial_number = sn_val

    if verbose:
        print(f"\n{'='*70}")
        print("SENSOR IDENTITY")
        print(f"{'='*70}")
        if part_number:
            print(f"  Part Number:   {part_number}")
        if serial_number is not None:
            print(f"  Serial Number: {serial_number}")
        if prange_val is not None:
            print(f"  PRange:        {prange_val}")

    # =========================================================================
    # 2. Read all 16 calibration coefficients (Pages 0-5)
    # =========================================================================
    cal_raw = read_register_block(reader, CAL_COEFFICIENTS)

    coeff_names = ["H0", "H1", "H2", "H3", "G0", "G1", "G2", "G3",
                   "N0", "N1", "N2", "N3", "M0", "M1", "M2", "M3"]

    coefficients = {}
    for name in coeff_names:
        raw_val = combine_24bit(
            cal_raw.get(f"{name}_LSB"),
            cal_raw.get(f"{name}_MID"),
            cal_raw.get(f"{name}_MSB")
        )
        coefficients[name] = raw_val

    if verbose:
        print(f"\n{'='*70}")
        print("CALIBRATION COEFFICIENTS (EEPROM Pages 0-5)")
        print(f"{'='*70}")
        for family_name, family_desc in [("H", "Offset"), ("G", "Gain"),
                                          ("N", "Nonlinearity"), ("M", "Temperature")]:
            print(f"\n  {family_desc} Coefficients ({family_name}):")
            for i in range(4):
                name = f"{family_name}{i}"
                val = coefficients[name]
                if val is not None:
                    signed = to_signed_24bit(val)
                    print(f"    {name}: 0x{val:06X} ({signed:+9d})")
                else:
                    print(f"    {name}: READ ERROR")

    # =========================================================================
    # 3. Read supporting calibration registers
    # =========================================================================
    support_raw = read_register_block(reader, SUPPORT_REGISTERS)

    padc_gain = combine_24bit(
        support_raw.get("PADC_GAIN_LSB"),
        support_raw.get("PADC_GAIN_MID"),
        support_raw.get("PADC_GAIN_MSB"))
    padc_offset = combine_24bit(
        support_raw.get("PADC_OFFSET_LSB"),
        support_raw.get("PADC_OFFSET_MID"),
        support_raw.get("PADC_OFFSET_MSB"))
    tadc_gain = combine_24bit(
        support_raw.get("TADC_GAIN_LSB"),
        support_raw.get("TADC_GAIN_MID"),
        support_raw.get("TADC_GAIN_MSB"))
    tadc_offset = combine_24bit(
        support_raw.get("TADC_OFFSET_LSB"),
        support_raw.get("TADC_OFFSET_MID"),
        support_raw.get("TADC_OFFSET_MSB"))

    adc_24bit_en = support_raw.get("ADC_24BIT_ENABLE")
    offset_enable = support_raw.get("OFFSET_ENABLE")

    # Convert gain/offset to signed where needed
    padc_offset_signed = to_signed_24bit(padc_offset) if padc_offset is not None else None
    tadc_offset_signed = to_signed_24bit(tadc_offset) if tadc_offset is not None else None
    padc_gain_signed = to_signed_24bit(padc_gain) if padc_gain is not None else None
    tadc_gain_signed = to_signed_24bit(tadc_gain) if tadc_gain is not None else None

    if verbose:
        print(f"\n{'='*70}")
        print("SUPPORTING CALIBRATION REGISTERS")
        print(f"{'='*70}")

        print("\n  ADC Digital Gain/Offset (must match coefficient calculation):")
        if padc_gain is not None:
            print(f"    PADC_GAIN:    0x{padc_gain:06X} ({padc_gain_signed:+d})")
        else:
            print(f"    PADC_GAIN:    READ ERROR")
        if padc_offset is not None:
            print(f"    PADC_OFFSET:  0x{padc_offset:06X} ({padc_offset_signed:+d})")
        else:
            print(f"    PADC_OFFSET:  READ ERROR")
        if tadc_gain is not None:
            print(f"    TADC_GAIN:    0x{tadc_gain:06X} ({tadc_gain_signed:+d})")
        else:
            print(f"    TADC_GAIN:    READ ERROR")
        if tadc_offset is not None:
            print(f"    TADC_OFFSET:  0x{tadc_offset:06X} ({tadc_offset_signed:+d})")
        else:
            print(f"    TADC_OFFSET:  READ ERROR")

        print("\n  Compensation Engine Control:")
        if adc_24bit_en is not None:
            mode = "24-bit" if (adc_24bit_en & 0x01) else "16-bit"
            print(f"    ADC_24BIT_EN: {adc_24bit_en} ({mode} mode)")
        if offset_enable is not None:
            off_en = "offset before gain" if (offset_enable & 0x01) else "gain before offset"
            print(f"    OFFSET_EN:    {offset_enable} ({off_en})")

    # =========================================================================
    # 4. Read AFE hardware configuration (Page 6)
    # =========================================================================
    afe_raw = read_register_block(reader, AFE_REGISTERS)

    if verbose:
        print(f"\n{'='*70}")
        print("AFE HARDWARE CONFIGURATION (EEPROM Page 6)")
        print(f"{'='*70}")

        p_gain_raw = afe_raw.get("P_GAIN_SELECT")
        if p_gain_raw is not None:
            p_gain_code = p_gain_raw & 0x1F
            p_inv = bool(p_gain_raw & 0x80)
            p_gain_val = P_GAIN_TABLE.get(p_gain_code, "Unknown")
            print(f"    P_GAIN:       {p_gain_val} (code={p_gain_code}, P_INV={p_inv})")

        t_gain_raw = afe_raw.get("T_GAIN_SELECT")
        if t_gain_raw is not None:
            t_gain_code = t_gain_raw & 0x03
            t_inv = bool(t_gain_raw & 0x80)
            t_gain_val = T_GAIN_TABLE.get(t_gain_code, "Unknown")
            print(f"    T_GAIN:       {t_gain_val} (code={t_gain_code}, T_INV={t_inv})")

        brdg_raw = afe_raw.get("BRDG_CTRL")
        if brdg_raw is not None:
            brdg_en = bool(brdg_raw & 0x01)
            vbrdg_code = (brdg_raw >> 1) & 0x03
            vbrdg_val = VBRDG_TABLE.get(vbrdg_code, "Unknown")
            print(f"    Bridge:       {'Enabled' if brdg_en else 'Disabled'}, VBRDG={vbrdg_val}")

        op_raw = afe_raw.get("OP_STAGE_CTRL")
        if op_raw is not None:
            dac_gain_code = op_raw & 0x07
            ma_420 = bool(op_raw & 0x08)
            dac_gain_val = DAC_GAIN_TABLE.get(dac_gain_code, "Unknown")
            print(f"    DAC Gain:     {dac_gain_val}")
            print(f"    4-20mA Mode:  {'Enabled' if ma_420 else 'Disabled'}")

        dac_ctrl_raw = afe_raw.get("DAC_CTRL_STATUS")
        if dac_ctrl_raw is not None:
            dac_en = bool(dac_ctrl_raw & 0x01)
            print(f"    DAC:          {'Enabled' if dac_en else 'Disabled'}")

        dac_cfg_raw = afe_raw.get("DAC_CONFIG")
        if dac_cfg_raw is not None:
            ratio = bool(dac_cfg_raw & 0x01)
            print(f"    Ratiometric:  {'Enabled' if ratio else 'Disabled'}")

    # =========================================================================
    # 5. Read DAC output range and linearization
    # =========================================================================
    range_raw = read_register_block(reader, RANGE_REGISTERS)
    dac_lin_raw = read_register_block(reader, DAC_LIN_REGISTERS)

    normal_low = combine_16bit(range_raw.get("NORMAL_LOW_LSB"), range_raw.get("NORMAL_LOW_MSB"))
    normal_high = combine_16bit(range_raw.get("NORMAL_HIGH_LSB"), range_raw.get("NORMAL_HIGH_MSB"))
    low_clamp = combine_16bit(range_raw.get("LOW_CLAMP_LSB"), range_raw.get("LOW_CLAMP_MSB"))
    high_clamp = combine_16bit(range_raw.get("HIGH_CLAMP_LSB"), range_raw.get("HIGH_CLAMP_MSB"))

    dac_coefficients = {}
    for name in ["A0", "A1", "A2", "B0", "B1", "B2"]:
        dac_coefficients[name] = combine_16bit(
            dac_lin_raw.get(f"{name}_LSB"),
            dac_lin_raw.get(f"{name}_MSB"))

    if verbose:
        print(f"\n{'='*70}")
        print("DAC OUTPUT RANGE & LINEARIZATION")
        print(f"{'='*70}")
        if normal_low is not None:
            print(f"    NORMAL_LOW:   0x{normal_low:04X} ({normal_low})")
        if normal_high is not None:
            print(f"    NORMAL_HIGH:  0x{normal_high:04X} ({normal_high})")
        if low_clamp is not None:
            print(f"    LOW_CLAMP:    0x{low_clamp:04X} ({low_clamp})")
        if high_clamp is not None:
            print(f"    HIGH_CLAMP:   0x{high_clamp:04X} ({high_clamp})")

        non_zero_dac = {k: v for k, v in dac_coefficients.items()
                        if v is not None and v != 0}
        if non_zero_dac:
            print("\n    DAC Linearization Coefficients:")
            for name, val in dac_coefficients.items():
                if val is not None:
                    print(f"      {name}: 0x{val:04X} ({val:5d})")
        else:
            print("\n    DAC Linearization: Not programmed (all zero)")

    # =========================================================================
    # 6. Analysis and Consistency Checks
    # =========================================================================
    if verbose:
        print(f"\n{'='*70}")
        print("CALIBRATION ANALYSIS")
        print(f"{'='*70}")

    # Determine which coefficients are non-zero
    non_zero_cal = {k: v for k, v in coefficients.items()
                    if v is not None and v != 0}
    has_coefficients = len(non_zero_cal) > 0

    # Determine calibration type from coefficient pattern
    # Temperature order: count how many temp levels have non-zero coefficients
    temp_points = 0
    for i in range(4):
        has_at_level = any(
            coefficients.get(f"{fam}{i}") not in [None, 0]
            for fam in ["H", "G", "N", "M"]
        )
        if has_at_level:
            temp_points = i + 1

    # Pressure order: count which families are used
    pressure_points = 0
    for j, fam in enumerate(["H", "G", "N", "M"]):
        has_in_family = any(
            coefficients.get(f"{fam}{i}") not in [None, 0]
            for i in range(4)
        )
        if has_in_family:
            pressure_points = j + 1

    # Determine normalization factor based on ADC mode
    is_24bit = (adc_24bit_en is not None) and (adc_24bit_en & 0x01)
    norm_factor = NORM_FACTOR_24BIT if is_24bit else NORM_FACTOR_16BIT

    warnings = []
    info = []

    if has_coefficients:
        cal_type = f"{temp_points}T{pressure_points}P"
        info.append(f"Calibration type: {cal_type}")

        if verbose:
            print(f"\n  ✓ Calibration coefficients detected ({cal_type})")
            print(f"\n  Non-zero coefficients (normalized = EEPROM / {norm_factor}):")
            for name, val in non_zero_cal.items():
                signed = to_signed_24bit(val)
                normalized = signed / norm_factor
                print(f"    {name}: 0x{val:06X} ({signed:+d})  ->  {normalized:+.6f}")

        # --- Consistency Checks ---
        if verbose:
            print(f"\n  {'_'*60}")
            print(f"  CONSISTENCY CHECKS")
            print(f"  {'_'*60}")

        # Check 1: PADC/TADC gain should not be zero if coefficients are present
        if padc_gain is not None and padc_gain == 0:
            warnings.append("PADC_GAIN is 0 - pressure data will be zeroed out")
        if tadc_gain is not None and tadc_gain == 0 and temp_points > 1:
            warnings.append("TADC_GAIN is 0 but temperature coefficients are present")

        # Check 2: If gain is 1 and offset is 0, that's the default (no digital scaling)
        # This is valid for simple calibrations but worth noting
        padc_defaults = (padc_gain in [1, None]) and (padc_offset in [0, None])
        tadc_defaults = (tadc_gain in [1, None]) and (tadc_offset in [0, None])

        if padc_defaults and tadc_defaults:
            info.append("PADC/TADC gain=1, offset=0 (no digital scaling applied)")
            if verbose:
                print(f"  i  PADC/TADC gain=1, offset=0 (no digital scaling)")
                print(f"     This is normal for simple calibrations where the")
                print(f"     calculator recommended gain=1 and offset=0.")
        else:
            if verbose:
                print(f"  ✓  Digital scaling is configured:")
                if not padc_defaults:
                    print(f"     PADC: gain={padc_gain_signed}, offset={padc_offset_signed}")
                if not tadc_defaults:
                    print(f"     TADC: gain={tadc_gain_signed}, offset={tadc_offset_signed}")

        # Check 3: ADC mode should be set
        if adc_24bit_en is not None:
            if verbose:
                mode = "24-bit" if is_24bit else "16-bit"
                print(f"  ✓  ADC mode: {mode}")
        else:
            warnings.append("Could not read ADC_24BIT_ENABLE register")

        # Check 4: OFF_EN consistency
        if offset_enable is not None:
            off_en_set = bool(offset_enable & 0x01)
            if verbose:
                order = "offset then gain" if off_en_set else "gain then offset"
                print(f"  ✓  OFF_EN={int(off_en_set)} ({order})")
        else:
            warnings.append("Could not read OFFSET_ENABLE register")

        # Check 5: DAC should be enabled
        dac_en = afe_raw.get("DAC_CTRL_STATUS")
        if dac_en is not None and not (dac_en & 0x01):
            warnings.append("DAC is DISABLED - sensor will not produce output")
        elif dac_en is not None:
            if verbose:
                print(f"  ✓  DAC is enabled")

        # Check 6: Bridge should be enabled
        brdg = afe_raw.get("BRDG_CTRL")
        if brdg is not None and not (brdg & 0x01):
            warnings.append("Bridge excitation is DISABLED - sensor cannot measure pressure")
        elif brdg is not None:
            if verbose:
                print(f"  ✓  Bridge excitation is enabled")

        # Check 7: NORMAL_HIGH should be set (typically 0x3FFF for 14-bit DAC)
        if normal_high is not None:
            if normal_high == 0x3FFF:
                if verbose:
                    print(f"  ✓  NORMAL_HIGH=0x3FFF (14-bit full-scale)")
            elif normal_high == 0:
                warnings.append("NORMAL_HIGH is 0 - DAC output range may be wrong")
            else:
                if verbose:
                    print(f"  i  NORMAL_HIGH=0x{normal_high:04X} (custom range)")

        # Check 8: All-0xFF check (erased EEPROM)
        all_ff = all(
            coefficients.get(name) == 0xFFFFFF
            for name in coeff_names
            if coefficients.get(name) is not None
        )
        if all_ff:
            warnings.append("All coefficients are 0xFFFFFF - EEPROM may be erased/blank")

        # Print warnings
        if warnings:
            if verbose:
                print(f"\n  {'_'*60}")
                print(f"  WARNINGS ({len(warnings)}):")
                for w in warnings:
                    print(f"    ! {w}")
        else:
            if verbose:
                print(f"\n  ✓  All consistency checks passed")

    else:
        # No coefficients found
        if verbose:
            print("\n  ! ALL calibration coefficients are ZERO")
            print("    This sensor does NOT appear to be calibrated.")
            print()
            print("    Recommended actions:")
            print("      1. Run the LabVIEW calibration procedure")
            print("      2. Use '06_-_Set_Cal_Coefficients.vi' to program coefficients")
            print("      3. Verify calibration data files exist for this part number")

    # =========================================================================
    # Build and return result dict
    # =========================================================================
    result = {
        'part_number': part_number,
        'serial_number': serial_number,
        'prange': prange_val,
        'coefficients': coefficients,
        'padc_gain': padc_gain,
        'padc_offset': padc_offset,
        'tadc_gain': tadc_gain,
        'tadc_offset': tadc_offset,
        'adc_24bit': is_24bit,
        'offset_enable': bool(offset_enable & 0x01) if offset_enable is not None else None,
        'normal_high': normal_high,
        'normal_low': normal_low,
        'dac_coefficients': dac_coefficients,
        'afe_config': afe_raw,
        'is_calibrated': has_coefficients,
        'cal_type': f"{temp_points}T{pressure_points}P" if has_coefficients else None,
        'warnings': warnings,
    }

    return result


def run_calibration_verification():
    """
    Main function for running calibration verification from the menu.
    """
    print("\n" + "=" * 70)
    print("           PGA305 CALIBRATION VERIFICATION")
    print("=" * 70)
    print("\nReads all calibration-related registers from the PGA305 EEPROM")
    print("and verifies that the calibration data is complete and consistent.")
    print()

    # Get channel from user
    channel_input = input(f"Enter channel number (0-7) [default: {config.CHANNEL}]: ").strip()
    channel = int(channel_input) if channel_input else config.CHANNEL

    if channel < 0 or channel > 7:
        print("ERROR: Channel must be between 0 and 7")
        return

    # Initialize reader
    reader = PGA305Reader()

    try:
        print(f"\nConnecting to {config.SERIAL_PORT}...")
        reader.connect()

        board_id = reader.get_board_identity()
        print(f"Board: {board_id}")

        print(f"\n{'='*70}")
        print(f"CHANNEL {channel} - FULL CALIBRATION VERIFICATION")
        print(f"{'='*70}")

        result = verify_calibration(reader, channel, verbose=True)

        if result is None:
            print("\n✗ ERROR: Failed to read calibration data")
        else:
            print(f"\n{'='*70}")
            print("RESULT")
            print(f"{'='*70}")

            if result['part_number']:
                print(f"  Sensor:      {result['part_number']} (SN: {result['serial_number']})")

            if result['is_calibrated']:
                print(f"  Status:      ✓ CALIBRATED ({result['cal_type']})")
            else:
                print(f"  Status:      ! NOT CALIBRATED")

            if result['warnings']:
                print(f"  Warnings:    {len(result['warnings'])}")
                for w in result['warnings']:
                    print(f"               ! {w}")
            elif result['is_calibrated']:
                print(f"  Consistency: ✓ All checks passed")

            print(f"{'='*70}")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        reader.disconnect()


if __name__ == "__main__":
    run_calibration_verification()