from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from neurodaily.config import Config
from neurodaily.models import Item
from neurodaily.seen import filter_seen


class SeenDedupTests(unittest.TestCase):
    def test_previous_day_item_is_hidden(self):
        with TemporaryDirectory() as directory:
            cfg = Config.load()
            cfg.output = {"dir": directory, "seen_dedup": True}
            first = [Item("Same title", url="https://example.test/a")]
            kept = filter_seen(first, cfg, today=date(2026, 11, 22))
            self.assertEqual(len(kept), 1)
            again = filter_seen([Item("Same title", url="https://example.test/a")],
                                cfg, today=date(2026, 11, 23))
            self.assertEqual(again, [])
            kept_same_day = filter_seen([Item("Same title", url="https://example.test/a")],
                                        cfg, today=date(2026, 11, 22))
            self.assertEqual(len(kept_same_day), 1)


if __name__ == "__main__":
    unittest.main()
