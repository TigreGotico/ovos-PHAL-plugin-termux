# ovos-PHAL-plugin-termux

A PHAL plugin that controls system volume, vibration, and the camera on Termux. It runs as part of the [Platform/Hardware Abstraction Layer](https://github.com/OpenVoiceOS/ovos-PHAL) in OpenVoiceOS.

The plugin listens for OVOS bus messages and translates them into `termux-api` calls, so volume and camera commands work on an Android device running Termux.

For voice control of volume, use the companion [ovos-skill-volume](https://github.com/OpenVoiceOS/ovos-skill-volume).

## Install

```bash
pip install ovos-PHAL-plugin-termux
```

## Usage

OVOS loads this plugin as a PHAL entry point. It handles these bus messages:

```python
self.bus.on("mycroft.volume.get", self.handle_volume_request)
self.bus.on("mycroft.volume.set", self.handle_volume_change)
self.bus.on("mycroft.volume.mute", self.handle_mute_request)
self.bus.on("mycroft.volume.unmute", self.handle_unmute_request)
```

It also handles camera messages (`ovos.phal.camera.ping`, `ovos.phal.camera.get`) and can vibrate the device on record start, record end, sleep, and error events.

### Config

```json
  "PHAL": {
    "ovos-PHAL-plugin-termux": {
      "stream": "music",
      "camera_id": 0,
      "vibrate_on_record_start": false,
      "vibrate_on_record_end": false,
      "vibrate_on_sleep": false,
      "vibrate_on_error": true
    }
  }
```

## HiveMind support

This plugin works with OVOS and with [HiveMind](https://github.com/JarbasHiveMind) satellites.

Allow `mycroft.volume.get.response` in your HiveMind setup, so your satellite can report volume:

```bash
hivemind-core allow-msg "mycroft.volume.get.response"
```

## Related projects

- [ovos-PHAL](https://github.com/OpenVoiceOS/ovos-PHAL) - the plugin host this plugin registers with
- [ovos-skill-volume](https://github.com/OpenVoiceOS/ovos-skill-volume) - the skill that drives volume control through voice

## License

[Apache License 2.0](LICENSE)
