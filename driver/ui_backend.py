"""
UI backend helpers for the GUI.

Small wrappers around config I/O, COM-port listing, and simple `input_state`
snapshot helpers used by the GUI layer to keep UI concerns separated from
business logic.
"""
import time
import logging
from typing import List, Tuple, Optional

import config as cfg

log = logging.getLogger("g25-driver")


def save_config(conf: dict, path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
  """
  Save config using `config.save_config` and return (ok, error_message).

  The wrapper captures exceptions and logs them, returning a human-friendly
  error string on failure.
  """
  try:
    cfg.save_config(conf, path)
    return True, None
  except Exception as e:
    log.exception("Failed to save config")
    return False, str(e)


def list_com_ports() -> List[str]:
  """Return a list of available serial port device names.

  Handles missing `pyserial` gracefully and logs failures.
  """
  try:
    import serial.tools.list_ports as list_ports
  except Exception:
    return []

  try:
    return [p.device for p in list_ports.comports()]
  except Exception as e:
    log.debug("Failed to list COM ports: %s", e)
    return []


def get_snapshot(state: dict, lock) -> dict:
  """Return a shallow copy of the relevant state fields under lock."""
  with lock:
    return {
        "gear_arduino": state.get("gear_arduino"),
        "gear_computed": state.get("gear_computed"),
        "x": state.get("x", 0),
        "y": state.get("y", 0),
        "buttons": state.get("buttons", 0),
        "raw": state.get("raw", ""),
        "last_pressed_bits": state.get("last_pressed_bits", 0),
        "last_pressed_time": state.get("last_pressed_time", 0.0),
    }


def active_button_list(state: dict, lock, max_age: float = 3.0) -> List[int]:
  """
  Return a list of currently-active button indices.

  Prefers recently-recorded rising-edge bits (within `max_age` seconds),
  otherwise falls back to currently-pressed bits.
  """
  snap = get_snapshot(state, lock)
  last_bits = snap.get("last_pressed_bits", 0)
  last_time = snap.get("last_pressed_time", 0.0)
  bits = snap.get("buttons", 0)

  if last_bits and (time.time() - last_time) < max_age:
    return [i for i in range(16) if ((last_bits >> i) & 1)]
  if bits:
    return [i for i in range(16) if ((bits >> i) & 1)]
  return []
