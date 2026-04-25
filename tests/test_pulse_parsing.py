"""Parse pactl output into structured PaSource / BtCard records."""
from app import pulse

PACTL_LIST_SOURCES = """\
Source #0
\tState: SUSPENDED
\tName: alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
\tDescription: Monitor of Built-in Audio Analog Stereo
Source #1
\tState: RUNNING
\tName: alsa_input.usb-Generic_USB_Microphone-00.mono-fallback
\tDescription: USB Microphone
Source #2
\tState: SUSPENDED
\tName: bluez_input.AA_BB_CC_DD_EE_FF.0
\tDescription: Pixel Buds
\tProperties:
\t\tdevice.bus = "bluez"
"""


PACTL_LIST_CARDS = """\
Card #0
\tName: alsa_card.pci-0000_00_1f.3
\tProfiles:
\t\toutput:analog-stereo: Analog Stereo Output (priority: 6500, available: yes)
\tActive Profile: output:analog-stereo
Card #1
\tName: bluez_card.AA_BB_CC_DD_EE_FF
\tProfiles:
\t\ta2dp-sink: High Fidelity Playback (A2DP Sink) (priority: 40, available: yes)
\t\theadset-head-unit-msbc: Headset Head Unit (HSP/HFP, codec mSBC) (priority: 30, available: yes)
\t\theadset-head-unit-cvsd: Headset Head Unit (HSP/HFP, codec CVSD) (priority: 20, available: yes)
\tActive Profile: a2dp-sink
"""


def test_list_pa_sources_drops_monitors_and_flags_bluetooth(monkeypatch) -> None:
    monkeypatch.setattr(pulse, "_run", lambda cmd: PACTL_LIST_SOURCES)
    sources = pulse.list_pa_sources()
    names = [s.name for s in sources]
    # Monitor sources are filtered out.
    assert all(not n.endswith(".monitor") for n in names)
    # USB mic and BT mic both surface; only the BT one is flagged.
    bt = [s for s in sources if s.is_bluetooth]
    non_bt = [s for s in sources if not s.is_bluetooth]
    assert len(bt) == 1 and "bluez_input" in bt[0].name
    assert len(non_bt) == 1 and "USB" in non_bt[0].description


def test_list_bt_cards_collects_hsp_profiles(monkeypatch) -> None:
    monkeypatch.setattr(pulse, "_run", lambda cmd: PACTL_LIST_CARDS)
    cards = pulse.list_bt_cards()
    assert len(cards) == 1
    card = cards[0]
    assert card.name == "bluez_card.AA_BB_CC_DD_EE_FF"
    assert card.active_profile == "a2dp-sink"
    assert "headset-head-unit-msbc" in card.hsphfp_profiles
    assert "headset-head-unit-cvsd" in card.hsphfp_profiles
