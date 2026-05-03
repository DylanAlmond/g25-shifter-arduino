"""
Tkinter GUI for calibration and mapping.

This module provides `gui_loop` which starts a simple Tk UI for visualizing
the shifter, calibrating offsets, and editing gear/button mappings via the
`MappingEditor` dialog.
"""
import tkinter as tk
from tkinter import messagebox
import time
import config as cfg
import logging
import ui_backend
from typing import Any, List
import os

log = logging.getLogger("g25-driver")

# keep references to Tk images so they are not garbage-collected
_image_refs: List[Any] = []

DEFAULT_BUTTON_POSITIONS = {
    # Black button
    "7": {"x": 240, "y": 80},
    "6": {"x": 270, "y": 105},
    "4": {"x": 240, "y": 130},
    "5": {"x": 210, "y": 105},

    # D-Pad
    "0": {"x": 240, "y": 170},
    "1": {"x": 240, "y": 210},
    "2": {"x": 210, "y": 188},
    "3": {"x": 270, "y": 188},

    # Red buttons
    "8": {"x": 180, "y": 245},
    "10": {"x": 220, "y": 245},
    "11": {"x": 260, "y": 245},
    "9": {"x": 300, "y": 245}
}

# UI layout constants
DEFAULT_RECT_SIZE = 14


