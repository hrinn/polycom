import sys
import time

from dataclasses import dataclass

from hid_manager import init_hid_manager, start_hid_manager, install_handler
from sip_manager import SIPManager
from display import Display

@dataclass
class Contact:
    name: str
    sip: str
    number: int
    is_me: bool = False

    def get_username(self) -> str:
        return self.sip[4:].split("@")[0]

contacts = [
    Contact("hayden", "sip:haydentty@sip.linphone.org", 5235),
    Contact("astrid", "sip:freshcage@sip.linphone.org", 9328),
]

def select_my_contact(username: str):
    for contact in contacts:
        if contact.get_username() == username:
            contact.is_me = True
            print(f"Selected my contact: {contact}")
            return

class PhoneApp:
    def __init__(self, username, password):
        self.username = username
        self.password = password

        self.dialed = ""
        self.hook_up = False

        # Initialize hardware
        self.hid_device = init_hid_manager()
        self.display = Display(self.hid_device)
        self.display.write_default_message()

        # Initialize SIP
        self.sip = SIPManager(
            username, password, self.on_incoming_call,
            on_disconnected=self.on_call_disconnected,
        )

        # Configure contacts
        select_my_contact(username)

        # Register HID callbacks
        install_handler("key_char", self.dial_putc)
        install_handler("delete", self.dial_delete)
        install_handler("on_hook_change", self.on_hook_change)

    def dial_putc(self, c: str):
        self.dialed += c

        if len(self.dialed) == 4:
            for contact in contacts:
                if not contact.is_me and int(self.dialed) == contact.number:
                    print(f"Dialing {contact.name} ({contact.number}) @ {contact.sip}")
                    self.display.write_screen(f"Calling {contact.name} - {contact.number}...")
                    self.sip.call(contact.sip, on_connected=self.on_call_connected)
                    return

            print(f"{self.dialed} is not a valid number!")
            self.display.write_screen_temp(f"No match for number {self.dialed}...", "Please try again.", 4.0)
            self.dialed = ""
        else:
            print(f"Dialed = {self.dialed}")
        

    def on_incoming_call(self):
        self.display.write_screen("Incoming call!")

    def on_call_connected(self):
        self.display.write_screen("Call connected")

    def on_call_disconnected(self):
        self.dialed = ""
        if self.hook_up:
            self.display.write_screen("Dial 4 digit number:")
        else:
            self.display.write_default_message()

    def on_hook_change(self, hook_up: bool):
        self.hook_up = hook_up
        print(f"hook up: {hook_up}")
        if hook_up:
            if self.sip.answer():
                self.on_call_connected()
            else:
                self.display.write_screen("Dial 4 digit number:")
        else:
            self.sip.hangup()
            self.display.write_default_message()

    def dial_delete(self):
        self.dialed = self.dialed[:-1]
        print(f"Dialed = {self.dialed}")

    def run(self):
        try:
            start_hid_manager(self.hid_device)
        finally:
            self.sip.close()

def main():
    if len(sys.argv) != 3:
        print("Usage: python polycom.py <username> <password>")
        sys.exit(1)

    username, password = sys.argv[1:3]

    app = PhoneApp(username, password)
    app.run()

if __name__ == "__main__":
    main()
