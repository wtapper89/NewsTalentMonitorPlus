from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import httpx

from app.models import MicSnapshot
from app.services.dashboard import DashboardService
from app.services.photos import AnchorPhotoResolver, normalized_anchor_filename, parse_unc_path
from app.services.shure import (
    MicboardAdapter,
    MockShureAdapter,
    QlxdAdapter,
    QlxdChannelState,
    build_endpoint_url,
    deep_get,
    render_template,
)
from app.store import MappingStore, StateStore


class UtilityTests(unittest.TestCase):
    def test_deep_get_supports_nested_paths(self) -> None:
        payload = {"battery": {"percent": 77}, "items": [{"name": "Mic"}]}
        self.assertEqual(deep_get(payload, "battery.percent"), 77)
        self.assertEqual(deep_get(payload, "items.0.name"), "Mic")
        self.assertEqual(deep_get(payload, "items.1.name", "missing"), "missing")

    def test_render_template_replaces_nested_values(self) -> None:
        payload = {"name": "{name}", "meta": ["{name}", "ok"]}
        rendered = render_template(payload, {"name": "HOST MIC"})
        self.assertEqual(rendered["name"], "HOST MIC")
        self.assertEqual(rendered["meta"][0], "HOST MIC")

    def test_build_endpoint_url_uses_ip_and_path(self) -> None:
        mic = {"device_ip": "192.168.1.22", "scheme": "https", "port": 4443, "telemetry_path": "/status"}
        url = build_endpoint_url(mic, "telemetry_url", "telemetry_path", {"scheme": "https", "port": 443})
        self.assertEqual(url, "https://192.168.1.22:4443/status")


class MappingStoreTests(unittest.TestCase):
    def test_mapping_store_normalizes_legacy_url_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            mapping_file.write_text(
                """
                {
                  "mics": [
                    {
                      "id": "mic-1",
                      "default_name": "HOST",
                      "telemetry_url": "https://10.0.0.9:4443/api/channel/1",
                      "rename_url": "https://10.0.0.9:4443/api/channel/1/name"
                    }
                  ]
                }
                """.strip(),
                encoding="utf-8",
            )

            mapping = MappingStore(mapping_file).load()

            self.assertEqual(mapping["mics"][0]["device_ip"], "10.0.0.9")
            self.assertEqual(mapping["mics"][0]["port"], 4443)
            self.assertEqual(mapping["mics"][0]["telemetry_path"], "/api/channel/1")
            self.assertEqual(mapping["mics"][0]["rename_path"], "/api/channel/1/name")

    def test_mapping_store_normalizes_display_and_companion_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            mapping_file.write_text(
                """
                {
                  "display": {
                    "show_title_mode": "companion",
                    "manual_show_title": "TVC NEWS",
                    "preview_mode": "ndi",
                    "preview_url": "http://127.0.0.1:9000/preview",
                    "font_family": "Gotham"
                  },
                  "companion": {
                    "enabled": true,
                    "base_url": "http://127.0.0.1:8000/",
                    "connection_label": "Cuez",
                    "variable_name": "segment_title"
                  }
                }
                """.strip(),
                encoding="utf-8",
            )

            mapping = MappingStore(mapping_file).load()

            self.assertEqual(mapping["display"]["show_title_mode"], "companion")
            self.assertEqual(mapping["display"]["preview_mode"], "ndi")
            self.assertEqual(mapping["display"]["font_family"], "Gotham")
            self.assertTrue(mapping["companion"]["enabled"])
            self.assertEqual(mapping["companion"]["base_url"], "http://127.0.0.1:8000")
            self.assertEqual(mapping["companion"]["variable_name"], "segment_title")

    def test_mapping_store_normalizes_anchor_photos_and_assignment_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            mapping_file.write_text(
                """
                {
                  "anchor_photos": {
                    "enabled": true,
                    "share_path": "\\\\\\\\server\\\\folder",
                    "username": "anchor-user",
                    "password": "secret"
                  },
                  "mics": [
                    {
                      "id": "mic-1",
                      "default_name": "MIC 1",
                      "assignment_variable_name": "mic_1_anchor"
                    }
                  ]
                }
                """.strip(),
                encoding="utf-8",
            )

            mapping = MappingStore(mapping_file).load()

            self.assertTrue(mapping["anchor_photos"]["enabled"])
            self.assertEqual(mapping["anchor_photos"]["share_path"], "\\\\server\\folder")
            self.assertEqual(mapping["mics"][0]["assignment_variable_name"], "mic_1_anchor")


