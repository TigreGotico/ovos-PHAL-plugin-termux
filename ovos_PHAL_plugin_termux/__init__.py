from ovos_plugin_manager.phal import PHALPlugin
from ovos_utils.log import LOG
from ovos_bus_client import Message
from ovos_bus_client.session import SessionManager
from ovos_utils.system import find_executable, is_process_running
from ovos_plugin_manager.phal import find_phal_plugins

import subprocess
import json


class TermuxValidator:
    @staticmethod
    def validate(config=None):
        return True


class TermuxVolumeControlPlugin(PHALPlugin):
    validator = TermuxValidator

    def __init__(self, bus=None, config=None):
        super().__init__(bus=bus, name="ovos-PHAL-plugin-termux", config=config)
        self.termux = TermuxControl(stream=self.config.get("stream", "music"))
        self.bus.on("mycroft.volume.get", self.handle_volume_request)
        self.bus.on("mycroft.volume.set", self.handle_volume_change)
        self.bus.on("mycroft.volume.increase", self.handle_volume_increase)
        self.bus.on("mycroft.volume.decrease", self.handle_volume_decrease)
        self.bus.on("mycroft.volume.mute", self.handle_mute_request)
        self.bus.on("mycroft.volume.unmute", self.handle_unmute_request)
        self.bus.on("mycroft.volume.mute.toggle", self.handle_mute_toggle_request)
        self.bus.on("recognizer_loop:record_begin", self.handle_record_start)
        self.bus.on("recognizer_loop:record_end", self.handle_record_end)
        self.bus.on("recognizer_loop:sleep", self.handle_sleep)
        self.bus.on("recognizer_loop:speech.recognition.unknown", self.handle_error)
        self.bus.on("complete_intent_failure", self.handle_error)

    def handle_record_start(self):
        if self.config.get("vibrate_on_record_start"):
            subprocess.call("termux-vibrate")

    def handle_record_end(self):
        if self.config.get("vibrate_on_record_end"):
            subprocess.call("termux-vibrate")

    def handle_sleep(self):
        if self.config.get("vibrate_on_sleep"):
            subprocess.call("termux-vibrate")

    def handle_error(self):
        if self.config.get("vibrate_on_error", True):
            subprocess.call("termux-vibrate")

    def get_volume(self):
        return self.termux.get_volume_percent()

    def set_volume(self, percent=None, play_sound=True):
        volume = int(percent)
        volume = min(100, volume)
        volume = max(0, volume)
        if play_sound:
            self.bus.emit(Message("mycroft.audio.play_sound", {"uri": "snd/blop-mark-diangelo.wav"}))
        self.termux.set_volume_percent(volume)
        # report change
        self.handle_volume_request(Message("mycroft.volume.get"))

    def increase_volume(self, volume_change=None, play_sound=True):
        if not volume_change:
            volume_change = 15
        if play_sound:
            self.bus.emit(Message("mycroft.audio.play_sound", {"uri": "snd/blop-mark-diangelo.wav"}))
        self.termux.increase_volume(volume_change)
        # report change
        self.handle_volume_request(Message("mycroft.volume.get"))

    def decrease_volume(self, volume_change=None, play_sound=True):
        if not volume_change:
            volume_change = -15
        if volume_change > 0:
            volume_change = 0 - volume_change
        if play_sound:
            self.bus.emit(Message("mycroft.audio.play_sound", {"uri": "snd/blop-mark-diangelo.wav"}))
        self.termux.increase_volume(volume_change)
        # report change
        self.handle_volume_request(Message("mycroft.volume.get"))

    def handle_mute_request(self, message):
        if not self.validate_message_context(message):
            return

        self.log.info("User muted audio.")
        self.termux.mute()
        # report change
        self.handle_volume_request(Message("mycroft.volume.get"))

    def handle_unmute_request(self, message):
        if not self.validate_message_context(message):
            return

        self.log.info("User unmuted audio.")
        self.termux.unmute()
        # report change
        self.handle_volume_request(Message("mycroft.volume.get"))

    def handle_mute_toggle_request(self, message):
        if not self.validate_message_context(message):
            return

        self.termux.toggle_mute()
        muted = self.termux.is_muted()
        self.log.info(f"User toggled mute. Result: {'muted' if muted else 'unmuted'}")
        # report change
        self.handle_volume_request(Message("mycroft.volume.get"))

    def handle_volume_request(self, message):
        if not self.validate_message_context(message):
            return

        percent = self.get_volume() / 100
        self.bus.emit(message.response({"percent": percent,
                                        "muted": self.termux.is_muted()}))

    def handle_volume_change(self, message):
        if not self.validate_message_context(message):
            return

        percent = message.data["percent"] * 100
        play_sound = message.data.get("play_sound", True)
        assert isinstance(play_sound, bool)
        self.set_volume(percent, play_sound=play_sound)

    def handle_volume_increase(self, message):
        if not self.validate_message_context(message):
            return

        percent = message.data.get("percent", .10) * 100
        play_sound = message.data.get("play_sound", True)
        assert isinstance(play_sound, bool)
        self.increase_volume(percent, play_sound)

    def handle_volume_decrease(self, message):
        if not self.validate_message_context(message):
            return

        percent = message.data.get("percent", -.10) * 100
        play_sound = message.data.get("play_sound", True)
        assert isinstance(play_sound, bool)
        self.decrease_volume(percent, play_sound)

    def validate_message_context(self, message):
        sid = SessionManager.get(message).session_id
        LOG.debug(f"Request session: {sid}  |  Native Session: {self.bus.session_id}")
        return sid == self.bus.session_id

    def shutdown(self):
        self.bus.remove("mycroft.volume.get", self.handle_volume_request)
        self.bus.remove("mycroft.volume.set", self.handle_volume_change)
        self.bus.remove("mycroft.volume.increase", self.handle_volume_increase)
        self.bus.remove("mycroft.volume.decrease", self.handle_volume_decrease)
        self.bus.remove("mycroft.volume.mute", self.handle_mute_request)
        self.bus.remove("mycroft.volume.unmute", self.handle_unmute_request)
        self.bus.remove("mycroft.volume.mute.toggle", self.handle_mute_toggle_request)
        super().shutdown()