class MappingEditor(tk.Toplevel):
  """
  Modal dialog to edit gear and button mappings.

  Presents fields for gear positions and button->key mappings and supports
  recording current stick positions and button presses as mapping hints.
  """

  def __init__(self, master, state, lock, config_path=None):
    super().__init__(master)
    self.title("Mapping Editor")
    self.geometry("620x460")
    self.config_path = config_path
    self.state = state
    self.lock = lock

    self.conf = cfg.load_config(config_path)

    gear_frame = tk.LabelFrame(
      self, text="Gear Mappings (press Record while stick is in position)")
    gear_frame.pack(fill="x", padx=6, pady=6)

    self.gear_entries = {}
    self.gear_pos_labels = {}
    row = 0
    for g in ["1", "2", "3", "4", "5", "6", "R", "up", "down"]:
      tk.Label(gear_frame, text=g).grid(row=row, column=0, sticky="w")
      e = tk.Entry(gear_frame, width=10)
      e.grid(row=row, column=1, sticky="w", padx=4, pady=2)
      e.insert(0, self.conf.get("mappings", {}).get("gear", {}).get(g, ""))
      self.gear_entries[g] = e

      lbl = tk.Label(gear_frame, text=self._pos_text_for(g))
      lbl.grid(row=row, column=2, sticky="w", padx=6)
      self.gear_pos_labels[g] = lbl

      # Exclude sequential gears from recording since they are not physical positions and would be confusing to record
      if g in ["up", "down"]:
        tk.Label(gear_frame, text="(seq)").grid(row=row, column=3, padx=6)
      else:
        tk.Button(
          gear_frame,
          text="Record",
          command=lambda g=g: self.record_gear(g)
        ).grid(row=row, column=3, padx=6)

      row += 1

    btn_frame = tk.LabelFrame(
      self, text="Button Bit Mappings (0..15) — use 'Record Button->Key'")
    btn_frame.pack(fill="both", expand=True, padx=6, pady=6)

    self.button_entries = {}
    for i in range(16):
      r = i // 4
      c = (i % 4) * 3
      tk.Label(btn_frame, text=str(i)).grid(row=r, column=c, sticky="w")
      e = tk.Entry(btn_frame, width=14)
      e.grid(row=r, column=c + 1, sticky="w", padx=2, pady=2)
      e.insert(0, self.conf.get("mappings", {}).get(
        "buttons", {}).get(str(i), ""))
      self.button_entries[i] = e

    rec_frame = tk.Frame(self)
    rec_frame.pack(fill="x", padx=6, pady=6)
    tk.Button(rec_frame, text="Record Button->Key",
              command=self.record_button_key).pack(side="left", padx=6)
    tk.Button(rec_frame, text="Save Mappings",
              command=self.save).pack(side="left", padx=6)
    tk.Button(rec_frame, text="Cancel", command=self.destroy).pack(
      side="right", padx=6)

  def save(self):
    # write gear map
    gm = {}
    for g, e in self.gear_entries.items():
      gm[g] = e.get().strip()

    bm = {}
    for i, e in self.button_entries.items():
      bm[str(i)] = e.get().strip()

    self.conf["mappings"]["gear"] = gm
    self.conf["mappings"]["buttons"] = bm
    ok, err = ui_backend.save_config(self.conf, self.config_path)
    if ok:
      messagebox.showinfo("Saved", "Mappings saved to config")
      self.destroy()
    else:
      log.exception("Failed to save mappings to config: %s", err)
      messagebox.showerror("Error", f"Failed to save config: {err}")

  def _pos_text_for(self, gear):
    gp = self.conf.get("gear_positions", {}) or {}
    if gear in gp:
      pos = gp[gear]
      btn = pos.get('buttons', 0)
      return f"pos: x={pos.get('x')} y={pos.get('y')} btn={bin(btn)}"
    return "pos: (not set)"

  def record_gear(self, gear):
    snap = ui_backend.get_snapshot(self.state, self.lock)
    x = snap.get("x", 0)
    y = snap.get("y", 0)
    bits = int(snap.get("buttons", 0))
    if "gear_positions" not in self.conf:
      self.conf["gear_positions"] = {}
    self.conf["gear_positions"][gear] = {
      "x": int(x), "y": int(y), "buttons": int(bits)}
    ok, err = ui_backend.save_config(self.conf, self.config_path)
    if ok:
      self.gear_pos_labels[gear].config(text=self._pos_text_for(gear))
      messagebox.showinfo(
        "Recorded", f"Recorded {gear} -> x={x} y={y} buttons={bin(bits)}")
    else:
      log.exception("Failed to save gear position: %s", err)
      messagebox.showerror("Error", f"Failed to save gear pos: {err}")

  def record_button_key(self):
    # Open a small modal and wait for a hardware button press, then capture the next keyboard key.
    wnd = tk.Toplevel(self)
    wnd.title("Record Button")
    wnd.geometry("360x120")
    lbl = tk.Label(wnd, text="Press a hardware button now...")
    lbl.pack(pady=8)
    cancel = tk.Button(wnd, text="Cancel", command=wnd.destroy)
    cancel.pack(pady=6)

    start = time.time()

    def poll():
      # prefer recent recorded rising-edge bits so user doesn't need to hold hardware button
      active = ui_backend.active_button_list(self.state, self.lock)

      if active:
        lbl.config(
          text=f"Detected bits: {active}\nPress the keyboard key to assign")
        wnd.focus_set()

        def on_key(event):
          key = event.keysym.lower()
          for i in active:
            self.button_entries[i].delete(0, tk.END)
            self.button_entries[i].insert(0, key)
            self.conf.setdefault("mappings", {}).setdefault(
              "buttons", {})[str(i)] = key

          ok, err = ui_backend.save_config(self.conf, self.config_path)
          if ok:
            messagebox.showinfo("Saved", f"Mapped bits {active} -> {key}")
          else:
            log.exception(
              "Failed to save mapping during record_button_key: %s", err)
            messagebox.showerror("Error", f"Failed to save config: {err}")

          try:
            wnd.unbind('<Key>')
          except Exception as e:
            log.debug("Failed to unbind key handler: %s", e)
          wnd.destroy()

        wnd.bind('<Key>', on_key)
        return

      if time.time() - start > 6.0:
        lbl.config(text="Timed out waiting for hardware press")
        return

      wnd.after(50, poll)

    poll()


