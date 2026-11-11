import sys
import time
from pathlib import Path

import pjsua2 as pj
from sip_config import initialize_sip

class MyCall(pj.Call):
    def __init__(
        self, account, endpoint, call_id=pj.PJSUA_INVALID_ID, *,
        on_connected=None, on_disconnected=None,
    ):
        super().__init__(account, call_id)
        self.endpoint = endpoint
        self.disconnected = False
        self.audio_connected = False
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected

    def onCallState(self, prm):
        info = self.getInfo()
        print(f"Call state: {info.stateText}")

        if info.state == pj.PJSIP_INV_STATE_CONFIRMED and self.on_connected is not None:
            on_connected = self.on_connected
            self.on_connected = None
            on_connected()

        if info.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.disconnected = True
            print("Call disconnected")
            if self.on_disconnected is not None:
                self.on_disconnected()

    def onCallMediaState(self, prm):
        try:
            info = self.getInfo()
            audio_manager = self.endpoint.audDevManager()

            for media_info in info.media:
                if (
                    media_info.type == pj.PJMEDIA_TYPE_AUDIO
                    and media_info.status == pj.PJSUA_CALL_MEDIA_ACTIVE
                ):
                    if self.audio_connected:
                        continue

                    call_audio = self.getAudioMedia(media_info.index)

                    # Microphone -> remote caller
                    audio_manager.getCaptureDevMedia().startTransmit(
                        call_audio
                    )

                    # Remote caller -> speaker
                    call_audio.startTransmit(
                        audio_manager.getPlaybackDevMedia()
                    )

                    self.audio_connected = True
                    print("Two-way audio connected")

        except pj.Error as e:
            print(f"Audio connection error: {e}")

class MyAccount(pj.Account):
    def __init__(self, endpoint, on_incoming_call, on_disconnected=None):
        super().__init__()
        self.endpoint = endpoint
        self.on_incoming_call = on_incoming_call
        self.on_disconnected = on_disconnected
        self.current_call = None
        self.ringtone_player = None

    def start_ringtone(self):
        try:
            player = pj.AudioMediaPlayer()
            player.createPlayer(str(Path(__file__).with_name("ringtone.wav").resolve()))
            playback = self.endpoint.audDevManager().getPlaybackDevMedia()
            player.startTransmit(playback)
            self.ringtone_player = player
        except pj.Error as error:
            print(f"Could not play ringtone: {error}")

    def stop_ringtone(self):
        # Destroying the player removes its port from the conference bridge.
        self.ringtone_player = None

    def on_incoming_disconnected(self):
        self.stop_ringtone()
        if self.on_disconnected is not None:
            self.on_disconnected()

    def onIncomingCall(self, prm):
        print(f"\nIncoming call: {prm.callId}")

        if (
            self.current_call is not None
            and not self.current_call.disconnected
        ):
            print("Already handling a call; rejecting new call.")
            temp_call = pj.Call(self, prm.callId)
            reject = pj.CallOpParam()
            reject.statusCode = 486
            temp_call.answer(reject)
            return

        self.current_call = MyCall(
            self,
            self.endpoint,
            prm.callId,
            on_disconnected=self.on_incoming_disconnected,
        )
        self.start_ringtone()
        self.on_incoming_call()

        

class SIPManager:
    def __init__(self, username, password, on_incoming_call, *, on_disconnected=None):
        self.ep, acc_cfg = initialize_sip(username, password)
        self.account = MyAccount(self.ep, on_incoming_call, on_disconnected)

        self.account.create(acc_cfg)

        print("Waiting for SIP registration...")

        for _ in range(100):
            if self.account.getInfo().regIsActive:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("SIP registration failed or timed out")

        print(f"Registered as {username}@sip.linphone.org")
        print("Waiting for incoming calls. Press Ctrl+C to quit.")

    def answer(self) -> bool:
        call = self.account.current_call
        if call is None or call.disconnected:
            return False

        try:
            info = call.getInfo()
            if info.role != pj.PJSIP_ROLE_UAS or info.state not in (
                pj.PJSIP_INV_STATE_INCOMING,
                pj.PJSIP_INV_STATE_EARLY,
            ):
                return False

            answer = pj.CallOpParam()
            answer.statusCode = 200
            self.account.stop_ringtone()
            print("Answering...")
            call.answer(answer)
        except pj.Error as error:
            print(f"Could not answer call: {error}")
            return False

        return True

    def call(self, destination, *, on_connected=None):
        call = MyCall(
            self.account, self.ep, on_connected=on_connected,
            on_disconnected=self.account.on_disconnected,
        )

        prm = pj.CallOpParam(True)
        prm.opt.audioCount = 1
        prm.opt.videoCount = 0

        self.account.current_call = call
        call.makeCall(destination, prm)

    def hangup(self):
        call = self.account.current_call
        if call is None or call.disconnected:
            return

        try:
            call.hangup(pj.CallOpParam())
        except pj.Error as error:
            if not call.disconnected:
                print(f"Could not hang up call: {error}")

    def close(self):
        print("Cleaning up sip manager")
        try:
            call = self.account.current_call

            if call is not None and not call.disconnected:
                self.hangup()

                for _ in range(30):
                    if call.disconnected:
                        break
                    time.sleep(0.1)
        finally:
            self.account.stop_ringtone()
            self.account.current_call = None
            self.ep.libDestroy()
