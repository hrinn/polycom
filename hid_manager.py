import hid
import time
import sys
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

# Statics
VENDOR_ID = 0x095D
PRODUCT_ID = 0x9201

class Flag:
    def __init__(self, data):
        self.data = data

    def is_redial_down(self):
        return self.data & 0x04

    def is_flash_down(self):
        return self.data & 0x02

    def is_delete_down(self):
        return self.data & 0x20

    def is_mute_down(self):
        return self.data & 0x10

    def is_hook_up(self):
        return self.data & 0x01

    def __repr__(self):
        return f"0x{self.data:02x}"

class Key(Enum):
    NO_KEY = 0x00
    KEYPAD_0_DOWN = 0x01
    KEYPAD_1_DOWN = 0x02
    KEYPAD_2_DOWN = 0x03
    KEYPAD_3_DOWN = 0x04
    KEYPAD_4_DOWN = 0x05
    KEYPAD_5_DOWN = 0x06
    KEYPAD_6_DOWN = 0x07
    KEYPAD_7_DOWN = 0x08
    KEYPAD_8_DOWN = 0x09
    KEYPAD_9_DOWN = 0x0A
    KEYPAD_STAR_DOWN = 0x0B
    KEYPAD_DASH_DOWN = 0x0C

key_char_map = {
    Key.KEYPAD_0_DOWN: "0",
    Key.KEYPAD_1_DOWN: "1",
    Key.KEYPAD_2_DOWN: "2",
    Key.KEYPAD_3_DOWN: "3",
    Key.KEYPAD_4_DOWN: "4",
    Key.KEYPAD_5_DOWN: "5",
    Key.KEYPAD_6_DOWN: "6",
    Key.KEYPAD_7_DOWN: "7",
    Key.KEYPAD_8_DOWN: "8",
    Key.KEYPAD_9_DOWN: "9",
    Key.KEYPAD_STAR_DOWN: "*",
    Key.KEYPAD_DASH_DOWN: "#"
}

class AudioDevice(Enum):
    HANDSET = 0x40
    SPEAKER = 0x50
    HEADSET = 0x60
    NO_CHANGE = 0x00
    SPEAKER_LOUD = 0x01
    SPEAKER_LOUDER = 0x02
    UNKNOWN = 0xFF
    
VOLUME_MAP = {
    0x700B: 1,
    0x2710: 2,
    0xD116: 3,
    0x3B20: 4,
    0x862D: 5,
    0x4E40: 6,
    0xD55A: 7,
    0x4E80: 8,
    0x3CB5: 9,
    0xFFFF: 10
}

@dataclass
class PhonePacket:
    flag: Flag
    button_pressed: Key
    receiving_audio: bool
    audio_device: AudioDevice
    volume_level: int
    muted: bool

def decode(data: bytes) -> PhonePacket:
    flag = Flag(data[1])

    try:    
        button_pressed = Key(data[2])
    except ValueError:
        print(f"Failed to get button_pressed: {data[2]:0x}")
        return None

    try:
        if data[4] == 0x52:
            audio_device = AudioDevice.SPEAKER
        else:
            audio_device = AudioDevice(data[4])
    except ValueError:
        print(f"Failed to get audio_device: {data[4]:0x}")
        return None

    receiving_audio = data[3] == 0x00

    try:
        volume_level = VOLUME_MAP[int.from_bytes(data[5:7], byteorder='big')]
    except KeyError:
        print(f"Failed to get volume_level: {data[5:7].hex(' ')}")
        return None

    muted = data[7] != 0x00

    return PhonePacket(
        flag,
        button_pressed,
        receiving_audio,
        audio_device,
        volume_level,
        muted
    )

def hook_change(hook_up: bool):
    print(f"Hook up: {hook_up}")

def hangup_call():
    print("Hanging up")

def handle_key_char(c: str):
    print(f"Pressed char: {c}")

def handle_delete():
    print("Delete")

phone_handlers = {
    "on_hook_change": hook_change,
    "key_char": handle_key_char,
    "delete": handle_delete,
}

def install_handler(key: str, handler):
    if not key in phone_handlers:
        print(f"Attempted to install invalid handler key: {key}")
        sys.exit(1)

    phone_handlers[key] = handler

class PhoneState():
    def __init__(self):
        self.picked_up: bool = False
        self.picked_up_device: Optional[AudioDevice] = None

    def process_packet(self, packet: PhonePacket):
        # Handle key char presses
        if packet.button_pressed in key_char_map:
            phone_handlers["key_char"](key_char_map[packet.button_pressed])
            return

        # Handle delete presses
        if packet.flag.is_delete_down():
            phone_handlers["delete"]()
            return

        # Handle pick ups
        if not self.picked_up and packet.flag.is_hook_up():
            self.picked_up = True
            self.picked_up_device = packet.audio_device
            phone_handlers["on_hook_change"](self.picked_up)
            return

        # Handle hang ups
        if (
            self.picked_up and
            packet.button_pressed == Key.NO_KEY and
            not packet.flag.is_hook_up() and
            packet.audio_device != AudioDevice.NO_CHANGE and
            packet.audio_device != self.picked_up_device
            ):
            self.picked_up = False
            self.picked_up_device = None
            phone_handlers["on_hook_change"](self.picked_up)
            return

        # Other packets are dropped

def init_hid_manager():
    dev = hid.device()
    dev.open(VENDOR_ID, PRODUCT_ID)

    print(f"Connected to {VENDOR_ID:04X}:{PRODUCT_ID:04X}")
    print(f"Manufacturer: {dev.get_manufacturer_string()}")
    print(f"Product: {dev.get_product_string()}")
    print(f"Serial No: {dev.get_serial_number_string()}")

    return dev

def start_hid_manager(dev):
    # Read loop
    phone_state = PhoneState()
    try:
        while True:
            data = dev.read(8, timeout_ms=1000)

            if not data:
                continue

            data = bytes(data)
            # print("RX:", data.hex(" "))

            if data[0] == 0x01:
                packet = decode(data)
                if packet:
                    print(packet)
                    phone_state.process_packet(packet)
    finally:
        dev.close()


if __name__ == '__main__':
    dev = init_hid_manager()
    start_hid_manager(dev)
