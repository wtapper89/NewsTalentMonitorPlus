from __future__ import annotations

import unittest
import ctypes
from types import SimpleNamespace
from unittest.mock import patch

from app.services.ndi import NDIlibSource, NDIlibRecvCreateV3, NDIReceiver, discover_ndi_sources


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


class ReceiverLayoutTests(unittest.TestCase):
    def test_receiver_settings_include_final_name_pointer(self):
        # SDK v3 layout: source (two pointers), two enums, bool, name pointer.
        pointer_size = ctypes.sizeof(ctypes.c_void_p)
        name_offset = ((2 * pointer_size + 9 + pointer_size - 1) // pointer_size) * pointer_size
        self.assertEqual(NDIlibRecvCreateV3.p_ndi_recv_name.offset, name_offset)
        self.assertEqual(ctypes.sizeof(NDIlibRecvCreateV3), name_offset + pointer_size)

    def test_connect_passes_valid_receiver_settings(self):
        from unittest.mock import Mock
        lib = Mock()
        lib.NDIlib_recv_create_v3.return_value = 123
        receiver = NDIReceiver(SimpleNamespace(lib=lib), 'vMix')
        source = NDIlibSource(b'vMix', b'host:5961')
        with patch.object(receiver, '_find_source', return_value=source):
            receiver.connect()
        settings = lib.NDIlib_recv_create_v3.call_args.args[0]._obj
        self.assertEqual(settings.p_ndi_recv_name, b'News Talent Monitor+')
        self.assertEqual(settings.source_to_connect_to.p_ndi_name, b'vMix')
        self.assertEqual(receiver.recv_instance, 123)
        receiver.close()
        lib.NDIlib_recv_destroy.assert_called_once_with(123)


if __name__ == '__main__':
    unittest.main()
