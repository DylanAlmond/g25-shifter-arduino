import json
import os
import tempfile
import copy
from typing import Optional

DEFAULT_CONFIG = {
  "serial": {
    "port": "COM5",
    "baud": 250000,
    "timeout": 1.0
  },
  "calibration": {
    "offset_x": 0,
    "offset_y": 0,
    "deadzone": 80
  },
  "controls": {
    "update_hz": 120,
    "gui": True,
    "config_reload_secs": 1.0
  },
  "mappings": {
    "gear": {
      "1": "1",
      "2": "2",
      "3": "3",
      "4": "4",
      "5": "5",
      "6": "6",
      "R": "r",
      "N": ""
    },
    "buttons": {
      "0": "up",
      "1": "down",
      "2": "left",
      "3": "right",
      "4": "s",
      "5": "a",
      "6": "d",
      "7": "w",
      "8": "1",
      "9": "4",
      "10": "2",
      "11": "3",
      "12": "",
      "13": "",
      "14": "",
      "15": ""
    }
  },
  "gear_positions": {
    "1": {
      "x": -224,
      "y": 355,
      "buttons": 0
    },
    "2": {
      "x": -249,
      "y": -437,
      "buttons": 0
    },
    "3": {
      "x": -53,
      "y": 370,
      "buttons": 0
    },
    "4": {
      "x": -39,
      "y": -443,
      "buttons": 0
    },
    "5": {
      "x": 145,
      "y": 371,
      "buttons": 0
    },
    "6": {
      "x": 149,
      "y": -437,
      "buttons": 0
    },
    "R": {
      "x": 187,
      "y": -440,
      "buttons": 16384
    }
  }
}

CONFIG_PATH_DEFAULT = os.path.join(os.path.dirname(__file__), "config.json")


def _merge_defaults(conf: dict) -> dict:
  merged = copy.deepcopy(DEFAULT_CONFIG)

  def merge(a, b):
    for k, v in b.items():
      if k in a and isinstance(a[k], dict) and isinstance(v, dict):
        merge(a[k], v)
      else:
        a[k] = v

  merge(merged, conf or {})
  return merged


def load_config(path: Optional[str] = None) -> dict:
  if path is None:
    path = CONFIG_PATH_DEFAULT

  if os.path.exists(path):
    try:
      with open(path, "r", encoding="utf-8") as f:
        conf = json.load(f)
      return _merge_defaults(conf)
    except Exception:
      conf = _merge_defaults({})
      save_config(conf, path)
      return conf

  conf = _merge_defaults({})
  save_config(conf, path)
  return conf


def save_config(conf: dict, path: Optional[str] = None) -> None:
  if path is None:
    path = CONFIG_PATH_DEFAULT

  d = os.path.dirname(path)
  if d and not os.path.exists(d):
    os.makedirs(d, exist_ok=True)

  fd, tmp = tempfile.mkstemp(dir=d or ".", prefix=".config", text=True)
  try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
      json.dump(conf, f, indent=2)
    os.replace(tmp, path)
  finally:
    if os.path.exists(tmp):
      try:
        os.remove(tmp)
      except Exception:
        pass
