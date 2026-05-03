import argparse
import threading
import time

import gui
import config as cfg

from logging_setup import setup_logging
from serial_reader import serial_thread
from loop import main_loop
import input_state

log = setup_logging()


def main():
  p = argparse.ArgumentParser()
  p.add_argument("--gui", action="store_true")
  p.add_argument("--config", "-c", default=None)
  p.add_argument("--port", default=None)
  p.add_argument("--baud", type=int, default=None)
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

  if args.gui:
    main_t = threading.Thread(
        target=main_loop,
        args=(args.config,),
        daemon=True
    )
    main_t.start()

    gui.gui_loop(input_state.state, input_state.lock, args.config)

    # GUI exited — signal shutdown and join threads
    input_state.running = False
    log.info("shutdown")
    try:
      main_t.join(timeout=2.0)
    except RuntimeError as e:
      log.debug("main thread join failed: %s", e)
    try:
      t.join(timeout=2.0)
    except RuntimeError as e:
      log.debug("serial thread join failed: %s", e)
  else:
    try:
      main_loop(args.config)
    except KeyboardInterrupt:
      input_state.running = False
      log.info("shutdown")
      try:
        t.join(timeout=2.0)
      except RuntimeError as e:
        log.debug("serial thread join failed: %s", e)


if __name__ == "__main__":
  main()
