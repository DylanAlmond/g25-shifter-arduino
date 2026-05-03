import time
import logging

import config as cfg
from input_state import state, lock

log = logging.getLogger("g25-driver")


def calibrate_cli(config_path=None, samples=50):
  conf = cfg.load_config(config_path)

  xs, ys = [], []

  for _ in range(samples):
    with lock:
      xs.append(state["x"])
      ys.append(state["y"])
    time.sleep(0.02)

  if not xs:
    return

  avg_x = sum(xs) / len(xs)
  avg_y = sum(ys) / len(ys)

  conf["calibration"]["offset_x"] = int(round(-avg_x))
  conf["calibration"]["offset_y"] = int(round(avg_y))

  cfg.save_config(conf, config_path)
