# This is the entire EEPROM page mapping
EEPROM_REGISTERS = {
    # PAGE 0-1 — H Coefficients (0x00–0x0B)
    0x00: "H0_LSB",
    0x01: "H0_MID",
    0x02: "H0_MSB",
    0x03: "H1_LSB",
    0x04: "H1_MID",
    0x05: "H1_MSB",
    0x06: "H2_LSB",
    0x07: "H2_MID",
    0x08: "H2_MSB",
    0x09: "H3_LSB",
    0x0A: "H3_MID",
    0x0B: "H3_MSB",

    # PAGE 1-2 — G Coefficients (0x0C–0x17)
    0x0C: "G0_LSB",
    0x0D: "G0_MID",
    0x0E: "G0_MSB",
    0x0F: "G1_LSB",
    0x10: "G1_MID",
    0x11: "G1_MSB",
    0x12: "G2_LSB",
    0x13: "G2_MID",
    0x14: "G2_MSB",
    0x15: "G3_LSB",
    0x16: "G3_MID",
    0x17: "G3_MSB",

    # PAGE 3 — N Coefficients (0x18–0x23)
    0x18: "N0_LSB",
    0x19: "N0_MID",
    0x1A: "N0_MSB",
    0x1B: "N1_LSB",
    0x1C: "N1_MID",
    0x1D: "N1_MSB",
    0x1E: "N2_LSB",
    0x1F: "N2_MID",
    0x20: "N2_MSB",
    0x21: "N3_LSB",
    0x22: "N3_MID",
    0x23: "N3_MSB",

    # PAGE 4-5 — M Coefficients (0x24–0x2F)
    0x24: "M0_LSB",
    0x25: "M0_MID",
    0x26: "M0_MSB",
    0x27: "M1_LSB",
    0x28: "M1_MID",
    0x29: "M1_MSB",
    0x2A: "M2_LSB",
    0x2B: "M2_MID",
    0x2C: "M2_MSB",
    0x2D: "M3_LSB",
    0x2E: "M3_MID",
    0x2F: "M3_MSB",

    # PAGE 6 — Analog Config (mirrored from runtime, 0x30–0x37)
    # NOTE: These are the EEPROM-stored copies of runtime registers.
    #       Runtime equivalents live at different addresses on I2C 0x22.
    0x30: "DIG_IF_CTRL",       # runtime: 0x22/0x06
    0x31: "DAC_CTRL_STATUS",   # runtime: 0x22/0x38
    0x32: "DAC_CONFIG",        # runtime: 0x22/0x39
    0x33: "OP_STAGE_CTRL",     # runtime: 0x22/0x3B
    0x34: "BRDG_CTRL",         # runtime: 0x22/0x46
    0x35: "P_GAIN_SELECT",     # runtime: 0x22/0x47
    0x36: "T_GAIN_SELECT",     # runtime: 0x22/0x48
    0x37: "TEMP_CTRL",         # runtime: 0x22/0x4C

    # PAGE 7 — Temperature / Normal Range (0x38–0x3F)
    # NOTE: 0x38, 0x39, 0x3B are reserved/unnamed in datasheet
    0x38: "ADD_0x38",
    0x39: "ADD_0x39",
    0x3A: "TEMP_SE",
    0x3B: "ADD_0x3B",
    0x3C: "NORMAL_LOW_LSB",
    0x3D: "NORMAL_LOW_MSB",
    0x3E: "NORMAL_HIGH_LSB",
    0x3F: "NORMAL_HIGH_MSB",

    # PAGE 8 — Clamp / PADC Gain (0x40–0x47)
    0x40: "LOW_CLAMP_LSB",
    0x41: "LOW_CLAMP_MSB",
    0x42: "HIGH_CLAMP_LSB",
    0x43: "HIGH_CLAMP_MSB",
    0x44: "PADC_GAIN_LSB",
    0x45: "PADC_GAIN_MID",
    0x46: "PADC_GAIN_MSB",
    0x47: "PADC_OFFSET_LSB",

    # PAGE 9 — PADC Offset / A Coefficients (0x48–0x4F)
    0x48: "PADC_OFFSET_MID",
    0x49: "PADC_OFFSET_MSB",
    0x4A: "A0_LSB",
    0x4B: "A0_MSB",
    0x4C: "A1_LSB",
    0x4D: "A1_MSB",
    0x4E: "A2_LSB",
    0x4F: "A2_MSB",

    # PAGE A — B Coefficients / Diagnostics (0x50–0x57)
    0x50: "B0_LSB",
    0x51: "B0_MSB",
    0x52: "B1_LSB",
    0x53: "B1_MSB",
    0x54: "B2_LSB",
    0x55: "B2_MSB",
    0x56: "DIAG_ENABLE",
    0x57: "EEPROM_LOCK",

    # PAGE B — AFE Diagnostics / TADC Gain (0x58–0x5F)
    0x58: "AFEDIAG_CFG",
    0x59: "AFEDIAG_MASK",
    0x5A: "ADD_0x5A",
    0x5B: "ADD_0x5B",
    0x5C: "FAULT_LSB",
    0x5D: "FAULT_MSB",
    0x5E: "TADC_GAIN_LSB",
    0x5F: "TADC_GAIN_MID",

    # PAGE C — TADC Gain/Offset / Serial Number (0x60–0x67)
    0x60: "TADC_GAIN_MSB",
    0x61: "TADC_OFFSET_LSB",
    0x62: "TADC_OFFSET_MID",
    0x63: "TADC_OFFSET_MSB",
    0x64: "SERIAL_NUMBER_BYTE0",
    0x65: "SERIAL_NUMBER_BYTE1",
    0x66: "SERIAL_NUMBER_BYTE2",
    0x67: "SERIAL_NUMBER_BYTE3",

    # PAGE D — ADC Config (0x68–0x6F)
    0x68: "ADC_24BIT_ENABLE",
    0x69: "OFFSET_ENABLE",
    0x6A: "ADD_0x6A",
    0x6B: "ADD_0x6B",
    0x6C: "ADD_0x6C",
    0x6D: "ADD_0x6D",
    0x6E: "ADD_0x6E",
    0x6F: "ADD_0x6F",

    # PAGE E — Part Number / Serial / Pressure Range (0x70–0x77)
    # Only used for full EEPROM read
    0x70: "PN_LSB",
    0x71: "PN_MID",
    0x72: "PN_MSB",
    0x73: "SN_LSB",
    0x74: "SN_MID",
    0x75: "SN_MSB",
    0x76: "PRANGE_LSB",
    0x77: "PRANGE_MSB",

    # PAGE F — Reserved / CRC (0x78–0x7F)
    0x78: "ADD_0x78",
    0x79: "ADD_0x79",
    0x7A: "ADD_0x7A",
    0x7B: "ADD_0x7B",
    0x7C: "ADD_0x7C",
    0x7D: "ADD_0x7D",
    0x7E: "ADD_0x7E",
    0x7F: "EEPROM_CRC_VALUE",

    # EEPROM Cache (0x80–0x87)
    # Read-only mirror of last read/written EEPROM page
    0x80: "EEPROM_CACHE_LO1",
    0x81: "EEPROM_CACHE_LO2",
    0x82: "EEPROM_CACHE_LO3",
    0x83: "EEPROM_CACHE_LO4",
    0x84: "EEPROM_CACHE_HI1",
    0x85: "EEPROM_CACHE_HI2",
    0x86: "EEPROM_CACHE_HI3",
    0x87: "EEPROM_CACHE_HI4",

    # EEPROM Control Registers (0x88–0x8D)
    # CRITICAL: These must be used to program/erase EEPROM
    0x88: "EEPROM_PAGE_ADDRESS",  # Set page before read/write
    0x89: "EEPROM_CTRL",          # Bits: ERASE_AND_PROGRAM, ERASE, PROGRAM
    0x8A: "EEPROM_CRC",           # Write 1 to CALCULATE_CRC to trigger CRC
    0x8B: "EEPROM_STATUS",        # Bits: PROGRAM_IN_PROGRESS, ERASE_IN_PROGRESS, READ_IN_PROGRESS
    0x8C: "EEPROM_CRC_STATUS",    # Bits: CRC_GOOD, CRC_CHECK_IN_PROGRESS
    0x8D: "EEPROM_CRC_VALUE",     # Calculated CRC result
}

