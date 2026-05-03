import time
import logging

try:
  import serial
except Exception:
  serial = None

from input_state import state, lock, running

log = logging.getLogger("g25-driver")


def parse_line(line: str):
  parts = line.split(",")

  if len(parts) == 5:
    try:
      gear = parts[1].strip()
      x = int(parts[2].strip())
      y = int(parts[3].strip())
      buttons_s = parts[4].strip()

      if len(buttons_s) != 16:
        return None

      buttons = int(buttons_s, 2)
      return gear, x, y, buttons
    except Exception:
      return None

  elif len(parts) == 4:
    try:
      x = int(parts[1].strip())
      y = int(parts[2].strip())
      buttons_s = parts[3].strip()

      if len(buttons_s) != 16:
        return None

      buttons = int(buttons_s, 2)
      return "", x, y, buttons
    except Exception:
      return None

  return None


def serial_thread(port: str, baud: int, timeout: float):
  if serial is None:
    log.error("pyserial not installed")
    return

  try:
    ser = serial.Serial(port, baud, timeout=timeout)
  except Exception as e:
    log.error(f"Serial open failed: {e}")
    return

  log.info(f"Serial opened {port}@{baud}")

  while running:
    try:
      line = ser.readline().decode(errors="ignore").strip()
      if not line:
        continue

      parsed = parse_line(line)
      if not parsed:
        continue

      gear, x, y, buttons = parsed

      with lock:
        prev = state["buttons"]
        state["gear"] = gear
        state["x"] = x
        state["y"] = y
        state["buttons"] = buttons
        state["raw"] = line

        rising = buttons & (~prev)
        if rising:
          state["last_pressed_bits"] = rising
          state["last_pressed_time"] = time.time()

    except Exception as e:
      log.error(f"serial error: {e}")
      time.sleep(0.1)
