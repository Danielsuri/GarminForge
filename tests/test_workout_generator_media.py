"""Unit tests for web.workout_generator._build_media_map()."""

from __future__ import annotations

import pathlib


from web.workout_generator import _build_media_map


class TestBuildMediaMap:
    def test_empty_static_dir_returns_empty_dict(self, tmp_path: pathlib.Path) -> None:
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        assert _build_media_map(static_dir) == {}

    def test_missing_gifs_dir_is_not_error(self, tmp_path: pathlib.Path) -> None:
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        result = _build_media_map(static_dir)
        assert isinstance(result, dict)

    def test_gif_files_loaded(self, tmp_path: pathlib.Path) -> None:
        static_dir = tmp_path / "static"
        gif_dir = static_dir / "gifs"
        gif_dir.mkdir(parents=True)
        (gif_dir / "BARBELL_BENCH_PRESS.gif").write_bytes(b"")
        (gif_dir / "PULL_UP.gif").write_bytes(b"")
        result = _build_media_map(static_dir)
        assert result["BARBELL_BENCH_PRESS"] == "/static/gifs/BARBELL_BENCH_PRESS.gif"
        assert result["PULL_UP"] == "/static/gifs/PULL_UP.gif"

    def test_mp4_files_loaded(self, tmp_path: pathlib.Path) -> None:
        static_dir = tmp_path / "static"
        video_dir = static_dir / "videos"
        video_dir.mkdir(parents=True)
        (video_dir / "bulgarian-split-squat.mp4").write_bytes(b"")
        result = _build_media_map(static_dir)
        assert result["BULGARIAN_SPLIT_SQUAT"] == "/static/videos/bulgarian-split-squat.mp4"

    def test_mp4_takes_priority_over_gif(self, tmp_path: pathlib.Path) -> None:
        static_dir = tmp_path / "static"
        (static_dir / "gifs").mkdir(parents=True)
        (static_dir / "videos").mkdir(parents=True)
        (static_dir / "gifs" / "BULGARIAN_SPLIT_SQUAT.gif").write_bytes(b"")
        (static_dir / "videos" / "bulgarian-split-squat.mp4").write_bytes(b"")
        result = _build_media_map(static_dir)
        assert result["BULGARIAN_SPLIT_SQUAT"].endswith(".mp4")

    def test_non_media_files_ignored(self, tmp_path: pathlib.Path) -> None:
        static_dir = tmp_path / "static"
        gif_dir = static_dir / "gifs"
        gif_dir.mkdir(parents=True)
        (gif_dir / "README.txt").write_bytes(b"")
        (gif_dir / ".gitkeep").write_bytes(b"")
        assert _build_media_map(static_dir) == {}

    def test_real_videos_include_shipped_mp4s(self) -> None:
        """Sanity check: the 3 AI-generated MP4s are present."""
        result = _build_media_map()
        assert result.get("BULGARIAN_SPLIT_SQUAT", "").endswith(".mp4")
        assert result.get("JUMP_SQUAT", "").endswith(".mp4")
        assert result.get("BURPEE", "").endswith(".mp4")

    def test_gif_only_exercise_returns_gif_url(self, tmp_path: pathlib.Path) -> None:
        static_dir = tmp_path / "static"
        gif_dir = static_dir / "gifs"
        gif_dir.mkdir(parents=True)
        (gif_dir / "BARBELL_DEADLIFT.gif").write_bytes(b"")
        result = _build_media_map(static_dir)
        assert result["BARBELL_DEADLIFT"] == "/static/gifs/BARBELL_DEADLIFT.gif"

    def test_hyphenated_gif_stem_normalised(self, tmp_path: pathlib.Path) -> None:
        """GIF stems are normalised same as MP4 (upper + hyphen→underscore)."""
        static_dir = tmp_path / "static"
        gif_dir = static_dir / "gifs"
        gif_dir.mkdir(parents=True)
        (gif_dir / "barbell-bench-press.gif").write_bytes(b"")
        result = _build_media_map(static_dir)
        assert "BARBELL_BENCH_PRESS" in result
