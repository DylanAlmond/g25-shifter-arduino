import time
import logging

try:
  import serial
except Exception:
  serial = None

from input_state import state, lock, running

log = logging.getLogger("g25-driver")
import threading

# Internal state for runtime port switching
_port_lock = threading.Lock()
_desired_port = None
_current_port = None
_ser = None
_baud = None
_timeout = None


def switch_port(new_port: str):
  """Request switching the serial connection to `new_port`.

  This is non-blocking; the serial manager thread will attempt to reopen
  the requested port and apply the change.
  """
  global _desired_port
  with _port_lock:
    _desired_port = new_port
  log.info(f"Requested serial port switch to {new_port}")


def current_port():
  with _port_lock:
    return _current_port


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

  # initialize desired/current port and params
  global _ser, _desired_port, _current_port, _baud, _timeout
  with _port_lock:
    _desired_port = port
  _baud = baud
  _timeout = timeout

  # Manager loop: attempt to open the requested port and read continuously.
  while running:
    with _port_lock:
      desired = _desired_port

    # If we don't have an open Serial object, try to open the desired port
    if _ser is None:
      if not desired:
        time.sleep(0.5)
        continue
      try:
        _ser = serial.Serial(desired, _baud, timeout=_timeout)
        with _port_lock:
          _current_port = desired
          _desired_port = None
        log.info(f"Serial opened {_current_port}@{_baud}")
      except Exception as e:
        log.error(f"Serial open failed: {e}")
        time.sleep(1.0)
        continue

    try:
      # read a line (honors timeout)
      line = _ser.readline().decode(errors="ignore").strip()

      # check for a pending port switch even when no data arrived
      with _port_lock:
        desired = _desired_port

      if not line:
        if desired and desired != _current_port:
          try:
            _ser.close()
          except Exception:
            pass
          _ser = None
          with _port_lock:
            _current_port = None
          log.info(f"Switching serial port to {desired}")
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
      try:
        if _ser:
          _ser.close()
      except Exception:
        pass
      _ser = None
      with _port_lock:
        _current_port = None
      time.sleep(0.1)

  # cleanup
  try:
    if _ser:
      _ser.close()
  except Exception:
    pass