class TermuxControl:

    def __init__(self, stream="music"):
        self.stream = stream
        self._volume = 0
        self.max_vol = self.get_streams()[stream]["max_volume"]
        self.muted = False
        self.get_volume() # initial sync

    @staticmethod
    def get_streams():
        out = subprocess.check_output("termux-volume").decode("utf-8")
        streams = {e["stream"]: {"volume": e["volume"], "max_volume": e["max_volume"]}
                   for e in json.loads(out)}
        LOG.debug(f"volume info: {streams}")
        return streams

    def is_muted(self):
        return self.muted

    def increase_volume(self, percent):
        volume = self.get_volume_percent()
        volume += percent
        self.set_volume_percent(min(volume, 100))

    def decrease_volume(self, percent):
        volume = self.get_volume_percent()
        volume -= percent
        self.set_volume_percent(max(volume, 0))

    def get_volume(self):
        self._volume = self.get_streams()[self.stream]["volume"]
        return self._volume

    def set_volume(self, volume):
        volume = int(min(volume, self.max_vol))
        self._volume = volume
        self.muted = volume == 0
        subprocess.call(["termux-volume", self.stream, str(volume)])

    def get_volume_percent(self):
        vol = self.get_volume()
        return vol * 100 / self.max_vol

    def set_volume_percent(self, percent):
        n = percent * self.max_vol / 100  # convert % to range
        self.set_volume(n)

    def mute(self):
        self._volume = self.get_volume() or self._volume  # save for restoring
        return self.set_volume(0)

    def unmute(self):
        if self.muted:
            self.set_volume(self._volume or 2)
            self.muted = False

    def toggle_mute(self):
        if self.muted:
            self.unmute()
        else:
            self.mute()
