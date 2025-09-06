# ovos-PHAL-plugin - termux volume control

controls system volume with termux

for voice control you need the companion [ovos-skill-volume](https://github.com/OpenVoiceOS/ovos-skill-volume)

```python
self.bus.on("mycroft.volume.get", self.handle_volume_request)
self.bus.on("mycroft.volume.set", self.handle_volume_change)
self.bus.on("mycroft.volume.mute", self.handle_mute_request)
self.bus.on("mycroft.volume.unmute", self.handle_unmute_request)
```

---

## HiveMind Support

This plugin can be used both in OVOS and with [HiveMind](https://github.com/JarbasHiveMind) satellites.

Be sure to allow `"mycroft.volume.get.response"` in your hivemind for your satellite to be able to report volume

```bash
hivemind-core allow-msg "mycroft.volume.get.response"
```
