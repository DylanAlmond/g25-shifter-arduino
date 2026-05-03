import logging
import mapper

try:
  import keyboard
except ImportError:
  keyboard = None

log = logging.getLogger("g25-driver")

last_gear = None
last_bits = {i: False for i in range(16)}


def apply_gear(gear: str, conf: dict):
  global last_gear

  if gear == last_gear:
    return

  for k in ["1", "2", "3", "4", "5", "6", "r"]:
    if keyboard:
      try:
        keyboard.release(k)
      except Exception as e:
        log.debug("keyboard.release(%s) failed: %s", k, e)

  key = conf.get("mappings", {}).get("gear", {}).get(gear, "")

  if key and keyboard:
    try:
      keyboard.press(key)
      log.info(f"GEAR {gear} -> {key}")
    except Exception as e:
      log.debug("keyboard.press(%s) failed: %s", key, e)

  last_gear = gear


def handle_buttons(buttons: int, conf: dict):
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
