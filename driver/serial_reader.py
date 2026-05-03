"""Serial port manager and reader for the G25 shifter.

This module runs a background `serial_thread` that opens a serial device,
reads lines from the controller, parses them via `parse_line`, and updates
the shared `input_state` structure. Use `switch_port` to request a runtime
port change and `current_port` to query the active device name.
"""
import threading
import time
import logging

try:
  import serial
except ImportError:
  serial = None

import input_state

log = logging.getLogger("g25-driver")

# Internal state for runtime port switching
_port_lock = threading.Lock()
_desired_port = None
_current_port = None
_ser = None
_baud = None
_timeout = None


def switch_port(new_port: str):
  """
  Request switching the serial connection to `new_port`.

  This is non-blocking; the serial manager thread will attempt to reopen
  the requested port and apply the change.
  """
  global _desired_port

  with _port_lock:
    _desired_port = new_port
  log.info(f"Requested serial port switch to {new_port}")


def parse_line(line: str):
  """
  Parse a single line from the serial device.

  Supported formats:
  - 5-part: <prefix>,<gear>,<x>,<y>,<16bit-button-binary>
    -> returns (gear, x, y, buttons)
  - 4-part: <prefix>,<x>,<y>,<16bit-button-binary>
    -> returns ("", x, y, buttons)

  Returns None on parse errors or unexpected formats.
  """
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
    except (ValueError, TypeError):
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
    except (ValueError, TypeError):
      return None

  return None


def serial_thread(port: str, baud: int, timeout: float):
  """
  Background thread that opens and reads from the serial device.

  Opens `port` at `baud` using `timeout` and continuously reads lines.
  When a port switch is requested via `switch_port`, the thread will close
  and reopen the connection. The thread exits when `input_state.running`
  becomes False.
  """
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
  while input_state.running:
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
      except (serial.SerialException, OSError) as e:
        log.error(f"Serial open failed: {e}")
        time.sleep(1.0)
        continue
      except Exception as e:
        log.exception("Unexpected error opening serial port: %s", e)
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
          except OSError as e:
            log.debug("Error closing serial before port switch: %s", e)
          _ser = None
          with _port_lock:
            _current_port = None
          log.info(f"Switching serial port to {desired}")
        continue

      parsed = parse_line(line)
      if not parsed:
        continue

      gear, x, y, buttons = parsed

      with input_state.lock:
        prev = input_state.state["buttons"]
        input_state.state["gear_arduino"] = gear
        input_state.state["x"] = x
        input_state.state["y"] = y
        input_state.state["buttons"] = buttons
        input_state.state["raw"] = line

        rising = buttons & (~prev)
        if rising:
          input_state.state["last_pressed_bits"] = rising
          input_state.state["last_pressed_time"] = time.time()

    except serial.SerialException as e:
      log.error(f"serial error: {e}")
      try:
        if _ser:
          _ser.close()
      except OSError as e2:
        log.debug("Error closing serial: %s", e2)
      _ser = None
      with _port_lock:
        _current_port = None
      time.sleep(0.1)
    except Exception as e:
      log.exception("Unexpected serial processing error: %s", e)
      try:
        if _ser:
          _ser.close()
      except OSError as e2:
        log.debug("Error closing serial: %s", e2)
      _ser = None
      with _port_lock:
        _current_port = None
      time.sleep(0.1)

  # cleanup
  try:
    if _ser:
      _ser.close()
  except OSError as e:
    log.debug("Error closing serial during cleanup: %s", e)
