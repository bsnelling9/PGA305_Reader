import config
from pga305_reader import PGA305Reader
from typing import Optional
## This can probably be removed
# I2C address for UART registers (page 0x7)
UART_I2C_ADDR = 0x27

# UART register offsets
UART_CONFIG = 0x00
UART_EN = 0x01
BAUD_RATE_LO = 0x02
BAUD_RATE_HI = 0x03
UART_LINE_STATUS = 0x04
UART_INTERRUPT_STATUS = 0x08
UART_INTERRUPT_ENABLE = 0x0A
UART_RX_BUF_0 = 0x0C
UART_RX_BUF_1 = 0x0E


class HandleUART:
    """
    Reads and displays UART configuration registers from a PGA305 sensor.
    Page 0x7, I2C address 0x27.
    """

    def __init__(self, channel=1):
        self.channel = channel
        self.reader = PGA305Reader()

    def run(self):
        print("\n" + "="*70)
        print(f"UART REGISTERS — CHANNEL {self.channel}")
        print("="*70)

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            print(f"Switching to channel {self.channel}...")
            self.reader.set_channel(self.channel)

            print("Entering command mode...")
            if not self.reader.enter_command_mode():
                print("ERROR: Could not enter command mode")
                return False

            print("Command mode active\n")

            self._read_uart_config()
            self._read_uart_en()
            self._read_baud_rate()
            self._read_line_status()
            self._read_interrupt_status()
            self._read_interrupt_enable()
            self._read_rx_buf()

            return True

        except Exception as e:
            print(f"\nERROR: {e}")
            return False

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _read(self, reg: int) -> Optional[int]:
        return self.reader.read_register(reg, UART_I2C_ADDR)

    def _read_uart_config(self):
        val = self._read(UART_CONFIG)
        if val is None:
            print("UART_CONFIG (0x27/0x00): READ FAILED")
            return
        print(f"UART_CONFIG (0x27/0x00): 0x{val:02X} ({val:08b}b)")
        print(f"  TWO_STOP_BITS (bit 2): {(val >> 2) & 1}")
        print(f"  PARITY        (bit 1): {(val >> 1) & 1}")
        print(f"  PARITY_EN     (bit 0): {val & 1}")

    def _read_uart_en(self):
        val = self._read(UART_EN)
        if val is None:
            print("UART_EN (0x27/0x01): READ FAILED")
            return
        print(f"\nUART_EN (0x27/0x01): 0x{val:02X} ({val:08b}b)")
        print(f"  UART_EN (bit 0): {val & 1}")

    def _read_baud_rate(self):
        lo = self._read(BAUD_RATE_LO)
        hi = self._read(BAUD_RATE_HI)
        if lo is None or hi is None:
            print("BAUD_RATE: READ FAILED")
            return
        baud = lo | (hi << 8)
        print(f"\nBAUD_RATE_LO (0x27/0x02): 0x{lo:02X}")
        print(f"BAUD_RATE_HI (0x27/0x03): 0x{hi:02X}")
        print(f"  Combined baud rate value: 0x{baud:04X} ({baud})")

    def _read_line_status(self):
        val = self._read(UART_LINE_STATUS)
        if val is None:
            print("UART_LINE_STATUS (0x27/0x04): READ FAILED")
            return
        print(f"\nUART_LINE_STATUS (0x27/0x04): 0x{val:02X} ({val:08b}b)")
        print(f"  TX_COMPLETE    (bit 4): {(val >> 4) & 1}")
        print(f"  RX_READY       (bit 3): {(val >> 3) & 1}")
        print(f"  FRAMING_ERROR  (bit 2): {(val >> 2) & 1}")
        print(f"  PARITY_ERROR   (bit 1): {(val >> 1) & 1}")
        print(f"  OVERRUN_ERROR  (bit 0): {val & 1}")

    def _read_interrupt_status(self):
        val = self._read(UART_INTERRUPT_STATUS)
        if val is None:
            print("UART_INTERRUPT_STATUS (0x27/0x08): READ FAILED")
            return
        print(f"\nUART_INTERRUPT_STATUS (0x27/0x08): 0x{val:02X} ({val:08b}b)")
        print(f"  UART_TXCOMPLETE_I (bit 1): {(val >> 1) & 1}")
        print(f"  UART_RXCOMPLETE_I (bit 0): {val & 1}")

    def _read_interrupt_enable(self):
        val = self._read(UART_INTERRUPT_ENABLE)
        if val is None:
            print("UART_INTERRUPT_ENABLE (0x27/0x0A): READ FAILED")
            return
        print(f"\nUART_INTERRUPT_ENABLE (0x27/0x0A): 0x{val:02X} ({val:08b}b)")
        print(f"  UART_TXCOMPLET_INT_EN (bit 1): {(val >> 1) & 1}")
        print(f"  UART_RXRDY_INT_EN     (bit 0): {val & 1}")

    def _read_rx_buf(self):
        buf0 = self._read(UART_RX_BUF_0)
        buf1 = self._read(UART_RX_BUF_1)
        if buf0 is None or buf1 is None:
            print("UART_RX_BUF: READ FAILED")
            return
        print(f"\nUART_RX_BUF_0 (0x27/0x0C): 0x{buf0:02X}")
        print(f"UART_RX_BUF_1 (0x27/0x0E): 0x{buf1:02X}")