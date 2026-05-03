import argparse
import threading
import time
import sys

import gui
import config as cfg

from logging_setup import setup_logging
from serial_reader import serial_thread
from loop import main_loop
from calibration import calibrate_cli
from input_state import state, lock

log = setup_logging()


def main():
  p = argparse.ArgumentParser()
  p.add_argument("--gui", action="store_true")
  p.add_argument("--config", "-c", default=None)
  p.add_argument("--port", default=None)
  p.add_argument("--baud", type=int, default=None)
  p.add_argument("--calibrate", action="store_true")
  args = p.parse_args()

  conf = cfg.load_config(args.config)

  if args.port:
    conf.setdefault("serial", {})["port"] = args.port
  if args.baud:
    conf.setdefault("serial", {})["baud"] = args.baud

  port = conf["serial"]["port"]
  baud = conf["serial"]["baud"]
  timeout = conf["serial"].get("timeout", 1.0)

  t = threading.Thread(
      target=serial_thread,
      args=(port, baud, timeout),
      daemon=True
  )
  t.start()

  time.sleep(0.1)

  if args.calibrate:
    calibrate_cli(args.config)
    sys.exit(0)

  if args.gui:
    threading.Thread(
        target=main_loop,
        args=(args.config,),
        daemon=True
    ).start()

    gui.gui_loop(state, lock, args.config)
  else:
    try:
      main_loop(args.config)
    except KeyboardInterrupt:
      global running
      running = False
      log.info("shutdown")


if __name__ == "__main__":
  main()
