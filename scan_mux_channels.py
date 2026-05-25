import os
import csv
import datetime
import config
from pga305_reader import PGA305Reader

OUTPUT_DIR = "scan_channels_output"


class ScanMuxChannels:
    """
    Scans all channels repeatedly, reading part number, serial number,
    TADC and PADC from each PGA305. Saves results to a CSV file in
    scan_channels_output/ for timing analysis.
    """

    def __init__(self, iterations=10):
        self.iterations   = iterations
        self.num_channels = config.SCAN_NUM_CHANNELS
        self.reader       = PGA305Reader()
        self.results      = []

    def run(self):
        print("\n" + "="*70)
        print(f"CHANNEL SCAN — {self.num_channels} channels x {self.iterations} iterations")
        print("="*70)

        try:
            print(f"\nConnecting to {config.SERIAL_PORT}...")
            self.reader.connect()

            for iteration in range(1, self.iterations + 1):
                print(f"\n--- Iteration {iteration}/{self.iterations} ---")

                for channel in range(self.num_channels):
                    result = self._scan_channel(channel, iteration)
                    self.results.append(result)
                    self._print_result(result)

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.reader.disconnect_channel()
            self.reader.disconnect()

        self._save_csv()

    def _scan_channel(self, channel: int, iteration: int) -> dict:
        result = {
            'iteration':     iteration,
            'channel':       channel,
            'timestamp':     datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'part_number':   '',
            'serial_number': '',
            'tadc':          '',
            'padc':          '',
            'status':        'FAIL',
        }

        try:
            sensor = self.reader.read_sensor_data(channel, verbose=False)

            if sensor is None:
                result['status'] = 'CM_FAIL'
                return result

            result['part_number']   = sensor['part_number']
            result['serial_number'] = f"{sensor['serial_number']:06d}"

            self.reader.set_channel(channel)
            if not self.reader.enter_command_mode():
                result['status'] = 'CM_FAIL_ADC'
                return result

            tadc_lsb = self.reader.read_register(0x24, config.I2C_CONTROL)
            tadc_mid = self.reader.read_register(0x25, config.I2C_CONTROL)
            tadc_msb = self.reader.read_register(0x26, config.I2C_CONTROL)

            padc_lsb = self.reader.read_register(0x20, config.I2C_CONTROL)
            padc_mid = self.reader.read_register(0x21, config.I2C_CONTROL)
            padc_msb = self.reader.read_register(0x22, config.I2C_CONTROL)

            if None not in [tadc_lsb, tadc_mid, tadc_msb]:
                tadc = (tadc_msb << 16) | (tadc_mid << 8) | tadc_lsb
                if tadc > 8388607:
                    tadc -= 16777216
                result['tadc'] = tadc

            if None not in [padc_lsb, padc_mid, padc_msb]:
                padc = (padc_msb << 16) | (padc_mid << 8) | padc_lsb
                if padc > 8388607:
                    padc -= 16777216
                result['padc'] = padc

            result['status'] = 'OK'

        except Exception as e:
            result['status'] = f'ERROR: {e}'

        return result

    def _print_result(self, r: dict):
        status = r['status']
        ch     = r['channel']
        pn     = r['part_number'] or '---'
        sn     = r['serial_number'] or '---'
        tadc   = r['tadc'] if r['tadc'] != '' else '---'
        padc   = r['padc'] if r['padc'] != '' else '---'
        print(f"  CH{ch:02d}  {status:<12}  PN={pn:<8}  SN={sn}  TADC={tadc}  PADC={padc}")

    def _save_csv(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = os.path.join(OUTPUT_DIR, f"scan_{timestamp}.csv")

        headers = ['Iteration', 'Channel', 'Timestamp', 'Part Number',
                   'Serial Number', 'TADC', 'PADC', 'Status']

        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for r in self.results:
                writer.writerow({
                    'Iteration':     r['iteration'],
                    'Channel':       r['channel'],
                    'Timestamp':     r['timestamp'],
                    'Part Number':   r['part_number'],
                    'Serial Number': r['serial_number'],
                    'TADC':          r['tadc'] if r['tadc'] != '' else 'READ FAIL',
                    'PADC':          r['padc'] if r['padc'] != '' else 'READ FAIL',
                    'Status':        r['status'],
                })

        print(f"\nResults saved to: {filename}")
        print(f"   Total rows: {len(self.results)}")