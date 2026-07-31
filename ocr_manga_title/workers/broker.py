"""Dramatiq Redis broker configuration."""

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from ocr_manga_title.settings import REDIS_URL

broker = RedisBroker(url=REDIS_URL)  # type: ignore[no-untyped-call]
dramatiq.set_broker(broker)
