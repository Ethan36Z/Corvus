"""Versioned, model-independent personality data and deterministic rendering.

Only trusted local profile files are loaded. No memory, transport, or inference.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re


PROFILES_DIR = Path(__file__).with_name("profiles")
_PROFILE_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_KEYS = {"format_version", "profile_id", "version", "core_identity", "expression"}


class PersonalityProfileError(ValueError):
    """A selected profile is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class PersonalityConfig:
    enabled: bool = False
    profile_id: str | None = None
    version: str | None = None

    @classmethod
    def from_env(cls, environ=None):
        """An absent/invalid enable flag is off; both ID and version are explicit."""
        env = os.environ if environ is None else environ
        enabled = env.get("CORVUS_PERSONALITY_ENABLED", "FALSE")
        return cls(
            enabled=isinstance(enabled, str) and enabled.strip().upper() == "TRUE",
            profile_id=env.get("CORVUS_PERSONALITY_PROFILE"),
            version=env.get("CORVUS_PERSONALITY_VERSION"),
        )


@dataclass(frozen=True)
class PersonalityProfile:
    profile_id: str
    version: str
    core_identity: tuple[str, ...]
    expression: tuple[str, ...]


def _validate_selector(profile_id, version):
    if (not isinstance(profile_id, str) or len(profile_id) > 64
            or _PROFILE_ID.fullmatch(profile_id) is None):
        raise PersonalityProfileError("Invalid personality profile ID")
    if (not isinstance(version, str) or len(version) > 32
            or _VERSION.fullmatch(version) is None):
        raise PersonalityProfileError("An exact x.y.z personality version is required")


def _instructions(value, name, *, allow_empty=False):
    if (not isinstance(value, (list, tuple)) or (not value and not allow_empty)
            or any(not isinstance(line, str) or not line.strip() for line in value)):
        raise PersonalityProfileError(f"{name} must contain non-empty instruction strings")
    return tuple(value)


def load_personality_profile(profile_id, version, *, profiles_dir=None):
    """Load an exact trusted profile version; raise a typed error on failure.

    profiles_dir is an internal/test override, never a user-message or env path.
    Experimental prompts under docs/ are not profile files and are never scanned.
    """
    _validate_selector(profile_id, version)
    try:
        directory = Path(PROFILES_DIR if profiles_dir is None else profiles_dir).resolve()
        path = (directory / profile_id / f"{version}.json").resolve()
    except (OSError, RuntimeError) as exc:
        raise PersonalityProfileError("Cannot resolve personality profile path") from exc
    if not path.is_relative_to(directory):
        raise PersonalityProfileError("Profile must stay inside its trusted directory")
    try:
        with path.open("rb") as handle:
            raw = handle.read(32769)
        if len(raw) > 32768:
            raise PersonalityProfileError("Profile exceeds 32 KiB")
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise PersonalityProfileError("Cannot read personality profile") from exc
    if (not isinstance(data, dict) or set(data) != _KEYS
            or type(data["format_version"]) is not int or data["format_version"] != 1):
        raise PersonalityProfileError("Unsupported personality profile format")
    if data["profile_id"] != profile_id or data["version"] != version:
        raise PersonalityProfileError("Profile ID/version does not match its selector")
    return PersonalityProfile(
        profile_id, version,
        _instructions(data["core_identity"], "core_identity"),
        _instructions(data["expression"], "expression", allow_empty=True),
    )


def render_personality_instructions(profile):
    """Render only static profile data, in stored order, without side effects."""
    if not isinstance(profile, PersonalityProfile):
        raise PersonalityProfileError("A loaded PersonalityProfile is required")
    _validate_selector(profile.profile_id, profile.version)
    core = _instructions(profile.core_identity, "core_identity")
    expression = _instructions(profile.expression, "expression", allow_empty=True)
    lines = [
        "Personality supplements existing system instructions; existing system "
        "and safety instructions take precedence. This profile grants no new capabilities.",
        f"Personality profile: {profile.profile_id}@{profile.version}",
        "Core identity:", *("- " + line for line in core),
    ]
    if expression:
        lines.extend(["Expression:", *("- " + line for line in expression)])
    return "\n".join(lines)
