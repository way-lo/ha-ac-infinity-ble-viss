# Changelog

All notable changes to this fork, relative to the upstream
[`Viss/ha-ac-infinity-ble`](https://github.com/Viss/ha-ac-infinity-ble) base, are
documented here.

## [2.1.1]

### Fixed

- Auto Mode High/Low Temperature now read and write the controller's
  Fahrenheit byte directly, instead of deriving Fahrenheit from a
  round-tripped whole-degree-Celsius value. The protocol carries both an F
  and a C byte per threshold; the F byte is what the controller itself
  treats as authoritative (matching whatever display unit it's configured
  for), so setting e.g. 76°F no longer silently reads back as 75°F after the
  next poll. The Celsius byte is still sent on writes (derived from the
  Fahrenheit value) since the packet format requires it, but nothing reads
  it back, so its rounding no longer matters.
- Home Assistant's built-in Celsius/Fahrenheit conversion for `number`
  entities with `device_class: temperature` still works correctly on top of
  this for anyone whose Home Assistant unit system is set to Celsius — HA
  converts their input to Fahrenheit before it reaches this integration, so
  the fix benefits both unit systems, not just Fahrenheit users. (Celsius
  users will see ~0.56°C-sized steps rather than clean whole-Celsius
  increments, since the underlying native step is fixed at 1°F.)

## [2.1.0]

### Added

- **Domain renamed** from `ac_infinity` to `ac_infinity_viss`, so this fork can be
  installed alongside other AC Infinity integrations (e.g. `ac_infinity_airtap`)
  without colliding.
- **Min Speed / Max Speed** number entities — the stored auto-mode floor/ceiling
  speed presets, previously readable but not writable.
- **Auto Mode High Temperature** / **Auto Mode Low Temperature** number
  entities — natively Fahrenheit at the entity boundary (whole-degree steps),
  converting to/from the single whole-degree-Celsius byte the controller
  actually stores.
- **Auto Mode High/Low Temperature Trigger** switches — enable or disable each
  temperature-based auto-mode trigger independently.
- **Auto / On preset modes** on the fan entity, so the fan can be commanded
  into Auto or On via `fan.set_preset_mode`, voice assistants, automations, or
  a custom dashboard card — not just plain on/off/speed.

### Fixed

- Crash (`IndexError`) during setup when a model-response parameter was
  present in the reply but zero-length; now treated as "not supported on this
  device" instead of read as data.
- Auto-mode config (triggers, thresholds) is now parsed correctly as a single
  7-byte blob under parameter `0x13` — an earlier attempt incorrectly assumed
  each field lived at its own sequential parameter ID.
- Humidity sensor is no longer created for Airtap-family devices (type 6),
  which have no humidity hardware; other device types are unaffected.
- Fan entity's `is_on` no longer falls back to Home Assistant's default
  "any preset_mode counts as on" behavior, which previously made the fan show
  as `on` at `0%` any time it was sitting in Auto mode, even while genuinely
  idle. `is_on` now strictly reflects whether the fan is actually spinning.

### Known device behavior (not a bug)

- Writing to the auto-mode config — via either trigger switch or either
  temperature number — causes the controller to switch its own mode to Auto,
  even if it was previously Off. This is not requested by any command this
  integration sends; it appears to be a firmware-level side effect of writing
  to that parameter block, consistent with the OEM app only exposing these
  settings from within Auto mode in the first place.

