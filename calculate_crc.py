def calculate_eeprom_crc(data: list, initial_crc: int = 0x00) -> int:

    crc = initial_crc

    for byte in data:
        c = [(crc  >> i) & 1 for i in range(8)]
        d = [(byte >> i) & 1 for i in range(8)]

        next_crc = 0
        next_crc |= (d[7] ^ d[6] ^ d[0] ^ c[0] ^ c[6] ^ c[7])                       << 0
        next_crc |= (d[6] ^ d[1] ^ d[0] ^ c[0] ^ c[1] ^ c[6])                        << 1
        next_crc |= (d[6] ^ d[2] ^ d[1] ^ d[0] ^ c[0] ^ c[1] ^ c[2] ^ c[6])         << 2
        next_crc |= (d[7] ^ d[3] ^ d[2] ^ d[1] ^ c[1] ^ c[2] ^ c[3] ^ c[7])         << 3
        next_crc |= (d[4] ^ d[3] ^ d[2] ^ c[2] ^ c[3] ^ c[4])                        << 4
        next_crc |= (d[5] ^ d[4] ^ d[3] ^ c[3] ^ c[4] ^ c[5])                        << 5
        next_crc |= (d[6] ^ d[5] ^ d[4] ^ c[4] ^ c[5] ^ c[6])                        << 6
        next_crc |= (d[7] ^ d[6] ^ d[5] ^ c[5] ^ c[6] ^ c[7])                        << 7

        crc = next_crc & 0xFF

    return crc


if __name__ == "__main__":
    # Verification test against LabVIEW probe data
    # Current CRC going into page E = 0x5F (95)
    # Page E bytes = 7B, 29, 00, 0D, 00, 00, 64, 00
    # Expected updated CRC = 0xE3 (227)

    probe_crc   = 0x5F
    page_e_data = [0x7B, 0x29, 0x00, 0x0D, 0x00, 0x00, 0x64, 0x00]
    expected    = 0xE3

    result = calculate_eeprom_crc(page_e_data, initial_crc=probe_crc)

    print(f"Input CRC  : 0x{probe_crc:02X} ({probe_crc})")
    print(f"Page data  : {[f'0x{b:02X}' for b in page_e_data]}")
    print(f"Result     : 0x{result:02X} ({result})")
    print(f"Expected   : 0x{expected:02X} ({expected})")
    print(f"Match      : {result == expected}")