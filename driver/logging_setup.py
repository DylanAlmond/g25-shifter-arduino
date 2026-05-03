"""
Simple logging configuration helper for the driver.

Provides `setup_logging()` which configures basic logging and returns the
named logger used across driver modules.
"""
import logging


def setup_logging():
  """Configure basic logging and return the 'g25-driver' logger."""
  logging.basicConfig(
      level=logging.DEBUG,
      format="%(asctime)s | %(levelname)s | %(message)s"
  )
  return logging.getLogger("g25-driver")
