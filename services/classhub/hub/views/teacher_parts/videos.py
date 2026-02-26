"""Compatibility re-exports for teacher video and asset views."""

from .videos_assets import teach_assets
from .videos_lessons import teach_videos

__all__ = [
    "teach_videos",
    "teach_assets",
]
