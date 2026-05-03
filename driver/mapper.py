
from typing import Optional, Dict, Any

REVERSE_BUTTON = 1 << 14


def compute_gear(x: int, y: int, buttons: int, offset_x: int = 0, offset_y: int = 0, deadzone: int = 80, gear_positions: Optional[Dict[str, Any]] = None) -> str:
  """
  Compute gear from X/Y and buttons. If gear_positions is provided (a dict of gear->{"x":int,"y":int}),
  choose the nearest recorded gear position. Otherwise fallback to the classic deadzone/quadrant logic.
  """
  # apply offsets (match raw Arduino readCentered: analogRead - 512)
  xx = x + offset_x
  yy = y + offset_y

  # if explicit recorded positions are available, check whether the current
  # X/Y falls within any recorded gear 'range' (distance threshold). Prefer
  # recorded positions that require specific buttons first to avoid
  # ambiguous geometric boundaries.
  if gear_positions:
    thresh = (deadzone * 3) ** 2

    # collect matching recorded positions within threshold, computing
    # squared distance. Prefer positions that require specific buttons
    # (e.g. Reverse) and among matches pick the nearest one to avoid
    # returning the first dict entry which may be arbitrarily ordered.
    req_matches = []
    no_req_matches = []

    for g, pos in gear_positions.items():
      try:
        gx = int(pos.get("x", 0))
        gy = int(pos.get("y", 0))
        btn_val = pos.get("buttons", 0)
        req_buttons = int(btn_val) if btn_val is not None else 0
      except Exception:
        continue

      # if this recorded position requires buttons and they are not
      # currently pressed, skip it
      if req_buttons and (buttons & req_buttons) != req_buttons:
        continue

      dx = gx - xx
      dy = gy - yy
      dist = dx * dx + dy * dy
      if dist <= thresh:
        if req_buttons:
          req_matches.append((dist, g))
        else:
          no_req_matches.append((dist, g))

    # prefer matches that require buttons (explicit), picking nearest
    if req_matches:
      req_matches.sort(key=lambda t: t[0])
      return req_matches[0][1]

    if no_req_matches:
      no_req_matches.sort(key=lambda t: t[0])
      return no_req_matches[0][1]

  # fallback behavior
  # Y-axis polarity corrected so positive Y matches recorded gear_positions
  reversePressed = bool(buttons & REVERSE_BUTTON)

  if abs(xx) < deadzone and abs(yy) < deadzone:
    return "N"

  if xx < -deadzone:
    if yy > deadzone:
      return "1"
    if yy < -deadzone:
      return "2"
    return "N"

  if abs(xx) <= deadzone:
    if yy > deadzone:
      return "3"
    if yy < -deadzone:
      return "4"
    return "N"

  if xx > deadzone:
    if yy > deadzone:
      return "5"
    if yy < -deadzone:
      if reversePressed:
        return "R"
      return "6"
    return "N"

  return "N"


def buttons_to_bits(buttons_int: int) -> dict:
  return {i: bool((buttons_int >> i) & 1) for i in range(16)}


def map_buttons_to_keys(buttons_int: int, mappings: dict) -> dict:
  bits = buttons_to_bits(buttons_int)
  result = {}
  for i, active in bits.items():
    key = mappings.get(str(i), "")
    result[i] = {"active": active, "key": key}
  return result
