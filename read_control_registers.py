import config
from pga305_reader import PGA305Reader
from control_status_registers import REGISTERS

class ReadControlRegisters:

    def __init__(self, channel=1):
        self.channel = channel
        self.reader = PGA305Reader()

    # Page 0x0 registers — hardcoded here since they're small and stable
    PAGE0_REGISTERS = {
        0x00: "REVISION_ID1",
        0x01: "REVISION_ID2",
        0x04: "COM_MCU_TO_DIF_B1",
        0x05: "COM_MCU_TO_DIF_B2",
        0x06: "COM_TX_STATUS",
        0x08: "COM_DIF_TO_MCU_B1",
        0x09: "COM_DIF_TO_MCU_B2",
        0x0A: "COM_RX_STATUS",
        0x0B: "COM_RX_INT_ENABLE",
        0x0C: "COMPENSATION_CONTROL",
        0x0D: "SECLOCK",
        0xF4: "AFE_CFG",
    }

    def run(self):
        print("\n" + "="*70)
        print(f"READ CONTROL REGISTERS — CHANNEL {self.channel}")
        print("="*70)

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            print(f"Switching to channel {self.channel}...")
            self.reader.set_channel(self.channel)

            print("Entering command mode...")
            if not self.reader.enter_command_mode():
                print("ERROR: Could not enter command mode")
                return

            print("Command mode active\n")
            self._print_registers()
            self._edit_menu()

        except Exception as e:
            print(f"\nERROR: {e}")

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

    def _print_registers(self):
        print("-" * 70)
        print("PAGE 0x0 — Runtime / Communication  (I2C 0x20)")
        print("-" * 70)
        for addr, name in self.PAGE0_REGISTERS.items():
            val = self.reader.read_register(addr, config.PGA305_I2C_ADDR)
            if val is None:
                print(f"  0x{addr:02X}  {name:<30}  READ FAILED")
            else:
                print(f"  0x{addr:02X}  {name:<30}  0x{val:02X}  ({val:3d})")

        print("-" * 70)
        print("PAGE 0x2 — Control and Status  (I2C 0x22)")
        print("-" * 70)
        for addr, name in REGISTERS.items():
            val = self.reader.read_register(addr, config.I2C_CONTROL)
            if val is None:
                print(f"  0x{addr:02X}  {name:<30}  READ FAILED")
            else:
                print(f"  0x{addr:02X}  {name:<30}  0x{val:02X}  ({val:3d})")

        print("\n" + "="*70)
        print("CONTROL REGISTER READ COMPLETE")
        print("="*70)

    def _edit_menu(self):
        while True:
            print("\n" + "-"*70)
            print("  W. Write a register")
            print("  R. Re-read all registers")
            print("  X. Exit")
            print("-"*70)
            choice = input("Select option: ").strip().upper()

            if choice == 'X':
                break

            elif choice == 'R':
                if not self.reader.enter_command_mode():
                    print("ERROR: Could not enter command mode")
                    continue
                self._print_registers()

            elif choice == 'W':
                try:
                    page_input = input("Page (0 or 2): ").strip()
                    addr_input = input("Register address (e.g. 0x0B): ").strip()
                    val_input  = input("Value (e.g. 0x01): ").strip()

                    page = int(page_input)
                    addr = int(addr_input, 16)
                    val  = int(val_input, 16)

                    if page == 0:
                        i2c_addr = config.PGA305_I2C_ADDR
                        name = self.PAGE0_REGISTERS.get(addr, f"0x{addr:02X}")
                    elif page == 2:
                        i2c_addr = config.I2C_CONTROL
                        name = REGISTERS.get(addr, f"0x{addr:02X}")
                    else:
                        print("ERROR: Invalid page — must be 0 or 2")
                        continue

                    current = self.reader.read_register(addr, i2c_addr)
                    print(f"  {name} current: 0x{current:02X}")

                    if not self.reader.write_register(addr, val, i2c_addr):
                        print("ERROR: Write failed")
                        continue

                    readback = self.reader.read_register(addr, i2c_addr)
                    print(f"  {name} after:   0x{readback:02X}")

                except ValueError:
                    print("ERROR: Invalid input")