class AnchorPhotoTests(unittest.TestCase):
    def test_anchor_photo_names_match_share_filenames(self) -> None:
        self.assertEqual(normalized_anchor_filename("John Smith"), "JohnSmith")
        self.assertEqual(normalized_anchor_filename("Dr. Amy O'Neil"), "DrAmyONeil")

    def test_unc_path_is_split_for_smbclient(self) -> None:
        service, remote_dir = parse_unc_path("\\\\server\\folder\\Headshots")
        self.assertEqual(service, "//server/folder")
        self.assertEqual(remote_dir, "Headshots")

    def test_http_photo_urls_try_supported_extensions(self) -> None:
        resolver = AnchorPhotoResolver()
        urls = resolver.photo_urls_for("John Smith", {"enabled": True, "base_url": "http://vmix:8090/photos"})
        self.assertEqual(
            urls,
            [
                "http://vmix:8090/photos/JohnSmith.png",
                "http://vmix:8090/photos/JohnSmith.jpg",
                "http://vmix:8090/photos/JohnSmith.jpeg",
            ],
        )


class DashboardServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_assignment_is_merged_into_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            store = StateStore(state_file)
            store.set_assignment("mic-1", "Anchor")
            service = DashboardService(MockShureAdapter(), store, "mock", 2)

            state = await service.refresh()
            companion_state = await service.companion_state()
            await service.close()

            self.assertEqual(state["mics"][0]["assigned_to"], "Anchor")
            self.assertGreaterEqual(state["summary"]["total"], 1)
            self.assertIn("summary_total", companion_state["variables"])
            self.assertIn("history", state["mics"][0])

    async def test_manual_display_state_is_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            MappingStore(mapping_file).save(
                {
                    "display": {
                        "show_title_mode": "manual",
                        "manual_show_title": "TVC NEWS",
                        "preview_mode": "placeholder",
                        "preview_source_name": "StudioCam",
                        "font_family": "Gotham",
                    }
                }
            )
            service = DashboardService(
                MockShureAdapter(),
                StateStore(Path(temp_dir) / "state.json"),
                "mock",
                2,
                mapping_store=MappingStore(mapping_file),
            )

            state = await service.refresh()
            await service.close()

        self.assertEqual(state["display"]["show_title"], "TVC NEWS")
        self.assertEqual(state["display"]["show_title_source"], "manual")
        self.assertEqual(state["display"]["preview_source_name"], "StudioCam")
        self.assertEqual(state["display"]["font_family"], "Gotham")

    async def test_companion_variable_can_drive_display_title(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://127.0.0.1:8000/api/variable/Cuez/segment_title/value",
            )
            return httpx.Response(200, json="Election Special")

        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            MappingStore(mapping_file).save(
                {
                    "display": {
                        "show_title_mode": "companion",
                        "manual_show_title": "Fallback Title",
                    },
                    "companion": {
                        "enabled": True,
                        "base_url": "http://127.0.0.1:8000",
                        "connection_label": "Cuez",
                        "variable_name": "segment_title",
                    },
                }
            )
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            service = DashboardService(
                MockShureAdapter(),
                StateStore(Path(temp_dir) / "state.json"),
                "mock",
                2,
                mapping_store=MappingStore(mapping_file),
                client=client,
            )

            state = await service.refresh()
            await service.close()
            await client.aclose()

        self.assertEqual(state["display"]["show_title"], "Election Special")
        self.assertEqual(state["display"]["show_title_source"], "companion")

    async def test_companion_variables_can_drive_now_and_next_sources(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            values = {
                "http://127.0.0.1:8000/api/variable/custom/OnAir/value": "Studio Camera 2",
                "http://127.0.0.1:8000/api/variable/custom/NextUp/value": "Weather Center",
            }
            self.assertIn(str(request.url), values)
            return httpx.Response(200, json=values[str(request.url)])

        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            MappingStore(mapping_file).save(
                {
                    "companion": {
                        "enabled": True,
                        "base_url": "http://127.0.0.1:8000",
                        "connection_label": "custom",
                        "on_air_source_variable_name": "OnAir",
                        "next_source_variable_name": "NextUp",
                    },
                }
            )
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            service = DashboardService(
                MockShureAdapter(),
                StateStore(Path(temp_dir) / "state.json"),
                "mock",
                2,
                mapping_store=MappingStore(mapping_file),
                client=client,
            )

            state = await service.refresh()
            await service.close()
            await client.aclose()

        self.assertEqual(state["display"]["on_air_source_name"], "Studio Camera 2")
        self.assertEqual(state["display"]["next_source_name"], "Weather Center")

    async def test_companion_variable_can_drive_mic_assignment(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://127.0.0.1:8000/api/variable/Cuez/mic_1_anchor/value",
            )
            return httpx.Response(200, json="John Smith")

        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            MappingStore(mapping_file).save(
                {
                    "companion": {
                        "enabled": True,
                        "base_url": "http://127.0.0.1:8000",
                        "connection_label": "Cuez",
                    },
                    "mics": [
                        {
                            "id": "mic-1",
                            "default_name": "MIC 1",
                            "assignment_variable_name": "mic_1_anchor",
                        }
                    ],
                }
            )
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            service = DashboardService(
                MockShureAdapter(),
                StateStore(Path(temp_dir) / "state.json"),
                "mock",
                2,
                mapping_store=MappingStore(mapping_file),
                client=client,
            )

            state = await service.refresh()
            await service.close()
            await client.aclose()

        self.assertEqual(state["mics"][0]["assigned_to"], "John Smith")

    async def test_companion_assignment_accepts_wrapped_custom_variable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://127.0.0.1:8000/api/variable/custom/Mic1/value",
            )
            return httpx.Response(200, json="John Smith")

        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            MappingStore(mapping_file).save(
                {
                    "companion": {
                        "enabled": True,
                        "base_url": "http://127.0.0.1:8000",
                        "connection_label": "Cuez",
                    },
                    "mics": [
                        {
                            "id": "mic-1",
                            "default_name": "MIC 1",
                            "assignment_variable_name": "$(custom:Mic1)",
                        }
                    ],
                }
            )
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            service = DashboardService(
                MockShureAdapter(),
                StateStore(Path(temp_dir) / "state.json"),
                "mock",
                2,
                mapping_store=MappingStore(mapping_file),
                client=client,
            )

            state = await service.refresh()
            await service.close()
            await client.aclose()

        self.assertEqual(state["mics"][0]["assigned_to"], "John Smith")

    async def test_state_includes_trimmed_telemetry_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            store = StateStore(state_file)
            service = DashboardService(MockShureAdapter(), store, "mock", 2)

            service._record_history(  # type: ignore[attr-defined]
                [
                    MicSnapshot(
                        id="mic-1",
                        shure_name="HOST",
                        receiver_name="Rack A",
                        channel_label="A1",
                        battery_percent=100,
                        signal_strength=10,
                        audio_level=20,
                    )
                ],
                captured_at=100.0,
            )
            service._record_history(  # type: ignore[attr-defined]
                [
                    MicSnapshot(
                        id="mic-1",
                        shure_name="HOST",
                        receiver_name="Rack A",
                        channel_label="A1",
                        battery_percent=100,
                        signal_strength=40,
                        audio_level=60,
                    )
                ],
                captured_at=130.0,
            )
            service._record_history(  # type: ignore[attr-defined]
                [
                    MicSnapshot(
                        id="mic-1",
                        shure_name="HOST",
                        receiver_name="Rack A",
                        channel_label="A1",
                        battery_percent=100,
                        signal_strength=75,
                        audio_level=80,
                    )
                ],
                captured_at=161.0,
            )

            state = service._build_state(  # type: ignore[attr-defined]
                [
                    MicSnapshot(
                        id="mic-1",
                        shure_name="HOST",
                        receiver_name="Rack A",
                        channel_label="A1",
                        battery_percent=100,
                        signal_strength=75,
                        audio_level=80,
                    )
                ],
                "ok",
                "Live data connected",
            )

        history = state["mics"][0]["history"]
        self.assertEqual(history["window_seconds"], 60)
        self.assertEqual([sample["value"] for sample in history["signal_strength"]], [40, 75])
        self.assertEqual([sample["value"] for sample in history["audio_level"]], [60, 80])


