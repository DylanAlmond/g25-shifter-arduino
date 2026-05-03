import time
import logging

import config as cfg
import mapper

import input_state
from controls import apply_gear, handle_buttons

log = logging.getLogger("g25-driver")


def main_loop(config_path=None):
  conf = cfg.load_config(config_path)

  update_hz = conf.get("controls", {}).get("update_hz", 120)
  target_dt = 1.0 / float(update_hz)

  last_reload = time.time()

  while input_state.running:
    start = time.perf_counter()

    now = time.time()
    if now - last_reload > conf.get("controls", {}).get("config_reload_secs", 1.0):
      conf = cfg.load_config(config_path)
      update_hz = conf.get("controls", {}).get("update_hz", update_hz)
      target_dt = 1.0 / float(update_hz)
      last_reload = now

    with input_state.lock:
      x = input_state.state["x"]
      y = input_state.state["y"]
      buttons = input_state.state["buttons"]

    offset_x = conf["calibration"]["offset_x"]
    offset_y = conf["calibration"]["offset_y"]
    deadzone = conf["calibration"]["deadzone"]

    gear = mapper.compute_gear(
        x, y, buttons,
        offset_x, offset_y,
        deadzone,
        conf.get("gear_positions", {})
    )

    with input_state.lock:
      input_state.state["gear_computed"] = gear

    apply_gear(gear, conf)
    handle_buttons(buttons, conf)

    elapsed = time.perf_counter() - start
    sleep = target_dt - elapsed
    if sleep > 0:
      time.sleep(sleep)
