"""
Keyboard control helpers.

Maps computed gears and button bitfields to keyboard events using the
optional `keyboard` library. If `keyboard` is not installed, mapping logic
still runs but no key presses are emitted.
"""
import logging
import mapper

try:
  import keyboard
except ImportError:
  keyboard = None

import time

SEQ_COOLDOWN = 0.15  # seconds between sequential shifts
_last_seq_time = 0
_last_seq_dir = None

log = logging.getLogger("g25-driver")

last_gear = None
last_bits = {i: False for i in range(16)}


def apply_gear(gear: str, conf: dict):
  """
  Emit keyboard events for a gear transition.

  H-pattern gears are held.
  Sequential gears ("up"/"down") are tapped once per movement.
  """
  global last_gear, _last_seq_time, _last_seq_dir

  gear_map = conf.get("mappings", {}).get("gear", {})

  H_GEARS = ["1", "2", "3", "4", "5", "6", "r"]

  # Reset sequential state when leaving sequential mode
  if gear not in ["up", "down"]:
    _last_seq_dir = None

  # Sequential (momentary tap)
  if gear in ["up", "down"]:
    now = time.time()

    # trigger only on change (prevents repeat spam)
    if gear == _last_seq_dir:
      return

    # safety cooldown
    if (now - _last_seq_time) < SEQ_COOLDOWN:
      return

    key = gear_map.get(gear, "")

    if key and keyboard:
      try:
        # reliable tap (some systems ignore press_and_release)
        keyboard.press(key)
        time.sleep(0.01)
        keyboard.release(key)

        log.info(f"SEQUENTIAL {gear} -> {key}")
      except Exception as e:
        log.debug("SEQUENTIAL failed (%s): %s", key, e)

    _last_seq_dir = gear
    _last_seq_time = now
    last_gear = None
    return

  if gear == last_gear:
    return

  # Release previous H-pattern gear
  if last_gear in H_GEARS:
    old_key = gear_map.get(last_gear, "")
    if old_key and keyboard:
      try:
        keyboard.release(old_key)
      except Exception as e:
        log.debug("keyboard.release(%s) failed: %s", old_key, e)

  # H-pattern hold behavior
  key = gear_map.get(gear, "")

  if key and keyboard:
    try:
      keyboard.press(key)
      log.info(f"GEAR {gear} -> {key}")
    except Exception as e:
      log.debug("keyboard.press(%s) failed: %s", key, e)

  last_gear = gear


def handle_buttons(buttons: int, conf: dict):
  """
  Handle button bitfield transitions and emit press/release events.

  `buttons` is a 16-bit integer where each bit corresponds to one button.
  `conf` provides `mappings.buttons` mapping indices to key names.
  """
  global last_bits

  mapping = conf.get("mappings", {}).get("buttons", {})
  bits = mapper.map_buttons_to_keys(buttons, mapping)

  for i in range(16):
    item = bits.get(i, {"active": False, "key": ""})

    active = item["active"]
    key = item["key"]
    prev = last_bits[i]

    if active and not prev:
      if keyboard and key:
        try:
          keyboard.press(key)
        except Exception as e:
          log.debug("keyboard.press(%s) failed: %s", key, e)

    elif not active and prev:
      if keyboard and key:
        try:
          keyboard.release(key)
        except Exception as e:
          log.debug("keyboard.release(%s) failed: %s", key, e)

    last_bits[i] = active
