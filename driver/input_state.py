import threading

lock = threading.Lock()

state = {
    "gear_arduino": "N",
    "gear_computed": "N",
    "x": 0,
    "y": 0,
    "buttons": 0,
    "raw": "",
    "last_pressed_bits": 0,
    "last_pressed_time": 0.0
}

running = True
