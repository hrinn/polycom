import time
import threading

class Display:
    def __init__(self, dev):
        self.dev = dev
        self.timer = None

        # Initial feature report required for display ops
        dev.send_feature_report([0x17, 0x09, 0x04, 0x01, 0x02])

    def clear(self):
        self.dev.write([0x13, 0x00])
        time.sleep(0.05)

    def set_two_lines(self):
        self.dev.write([0x13, 0x15])
        time.sleep(0.05)

    def select_top_line(self):
        self.dev.write([0x14, 0x05, 0x80])
        time.sleep(0.05)

    def select_bottom_line(self):
        self.dev.write([0x14, 0x0A, 0x80])
        time.sleep(0.05)

    def write(self, msg: str):
        for i in range(0, len(msg), 8):
            chunk = msg[i:i+8]

            stop = 0x80 if (i + 8 >= len(msg)) else 0x00
            report = ([0x15, stop])

            for c in chunk:
                report.extend([ord(c), 0x00])

            report.extend([0x00, 0x00] * (8 - len(chunk)))
            assert len(report) == 18

            self.dev.write(report)
            time.sleep(0.05)

        print(f"Wrote '{msg}'")

    def write_screen(self, top_msg: str = "", bottom_msg: str = ""):
        if self.timer:
            self.timer.cancel()
        self.clear()
        self.set_two_lines()
        if top_msg != "":
            self.select_top_line()
            self.write(top_msg)
        if bottom_msg != "":
            self.select_bottom_line()
            self.write(bottom_msg)

    def write_default_message(self):
        self.write_screen("Welcome to pookie phone!", "Lift handset to begin.")

    def write_screen_temp(self, top_msg: str = "", bottom_msg: str = "", time: float = 5.0):
        if self.timer:
            self.timer.cancel()
        self.write_screen(top_msg, bottom_msg)
        self.timer = threading.Timer(time, self.write_default_message)
        self.timer.start()