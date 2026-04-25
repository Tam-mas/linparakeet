# LinParakeet

A **fully local, fully private** Linux voice-to-text tray app powered by
NVIDIA **Parakeet STT**. Hold a hotkey, speak, and the transcript is
copied to your clipboard and auto-pasted into the currently focused window.

- System-tray app, auto-starts on login
- **100% on-device inference** — no cloud, no API keys, no telemetry
- Downloads the Parakeet model once on first run, then runs fully offline
- Bluetooth headsets supported with automatic A2DP ↔ HSP/HFP profile switching
- Multi-GPU aware — loads on the GPU with the most free VRAM
- CPU fallback when every GPU is full (with an OOM retry at runtime)
- Remappable hotkey, toggle **or** hold-to-record mode, microphone picker, optional completion chime

## Privacy

LinParakeet is designed so your voice never leaves your machine.

- **No cloud.** Transcription runs entirely through a local copy of NVIDIA's
  Parakeet model using the NeMo toolkit. There is no speech-to-text API call,
  no background upload, and no account.
- **No telemetry.** The app makes no outbound network requests during normal
  use. You can verify this with `ss -tnp` / `nethogs` while recording.
- **Audio is ephemeral.** Recordings are held in RAM as a NumPy array, written
  briefly to a temp WAV for the model to read, and deleted as soon as
  transcription finishes. No history is kept on disk.
- **Clipboard stays local.** The transcript is placed on your system clipboard
  and pasted into the window you were focused on — nothing more.
- **One exception:** the **first launch** downloads the Parakeet model weights
  (~600 MB) from Hugging Face. After that, you can unplug Ethernet/Wi-Fi and
  it will keep working. You can pre-download the model manually and place it
  in `~/.cache/torch/NeMo/` for a completely offline install.

Settings live at `~/.config/linparakeet/settings.json`; nothing else is
persisted long-term. Audio temp files are written briefly under
`~/.cache/linparakeet/audio/` (mode `0700`) and unlinked the instant
transcription finishes; LinParakeet also wipes that directory on every
startup, so even a crash or `kill -9` mid-transcription cannot leave
recordings on disk past the next launch.

### Trust footnotes

- **Global key listening (pynput).** To detect the hotkey from any window,
  LinParakeet installs a system-wide keyboard listener. It inspects every
  keypress only long enough to ask "is this the hotkey?" and discards
  everything else; nothing is stored, logged, or sent. The mechanism is the
  same one any global-hotkey tool needs on Linux — but it is what it is, so
  it's worth disclosing.
- **Auto-paste on Wayland (ydotool).** The Wayland auto-paste path uses
  `ydotool`, which requires the `ydotoold` daemon to have access to
  `/dev/uinput`. That is broad permission to synthesize input events
  system-wide. If you don't want to grant that, leave auto-paste off — the
  transcript is still copied to your clipboard and you can paste it
  yourself.

---

## Install

```bash
./install.sh
```

Installs system deps (portaudio, xdotool, xclip, …), creates a venv at
`~/.local/share/linparakeet/venv`, pip-installs requirements, writes a launcher
to `~/.local/bin/linparakeet`, and adds an autostart entry to
`~/.config/autostart/linparakeet.desktop`.

## Run

```bash
linparakeet
```

The first launch downloads the Parakeet model (~600 MB). A progress dialog
appears while loading.

## Usage

- **Default hotkey:** hold **Right Ctrl** for 1 second to start recording, hold
  again for 1 second to stop.
- Transcript is copied to the clipboard and auto-pasted into the previously
  focused window.
- Right-click the tray icon for **Settings**, to toggle chime / auto-paste, or
  to **Quit**.

## Settings

| Section | Options |
|---------|---------|
| General | chime on/off, auto-paste on/off, launch at login, model selector |
| Hotkey  | remappable key, toggle vs hold-to-record, hold duration |
| Audio   | microphone picker (🎧 = Bluetooth), custom chime WAV |

Settings are stored at `~/.config/linparakeet/settings.json`.
Model cache lives under `~/.cache/torch/NeMo/` (managed by NeMo).

## Bluetooth headsets

Bluetooth headphones ship in **A2DP** mode (stereo output, no microphone).
When you select a BT headset as your mic, LinParakeet automatically:

1. Switches the card to HSP/HFP (mSBC preferred) — this exposes the mic.
2. Records.
3. Switches back to A2DP so music / video audio quality returns to normal.

Expect ~1 second of setup delay on the first recording after each profile switch.

## GPU / CPU behavior

At launch, LinParakeet inspects every CUDA device with `torch.cuda.mem_get_info`:

- Needs roughly **3 GB free** for the 0.6B models, **5 GB free** for 1.1B.
- Picks the GPU with the most free VRAM above that threshold.
- If no GPU qualifies, loads on **CPU** and posts a tray notification telling
  you which GPUs were full.

**Runtime OOM fallback:** if a transcription blows up mid-run because some
other app just ate your VRAM, LinParakeet moves the model to CPU, retries the
same clip, and posts a tray notification. The model stays on CPU for the rest
of the session; restart to go back to GPU once memory frees up.

**CPU speed reality check:**
- 0.6B model on CPU: tolerable for short clips (~2–5× real-time)
- 1.1B model on CPU: not recommended for interactive use

## Wayland

X11 is fully supported. On Wayland, global hotkeys and auto-paste rely on
`ydotool` with the right permissions; a warning notification appears at launch
if the session is Wayland.

---

## License

LinParakeet itself is released under the **MIT License** — see [LICENSE](./LICENSE).

Dependencies ship under their own licenses; two of them (**PySide6** and
**pynput**) are LGPL-3.0 and are used as libraries (`pip`-installed into a
virtualenv, which satisfies LGPL's replaceability requirement). See
[NOTICE.md](./NOTICE.md) for the full third-party breakdown, attribution for
the Parakeet model weights (CC-BY-4.0), and what to do if you redistribute
LinParakeet as a frozen bundle.

## Credits

- ASR model: **NVIDIA Parakeet-TDT** (CC-BY-4.0).
  <https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2>
- ASR framework: NVIDIA NeMo (Apache-2.0).
