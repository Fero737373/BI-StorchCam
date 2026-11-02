from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from bi_storchcam.providers import stream_source

MANIFEST = "https://manifest.googlevideo.com/api/manifest/hls_variant/expire/2000000000/ei/abc/id/xyz/file/index.m3u8"


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    stream_source.clear_cache()


def fake_ytdlp(monkeypatch: pytest.MonkeyPatch, info: Any = None, error: Exception | None = None) -> list[str]:
    calls: list[str] = []

    class YoutubeDL:
        def __init__(self, options: dict) -> None:
            assert options["skip_download"] and options["quiet"]

        def __enter__(self) -> YoutubeDL:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def extract_info(self, url: str, download: bool) -> Any:
            assert download is False
            calls.append(url)
            if error:
                raise error
            return info

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=YoutubeDL))
    return calls


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/embed/W2CicgFq5oo", "W2CicgFq5oo"),
        ("https://www.youtube.com/watch?v=W2CicgFq5oo&t=4", "W2CicgFq5oo"),
        ("https://youtu.be/W2CicgFq5oo", "W2CicgFq5oo"),
        ("https://www.youtube-nocookie.com/embed/W2CicgFq5oo?autoplay=1", "W2CicgFq5oo"),
        ("https://m.youtube.com/live/W2CicgFq5oo", "W2CicgFq5oo"),
        ("https://www.youtube.com/embed/zu-kurz", ""),
        ("https://example.org/cam", ""),
    ],
)
def test_youtube_ids(url: str, expected: str) -> None:
    assert stream_source.youtube_id(url) == expected


def test_direct_hls_empty_and_other_pages() -> None:
    direct = stream_source.resolve("https://cam.example.org/live/index.m3u8", now=1000)
    assert direct["kind"] == "hls" and direct["upstream"].endswith("index.m3u8") and direct["expires"] > 1000
    assert stream_source.resolve("  ") == {"kind": "none"}
    assert stream_source.resolve("https://example.org/webcam")["kind"] == "embed"


def test_youtube_uses_master_playlist_caches_and_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    info = {"manifest_url": MANIFEST, "url": "https://variant", "protocol": "m3u8_native", "title": "Hafen live", "channel": "Hafencam", "is_live": True}
    calls = fake_ytdlp(monkeypatch, info)
    first = stream_source.resolve("https://www.youtube.com/embed/W2CicgFq5oo", now=1_000_000)
    assert first == {"kind": "hls", "upstream": MANIFEST, "title": "Hafen live", "channel": "Hafencam", "live": True, "expires": 2_000_000_000.0}
    assert stream_source.resolve("https://youtu.be/W2CicgFq5oo", now=1_000_100) == first
    assert calls == ["https://www.youtube.com/watch?v=W2CicgFq5oo"]
    stream_source.resolve("https://youtu.be/W2CicgFq5oo", refresh=True, now=1_000_200)
    assert len(calls) == 2


def test_expired_cache_is_resolved_again(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_ytdlp(monkeypatch, {"manifest_url": MANIFEST, "is_live": True})
    stream_source.resolve("https://youtu.be/W2CicgFq5oo", now=1_000)
    stream_source.resolve("https://youtu.be/W2CicgFq5oo", now=2_000_000_000 - stream_source.REFRESH_MARGIN + 1)
    assert len(calls) == 2


def test_hls_found_in_formats_list(monkeypatch: pytest.MonkeyPatch) -> None:
    info = {"protocol": "https", "url": "https://progressive.mp4", "formats": [{"protocol": "https"}, {"protocol": "m3u8_native", "manifest_url": MANIFEST}]}
    fake_ytdlp(monkeypatch, info)
    assert stream_source.resolve("https://youtu.be/W2CicgFq5oo")["upstream"] == MANIFEST


def test_errors_and_videos_without_hls_fall_back_to_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ytdlp(monkeypatch, error=RuntimeError("Sign in to confirm you are not a bot"))
    failed = stream_source.resolve("https://youtu.be/W2CicgFq5oo")
    assert failed["kind"] == "embed" and "not a bot" in failed["reason"]
    fake_ytdlp(monkeypatch, {"protocol": "https", "url": "https://progressive.mp4", "formats": []})
    assert stream_source.resolve("https://youtu.be/W2CicgFq5oo")["kind"] == "embed"


def test_expiry_and_quality_helpers() -> None:
    assert stream_source.expires_at(MANIFEST, 0) == 2_000_000_000
    assert stream_source.expires_at("https://x/videoplayback?expire=1234&id=1", 0) == 1234
    assert stream_source.expires_at("https://x/live.m3u8", 50) == 50 + stream_source.DEFAULT_LIFETIME
    assert stream_source.max_height("720") == 720 and stream_source.max_height("auto") == 1080 and stream_source.max_height("quatsch") == 1080