def gui_loop(state: dict, lock, config_path=None):
  """
  Start the Tk mainloop for the calibration/mapping GUI.

  Args:
    state: shared input_state dict.
    lock: threading lock protecting `state`.
    config_path: optional path to configuration file.
  """
  conf = cfg.load_config(config_path)

  # attempt to use PIL for PNG support; fallback to tk.PhotoImage
  Image: Any = None
  ImageTk: Any = None
  try:
    from PIL import Image as PILImage, ImageTk as PILImageTk
    Image = PILImage
    ImageTk = PILImageTk
    PIL_AVAILABLE = True
  except ImportError:
    PIL_AVAILABLE = False

  root = tk.Tk()
  root.title("G25 Driver — Calibration & Mapping")

  gear_var = tk.StringVar()
  xy_var = tk.StringVar()
  btn_var = tk.StringVar()
  raw_var = tk.StringVar()
  status_var = tk.StringVar()

  # serial port selection
  port_var = tk.StringVar()
  # initialize from config if present
  port_var.set(conf.get("serial", {}).get("port", ""))
  port_status_var = tk.StringVar()

  tk.Label(root, textvariable=gear_var, font=("Arial", 20)).pack()
  tk.Label(root, textvariable=xy_var).pack()
  tk.Label(root, textvariable=btn_var).pack()
  tk.Label(root, textvariable=raw_var, font=("Courier", 8)).pack()

  # load UI image
  img_path = "shifter.jpg"
  if img_path and not os.path.isabs(img_path):
    img_path = os.path.join(os.path.dirname(__file__), img_path)

  # sizing defaults
  max_w = 1040
  max_h = 720

  tk_image = None
  img_w = min(480, max_w)
  img_h = min(320, max_h)
  if img_path and os.path.exists(img_path):
    try:
      if PIL_AVAILABLE:
        pil_img = Image.open(img_path)
        orig_w, orig_h = pil_img.size
        # scale down to fit within max_w x max_h while keeping aspect
        scale = min(max_w / orig_w, max_h / orig_h, 1.0)
        if scale < 1.0:
          new_w = max(1, int(orig_w * scale))
          new_h = max(1, int(orig_h * scale))
          # Pillow exposes LANCZOS in different locations depending on version
          resample = getattr(Image, "LANCZOS", None) or getattr(
            getattr(Image, "Resampling", None), "LANCZOS", None)
          pil_img = pil_img.resize((new_w, new_h), resample or 1)
        tk_image = ImageTk.PhotoImage(pil_img)
        img_w, img_h = pil_img.size
      else:
        # PhotoImage only supports integer subsample; compute factor
        raw_img: Any = tk.PhotoImage(file=img_path)
        w = raw_img.width()
        h = raw_img.height()
        subs_w = max(1, int((w + max_w - 1) // max_w))
        subs_h = max(1, int((h + max_h - 1) // max_h))
        subs = max(subs_w, subs_h)
        if subs > 1:
          tk_image = raw_img.subsample(subs, subs)
        else:
          tk_image = raw_img
        img_w = tk_image.width()
        img_h = tk_image.height()
    except Exception as e:
      status_var.set(f"Failed loading image: {e}")
  else:
    status_var.set(f"No UI image at {img_path}")

  frame = tk.Frame(root)
  frame.pack(pady=6)

  canvas = tk.Canvas(frame, width=img_w, height=img_h, bg="#ddd")
  canvas.pack()
  if tk_image:
    canvas_img = canvas.create_image(0, 0, anchor="nw", image=tk_image)
    # keep reference to avoid GC
    _image_refs.append(tk_image)
  else:
    canvas.create_rectangle(0, 0, img_w, img_h, fill="#ddd")

  # controls row
  ctrl_frame = tk.Frame(root)
  ctrl_frame.pack(fill="x", padx=6, pady=6)

  def calibrate():
    xs = []
    ys = []
    # sample a short burst
    for _ in range(30):
      with lock:
        xs.append(state.get("x", 0))
        ys.append(state.get("y", 0))
      time.sleep(0.02)
    if not xs:
      status_var.set("No samples read")
      return
    avg_x = sum(xs) / len(xs)
    avg_y = sum(ys) / len(ys)
    c = cfg.load_config(config_path)
    c["calibration"]["offset_x"] = int(round(-avg_x))
    c["calibration"]["offset_y"] = int(round(avg_y))
    cfg.save_config(c, config_path)
    status_var.set(
      f"Calibrated offsets -> offset_x={c['calibration']['offset_x']} offset_y={c['calibration']['offset_y']}")

  tk.Button(ctrl_frame, text="Calibrate Center",
            command=calibrate).pack(side="left", padx=6)
  tk.Button(ctrl_frame, text="Edit Mappings", command=lambda: MappingEditor(
    root, state, lock, config_path)).pack(side="left", padx=6)

  def reload_conf():
    new = cfg.load_config(config_path)
    conf.clear()
    conf.update(new)
    status_var.set("Config reloaded")
    rebuild_overlays()

  tk.Button(ctrl_frame, text="Reload Config",
            command=reload_conf).pack(side="left", padx=6)

  tk.Label(root, textvariable=status_var, fg="blue").pack()

  port_frame = tk.Frame(root)
  port_frame.pack(fill="x", padx=6, pady=4)

  tk.Label(port_frame, text="COM Port:").pack(side="left")

  def list_com_ports() -> list:
    return ui_backend.list_com_ports()

  def refresh_ports():
    ports = list_com_ports()
    menu = port_option['menu']
    menu.delete(0, 'end')
    for p in ports:
      menu.add_command(label=p, command=lambda v=p: on_port_selected(v))
    # choose sensible default: prefer configured port, else keep current, else first
    cfg_port = conf.get("serial", {}).get("port")
    if cfg_port and cfg_port in ports:
      port_var.set(cfg_port)
    elif port_var.get() and port_var.get() in ports:
      # keep current selection
      pass
    elif ports:
      port_var.set(ports[0])

  def on_port_selected(port):
    port_var.set(port)
    # save to config first
    try:
      conf.setdefault("serial", {})["port"] = port
      cfg.save_config(conf, config_path)
      saved = True
    except Exception as e:
      log.exception("Failed to save serial port to config")
      port_status_var.set(f"Failed to save config: {e}")
      saved = False

    # request serial switch
    try:
      from serial_reader import switch_port
    except ImportError as e:
      log.exception("Failed to import serial_reader for port switching")
      port_status_var.set(f"Failed to switch: serial support missing")
      return

    try:
      switch_port(port)
      if saved:
        port_status_var.set(f"Saved & switching to {port}")
      else:
        port_status_var.set(f"Switching to {port} (config save failed)")
    except Exception as e:
      log.exception("Error while requesting serial port switch")
      if saved:
        port_status_var.set(f"Saved to config, but failed to switch: {e}")
      else:
        port_status_var.set(f"Failed to switch and save: {e}")

  port_option = tk.OptionMenu(port_frame, port_var, "")
  port_option.pack(side="left", padx=6)
  tk.Button(port_frame, text="Refresh",
            command=refresh_ports).pack(side="left")
  tk.Label(port_frame, textvariable=port_status_var).pack(side="left", padx=6)

  # initial population
  try:
    refresh_ports()
  except Exception as e:
    log.exception("refresh_ports() failed: %s", e)

  # create overlay rectangles for configured button positions
  overlay_items = {}

  def rebuild_overlays():
    # remove existing overlays
    for v in list(overlay_items.values()):
      try:
        canvas.delete(v[0])
        canvas.delete(v[1])
      except Exception as e:
        log.debug("Failed to delete overlay items: %s", e)
    overlay_items.clear()
    labels = conf.get("mappings", {}).get("buttons", {}) or {}
    r = DEFAULT_RECT_SIZE
    for i_str, pos in DEFAULT_BUTTON_POSITIONS.items():
      try:
        i = int(i_str)
      except (ValueError, TypeError):
        continue
      if not pos:
        continue
      x = int(pos.get("x", 0))
      y = int(pos.get("y", 0))
      rect_id = canvas.create_rectangle(
        x - r, y - r, x + r, y + r, fill="white", outline="black", width=2)
      txt = labels.get(str(i), "")
      txt_id = canvas.create_text(
        x, y, text=txt, fill="black", font=("Arial", 10, "bold"))
      overlay_items[i] = (rect_id, txt_id)

  rebuild_overlays()

  def update():
    with lock:
      gv = state.get("gear_computed") or state.get("gear_arduino") or "N"
      x = state.get("x", 0)
      y = state.get("y", 0)
      btns = state.get("buttons", 0)
      raw = state.get("raw", "")
      last_bits = state.get("last_pressed_bits", 0)
      last_time = state.get("last_pressed_time", 0)

    gear_var.set(f"GEAR: {gv}")
    xy_var.set(f"X={x}  Y={y}")
    btn_var.set(f"BTN: {bin(btns)}")
    raw_var.set(raw)

    # update overlay colors
    nowt = time.time()
    for i, items in list(overlay_items.items()):
      rect_id, txt_id = items
      active = bool((btns >> i) & 1)
      recent = bool((last_bits >> i) & 1) and ((nowt - last_time) < 0.35)
      color = 'limegreen' if (active or recent) else 'white'
      try:
        canvas.itemconfig(rect_id, fill=color)
        canvas.tag_raise(txt_id)
      except tk.TclError as e:
        log.debug("Canvas update failed: %s", e)
      except Exception as e:
        log.debug("Unexpected canvas update error: %s", e)

    root.after(50, update)

  update()
  root.mainloop()