EEPROM_ID_MAP = {
    "PN":     [0x70, 0x71, 0x72],
    "SN":     [0x73, 0x74, 0x75],
    "PRANGE": [0x76, 0x77],
}


EEPROM_CACHE = {
    0x80: "EEPROM_CACHE_LO1",
    0x81: "EEPROM_CACHE_LO2",
    0x82: "EEPROM_CACHE_LO3",
    0x83: "EEPROM_CACHE_LO4",
    0x84: "EEPROM_CACHE_HI1",
    0x85: "EEPROM_CACHE_HI2",
    0x86: "EEPROM_CACHE_HI3",
    0x87: "EEPROM_CACHE_HI4",
}

EEPROM_CACHE_BASE    = 0x80
EEPROM_PAGE_ADDR_REG = 0x88
EEPROM_CTRL_REG      = 0x89
EEPROM_STATUS_REG    = 0x8B

# ---------------------------------------------------------------------------
# EEPROM_CTRL register bits (0x25/0x89)
# Write these to trigger EEPROM operations
# ---------------------------------------------------------------------------
EEPROM_CTRL_PROGRAM            = 0x01
EEPROM_CTRL_ERASE              = 0x02
EEPROM_CTRL_ERASE_AND_PROGRAM  = 0x04
EEPROM_CTRL_FIXED_TIME         = 0x08

