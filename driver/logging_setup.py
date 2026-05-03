import logging


def setup_logging():
  logging.basicConfig(
      level=logging.DEBUG,
      format="%(asctime)s | %(levelname)s | %(message)s"
  )
  return logging.getLogger("g25-driver")
