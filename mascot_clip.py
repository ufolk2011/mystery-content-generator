"""Compatibility wrapper — the lip-sync page uses moviepy, not AI models."""

from lip_sync import (  # noqa: F401
    LipSyncError as MascotClipError,
    make_lip_sync_clip as make_mascot_clip,
    render_lip_sync_page as render_mascot_clip_page,
)