# EEPROM_STATUS register bits (0x25/0x8B)
EEPROM_STATUS_READ_IN_PROGRESS    = 0x01
EEPROM_STATUS_ERASE_IN_PROGRESS   = 0x02
EEPROM_STATUS_PROGRAM_IN_PROGRESS = 0x04
# ---------------------------------------------------------------------------
# Page boundary labels for display grouping
# ---------------------------------------------------------------------------
EEPROM_PAGES = {
    0x00: "PAGE 0-1  — H Coefficients",
    0x0C: "PAGE 1-2  — G Coefficients",
    0x18: "PAGE 3    — N Coefficients",
    0x24: "PAGE 4-5  — M Coefficients",
    0x30: "PAGE 6    — Analog Config (EEPROM mirror)",
    0x38: "PAGE 7    — Temperature / Normal Range",
    0x40: "PAGE 8    — Clamp / PADC Gain",
    0x48: "PAGE 9    — PADC Offset / A Coefficients",
    0x50: "PAGE A    — B Coefficients / Diagnostics",
    0x58: "PAGE B    — AFE Diagnostics / TADC Gain",
    0x60: "PAGE C    — TADC Gain/Offset / Serial Number",
    0x68: "PAGE D    — ADC Config",
    0x70: "PAGE E    — Part Number / Serial / PRange",
    0x78: "PAGE F    — Reserved / CRC",
    0x80: "EEPROM Cache (read-only)",
    0x88: "EEPROM Control Registers",
}

COEFFICIENTS_MAP = {
    "H0": [0x00, 0x01, 0x02], "H1": [0x03, 0x04, 0x05], "H2": [0x06, 0x07, 0x08], "H3": [0x09, 0x0A, 0x0B],
    "G0": [0x0C, 0x0D, 0x0E], "G1": [0x0F, 0x10, 0x11], "G2": [0x12, 0x13, 0x14], "G3": [0x15, 0x16, 0x17],
    "N0": [0x18, 0x19, 0x1A], "N1": [0x1B, 0x1C, 0x1D], "N2": [0x1E, 0x1F, 0x20], "N3": [0x21, 0x22, 0x23],
    "M0": [0x24, 0x25, 0x26], "M1": [0x27, 0x28, 0x29], "M2": [0x2A, 0x2B, 0x2C], "M3": [0x2D, 0x2E, 0x2F],
    "TADC_GAIN": [0x5E, 0x5F, 0x60],
    "TADC_OFFSET": [0x61, 0x62, 0x63],
    "PADC_GAIN": [0x44, 0x45, 0x46],
    "PADC_OFFSET": [0x47, 0x48, 0x49],
    "OFF_EN": [0x69]
}