class QlxdTelemetryTests(unittest.TestCase):
    def test_channel_state_parses_reports_and_samples(self) -> None:
        state = QlxdChannelState(channel=1)

        state.apply_frame("REPLY 1 CHAN_NAME {HOST MIC}")
        state.apply_frame("REPORT 1 BATT_BARS 003")
        state.apply_frame("REP 1 ENCRYPTION_WARNING OFF")
        state.apply_frame("SAMPLE 1 ALL XB 035 040")

        self.assertEqual(state.name, "HOST MIC")
        self.assertEqual(state.battery_percent(), 60)
        self.assertEqual(state.rf_level, 30)
        self.assertEqual(state.audio_level, 80)
        self.assertTrue(state.has_recent_audio_peak(state.peak_at))
        self.assertEqual(state.battery_alert(state.battery_seen_at), "")

    def test_qlxd_adapter_builds_warning_snapshot_from_cached_state(self) -> None:
        class FakeRuntime:
            def __init__(self, state: QlxdChannelState) -> None:
                self.connection_status = "connected"
                self.last_error = ""
                self._state = state

            def state_for_channel(self, channel: int) -> QlxdChannelState:
                return self._state

            def diagnostics(self) -> dict:
                return {
                    "host": "10.0.0.11",
                    "port": 2202,
                    "connection_status": "connected",
                    "channels": [
                        {
                            "channel": 1,
                            "name": self._state.name,
                            "battery_percent": self._state.battery_percent(),
                            "rf_level": self._state.rf_level,
                            "audio_level": self._state.audio_level,
                        }
                    ],
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = QlxdAdapter(MappingStore(Path(temp_dir) / "mapping.json"))
            state = QlxdChannelState(channel=1)
            state.apply_frame("REP 1 CHAN_NAME {HOST MIC}")
            state.apply_frame("REP 1 BATT_BARS 002")
            state.apply_frame("REP 1 ENCRYPTION_WARNING ON")
            state.apply_frame("SAMPLE 1 ALL XB 080 050")
            adapter._receivers[("10.0.0.11", 2202)] = FakeRuntime(state)  # type: ignore[assignment]

            snapshot = adapter._snapshot_for_mic(
                {
                    "id": "mic-1",
                    "default_name": "HOST",
                    "receiver_name": "Rack A",
                    "channel_label": "A1",
                    "receiver_channel": 1,
                    "device_ip": "10.0.0.11",
                    "port": 2202,
                },
                {"port": 2202},
            )

        self.assertTrue(snapshot.is_online)
        self.assertEqual(snapshot.shure_name, "HOST MIC")
        self.assertEqual(snapshot.battery_percent, 40)
        self.assertGreater(snapshot.signal_strength, 0)
        self.assertNotIn("Low battery", snapshot.errors)
        self.assertNotIn("Battery replace soon", snapshot.errors)
        self.assertIn("Audio peak", snapshot.errors)
        self.assertIn("Encryption mismatch", snapshot.errors)

    def test_qlxd_adapter_diagnostics_reports_receiver_state(self) -> None:
        class FakeRuntime:
            def diagnostics(self) -> dict:
                return {
                    "host": "10.0.0.11",
                    "port": 2202,
                    "connection_status": "connected",
                    "channels": [{"channel": 1, "name": "HOST MIC"}],
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = QlxdAdapter(MappingStore(Path(temp_dir) / "mapping.json"))
            adapter._receivers[("10.0.0.11", 2202)] = FakeRuntime()  # type: ignore[assignment]

            diagnostics = adapter.diagnostics()

        self.assertEqual(diagnostics["source"], "qlxd")
        self.assertEqual(diagnostics["receivers"][0]["host"], "10.0.0.11")
        self.assertEqual(diagnostics["receivers"][0]["channels"][0]["name"], "HOST MIC")


class MicboardAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_maps_receivers_by_ip_not_display_label(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://micboard.local/data.json")
            return httpx.Response(
                200,
                json={
                    "receivers": [
                        {
                            "ip": "10.0.0.11",
                            "status": "CONNECTED",
                            "raw": {"DEVICE_ID": "QLXD4-1"},
                            "tx": [
                                {
                                    "slot": 1,
                                    "channel": 1,
                                    "name": "HOST",
                                    "name_raw": "HOST MIC",
                                    "battery": 4,
                                    "audio_level": 7,
                                    "rf_level": 9,
                                    "status": "CONNECTED",
                                    "raw": {},
                                }
                            ],
                        },
                        {
                            "ip": "10.0.0.12",
                            "status": "CONNECTED",
                            "raw": {"DEVICE_ID": "QLXD4-2"},
                            "tx": [
                                {
                                    "slot": 1,
                                    "channel": 1,
                                    "name": "GUEST",
                                    "name_raw": "GUEST MIC",
                                    "battery": 1,
                                    "audio_level": 2,
                                    "rf_level": 5,
                                    "status": "CRITICAL",
                                    "raw": {},
                                }
                            ],
                        },
                    ]
                },
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            store = MappingStore(mapping_file)
            store.save(
                {
                    "micboard": {"data_url": "http://micboard.local/data.json"},
                    "mics": [
                        {
                            "id": "mic-1",
                            "default_name": "HOST",
                            "receiver_name": "Rack A",
                            "channel_label": "A1",
                            "receiver_channel": 1,
                            "micboard_slot": 0,
                            "device_ip": "10.0.0.11",
                        },
                        {
                            "id": "mic-2",
                            "default_name": "GUEST",
                            "receiver_name": "Rack B",
                            "channel_label": "A2",
                            "receiver_channel": 1,
                            "micboard_slot": 0,
                            "device_ip": "10.0.0.12",
                        },
                    ],
                }
            )
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            adapter = MicboardAdapter(store, client=client)

            snapshots = await adapter.refresh()
            await client.aclose()

        self.assertEqual([snapshot.id for snapshot in snapshots], ["mic-1", "mic-2"])
        self.assertEqual(snapshots[0].shure_name, "HOST MIC")
        self.assertEqual(snapshots[0].receiver_name, "Rack A")
        self.assertEqual(snapshots[0].battery_percent, 80)
        self.assertTrue(snapshots[0].is_online)
        self.assertEqual(snapshots[1].receiver_name, "Rack B")
        self.assertEqual(snapshots[1].battery_percent, 20)
        self.assertNotIn("Low battery", snapshots[1].errors)

    async def test_refresh_returns_offline_snapshots_when_micboard_request_fails(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"detail": "unavailable"})

        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "mapping.json"
            store = MappingStore(mapping_file)
            store.save(
                {
                    "micboard": {"data_url": "http://micboard.local/data.json"},
                    "mics": [
                        {
                            "id": "mic-1",
                            "default_name": "HOST",
                            "receiver_name": "Rack A",
                            "channel_label": "A1",
                            "receiver_channel": 1,
                            "device_ip": "10.0.0.11",
                        }
                    ],
                }
            )
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            adapter = MicboardAdapter(store, client=client)

            snapshots = await adapter.refresh()
            await client.aclose()

        self.assertEqual(len(snapshots), 1)
        self.assertFalse(snapshots[0].is_online)
        self.assertIn("Fetch failed", snapshots[0].errors[0])


if __name__ == "__main__":
    unittest.main()
