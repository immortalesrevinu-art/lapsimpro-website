"""Static hub data: news.json and coaching-videos.json stay valid for GitHub Pages."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def load(name: str):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def test_news_json_has_dated_outbound_items():
    data = load("news.json")
    items = data["items"]
    assert 6 <= len(items) <= 20
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids))
    for item in items:
        assert item["title"]
        assert item["source"]
        assert item["url"].startswith("https://")
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", item["date"])
        assert item["summary"]


def test_coaching_videos_are_youtube_embeds_only():
    data = load("coaching-videos.json")
    videos = data["videos"]
    assert 6 <= len(videos) <= 16
    featured = [video for video in videos if video.get("featured")]
    assert len(featured) >= 2
    ids = [video["id"] for video in videos]
    assert len(ids) == len(set(ids))
    for video in videos:
        assert YOUTUBE_ID.match(video["id"])
        assert video["title"]
        assert video["creator"]
        assert video["watchUrl"] == f"https://www.youtube.com/watch?v={video['id']}"
        assert video["embedUrl"] == f"https://www.youtube-nocookie.com/embed/{video['id']}"
        assert "youtube.com/watch" in video["watchUrl"]
        assert not video["embedUrl"].startswith("http://")
        assert "mp4" not in video["embedUrl"].lower()


def test_seed_videos_present():
    ids = {video["id"] for video in load("coaching-videos.json")["videos"]}
    assert "8OtYGr5zLkg" in ids
    assert "dVfCvMcdMxU" in ids
