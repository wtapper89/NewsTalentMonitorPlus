from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.ndi import NDIlibSource, discover_ndi_sources


class FakeFinder:
    def __init__(self):
        self.now = 0.0
        self.waits = []
        self.destroyed = False

    def NDIlib_find_create_v2(self, settings):
        return 1

    def NDIlib_find_wait_for_sources(self, instance, timeout_ms):
        self.waits.append(timeout_ms)
        # Initial discovery wakes early with only two of six sources.
        self.now += min(0.1 if self.now < 0.1 else 0.4, timeout_ms / 1000)
        return True

    def NDIlib_find_get_current_sources(self, instance, count):
        size = 2 if self.now < 0.5 else 6
        count._obj.value = size
        return (NDIlibSource * size)(*[
            NDIlibSource(f'Source {i}'.encode(), f'host:{5960+i}'.encode())
            for i in range(size)
        ])

    def NDIlib_find_destroy(self, instance):
        self.destroyed = True


class DiscoveryTests(unittest.TestCase):
    def test_waits_past_first_partial_result(self):
        lib = FakeFinder()
        with patch('app.services.ndi.time.monotonic', side_effect=lambda: lib.now):
            sources = discover_ndi_sources(SimpleNamespace(lib=lib), timeout_ms=1000)
        self.assertEqual(len(sources), 6)
        self.assertGreater(len(lib.waits), 1)
        self.assertLessEqual(lib.now, 1.0)
        self.assertTrue(lib.destroyed)

    def test_zero_timeout_reads_without_waiting(self):
        lib = FakeFinder()
        sources = discover_ndi_sources(SimpleNamespace(lib=lib), timeout_ms=0)
        self.assertEqual(len(sources), 2)
        self.assertEqual(lib.waits, [])
        self.assertTrue(lib.destroyed)

    def test_finder_is_destroyed_after_sdk_error(self):
        lib = FakeFinder()
        with patch.object(lib, 'NDIlib_find_wait_for_sources', side_effect=RuntimeError('SDK error')):
            with self.assertRaises(RuntimeError):
                discover_ndi_sources(SimpleNamespace(lib=lib))
        self.assertTrue(lib.destroyed)


if __name__ == '__main__':
    unittest.main()
