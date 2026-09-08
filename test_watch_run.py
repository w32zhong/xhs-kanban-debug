#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import watch_run


class WatchRunOutputTests(unittest.TestCase):
    def test_output_path_creates_missing_logs_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            out = watch_run.prepare_output_path(root, "example-board")

            self.assertEqual(out, root / "logs" / "example-board-watch.log")
            self.assertTrue(out.parent.is_dir())


if __name__ == "__main__":
    unittest.main()
