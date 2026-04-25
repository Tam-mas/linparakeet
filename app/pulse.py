"""
PulseAudio/PipeWire helpers for mic enumeration and Bluetooth profile switching.
All commands use `pactl` which works with both PA and PipeWire-PA compatibility.
"""
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class PaSource:
    index: int
    name: str
    description: str
    is_bluetooth: bool
    card_name: Optional[str] = None


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def list_pa_sources() -> list[PaSource]:
    out = _run(["pactl", "list", "sources"])
    sources: list[PaSource] = []
    current: dict = {}

    for line in out.splitlines():
        line_s = line.strip()
        if line.startswith("Source #"):
            if current:
                sources.append(_parse_source(current))
            current = {"index": int(line.split("#")[1])}
        elif line_s.startswith("Name:"):
            current["name"] = line_s.split(":", 1)[1].strip()
        elif line_s.startswith("Description:"):
            current["description"] = line_s.split(":", 1)[1].strip()
        elif "bluez" in line_s.lower():
            current["is_bluetooth"] = True

    if current:
        sources.append(_parse_source(current))

    return [s for s in sources if not s.name.endswith(".monitor")]


def _parse_source(d: dict) -> PaSource:
    name = d.get("name", "")
    desc = d.get("description", name)
    is_bt = d.get("is_bluetooth", "bluez" in name.lower())
    return PaSource(
        index=d.get("index", 0),
        name=name,
        description=desc,
        is_bluetooth=is_bt,
    )


def set_default_source(source_name: str) -> bool:
    result = subprocess.run(
        ["pactl", "set-default-source", source_name],
        capture_output=True, timeout=5,
    )
    return result.returncode == 0


def get_default_source() -> Optional[str]:
    out = _run(["pactl", "get-default-source"])
    return out.strip() or None


@dataclass
class BtCard:
    name: str
    active_profile: str
    hsphfp_profiles: list[str]


def list_bt_cards() -> list[BtCard]:
    out = _run(["pactl", "list", "cards"])
    cards: list[BtCard] = []
    in_bluez = False
    current: dict = {}

    for line in out.splitlines():
        line_s = line.strip()
        if line.startswith("\tName:") or line.startswith("Card #"):
            if in_bluez and current:
                cards.append(_parse_card(current))
            in_bluez = False
            current = {}
            if "bluez" in line_s.lower():
                in_bluez = True
                current["name"] = line_s.split(":", 1)[1].strip()
        elif in_bluez:
            if line_s.startswith("Name:"):
                current["name"] = line_s.split(":", 1)[1].strip()
            elif line_s.startswith("Active Profile:"):
                current["active"] = line_s.split(":", 1)[1].strip()
            elif "headset-head-unit" in line_s or "hsp" in line_s.lower() or "hfp" in line_s.lower():
                current.setdefault("hsp_profiles", [])
                prof = line_s.split(":")[0].strip()
                if prof and not prof.startswith("("):
                    current["hsp_profiles"].append(prof)

    if in_bluez and current:
        cards.append(_parse_card(current))

    return cards


def _parse_card(d: dict) -> BtCard:
    return BtCard(
        name=d.get("name", ""),
        active_profile=d.get("active", ""),
        hsphfp_profiles=d.get("hsp_profiles", []),
    )


def switch_bt_to_hsp(card_name: str, prefer_msbc: bool = True) -> Optional[str]:
    """Switch card to best available HSP/HFP profile. Returns the profile activated, or None."""
    cards = list_bt_cards()
    card = next((c for c in cards if c.name == card_name), None)
    if card is None:
        return None

    priority = (
        ["headset-head-unit-msbc", "headset-head-unit-cvsd", "headset-head-unit"]
        if prefer_msbc
        else ["headset-head-unit-cvsd", "headset-head-unit-msbc", "headset-head-unit"]
    )
    for prof in priority:
        if prof in card.hsphfp_profiles:
            r = subprocess.run(
                ["pactl", "set-card-profile", card_name, prof],
                capture_output=True, timeout=5,
            )
            if r.returncode == 0:
                return prof
    return None


def switch_bt_profile(card_name: str, profile: str) -> bool:
    r = subprocess.run(
        ["pactl", "set-card-profile", card_name, profile],
        capture_output=True, timeout=5,
    )
    return r.returncode == 0
