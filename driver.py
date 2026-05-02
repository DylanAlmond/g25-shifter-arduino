import serial
import threading
import time
import sys
import keyboard
import logging

# ---------------- CONFIG ----------------
PORT = "COM3"
BAUD = 250000
UPDATE_HZ = 120

GUI_MODE = "--gui" in sys.argv

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("g25-driver")

# ---------------- SERIAL ----------------
try:
  ser = serial.Serial(PORT, BAUD, timeout=1)
  log.info(f"Serial opened on {PORT} @ {BAUD}")
except Exception as e:
  log.error(f"Failed to open serial: {e}")
  sys.exit(1)

# ---------------- STATE ----------------
lock = threading.Lock()

state = {
    "gear": "N",
    "buttons": 0,
    "raw": ""
}

running = True

# ---------------- PARSER ----------------


def bits_to_int(bits: str) -> int:
  try:
    return int(bits, 2)
  except Exception as e:
    log.warning(f"bit parse failed: {bits} | {e}")
    return 0


def parse_line(line: str):
  parts = line.split(',')

  if len(parts) != 5:
    log.debug(f"bad packet format: {line}")
    return None, None

  gear = parts[1].strip()
  buttons = parts[4].strip()

  if len(buttons) != 16:
    log.debug(f"bad button length: {buttons}")
    return None, None

  return gear, bits_to_int(buttons)

# ---------------- SERIAL THREAD ----------------


def serial_thread():
  log.info("Serial thread started")

  while running:
    try:
      line = ser.readline().decode(errors="ignore").strip()
      if not line:
        continue

      gear, buttons = parse_line(line)

      if gear is None:
        continue

      with lock:
        state["gear"] = gear
        state["buttons"] = buttons
        state["raw"] = line

      log.debug(f"RX | gear={gear} buttons={bin(buttons)} raw={line}")

    except Exception as e:
      log.error(f"serial error: {e}")

# ---------------- GEAR ----------------


last_gear = "N"


def apply_gear(gear):
  global last_gear

  if gear == last_gear:
    return

  for k in ["1", "2", "3", "4", "5", "6", "r"]:
    keyboard.release(k)

  mapping = {
      "1": "1",
      "2": "2",
      "3": "3",
      "4": "4",
      "5": "5",
      "6": "6",
      "R": "r"
  }

  if gear in mapping:
    keyboard.press(mapping[gear])
    log.info(f"GEAR → {gear}")
  else:
    log.info("GEAR → NEUTRAL")

  last_gear = gear

# ---------------- BUTTON HANDLER (UPDATED) ----------------


last_dpad = {
    "up": False,
    "down": False,
    "left": False,
    "right": False
}


def handle_buttons(buttons: int):
  global last_dpad

  # D-PAD mapping (bit 0–3)
  up = bool((buttons >> 0) & 1)
  down = bool((buttons >> 1) & 1)
  left = bool((buttons >> 2) & 1)
  right = bool((buttons >> 3) & 1)

  # UP
  if up and not last_dpad["up"]:
    keyboard.press("up")
    log.debug("DPAD UP press")
  elif not up and last_dpad["up"]:
    keyboard.release("up")
    log.debug("DPAD UP release")

  # DOWN
  if down and not last_dpad["down"]:
    keyboard.press("down")
    log.debug("DPAD DOWN press")
  elif not down and last_dpad["down"]:
    keyboard.release("down")
    log.debug("DPAD DOWN release")

  # LEFT
  if left and not last_dpad["left"]:
    keyboard.press("left")
    log.debug("DPAD LEFT press")
  elif not left and last_dpad["left"]:
    keyboard.release("left")
    log.debug("DPAD LEFT release")

  # RIGHT
  if right and not last_dpad["right"]:
    keyboard.press("right")
    log.debug("DPAD RIGHT press")
  elif not right and last_dpad["right"]:
    keyboard.release("right")
    log.debug("DPAD RIGHT release")

  last_dpad = {
      "up": up,
      "down": down,
      "left": left,
      "right": right
  }

  # optional debug
  if buttons:
    log.debug(f"buttons active: {bin(buttons)}")

# ---------------- MAIN LOOP ----------------


def main_loop():
  log.info("Main loop started")

  target_dt = 1.0 / UPDATE_HZ

  while True:
    start = time.perf_counter()

    with lock:
      gear = state["gear"]
      buttons = state["buttons"]

    apply_gear(gear)
    handle_buttons(buttons)

    elapsed = time.perf_counter() - start
    sleep_time = target_dt - elapsed

    if sleep_time > 0:
      time.sleep(sleep_time)

# ---------------- GUI ----------------


def gui_loop():
  import tkinter as tk

  root = tk.Tk()
  root.title("G25 Debug Driver")
  root.geometry("420x200")

  gear_var = tk.StringVar()
  btn_var = tk.StringVar()
  raw_var = tk.StringVar()

  tk.Label(root, textvariable=gear_var, font=("Arial", 24)).pack()
  tk.Label(root, textvariable=btn_var).pack()
  tk.Label(root, textvariable=raw_var, font=("Courier", 8)).pack()

  def update():
    with lock:
      gear_var.set(f"GEAR: {state['gear']}")
      btn_var.set(f"BTN: {bin(state['buttons'])}")
      raw_var.set(state["raw"])

    root.after(50, update)

  update()
  root.mainloop()

# ---------------- START ----------------


if __name__ == "__main__":
  threading.Thread(target=serial_thread, daemon=True).start()
  threading.Thread(target=main_loop, daemon=True).start()

  log.info("Driver started")

  if GUI_MODE:
    gui_loop()
  else:
    while True:
      time.sleep(1)
