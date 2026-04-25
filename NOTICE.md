# Third-Party Notices

LinParakeet itself is licensed under the **MIT License** (see `LICENSE`).
The dependencies below ship under their own licenses. LGPL-3.0 dependencies
(PySide6, pynput) are used as libraries via `pip install`, which is the
mode of use LGPL permits from non-LGPL applications.

## Runtime dependencies

| Component | License | Notes |
|-----------|---------|-------|
| [PySide6](https://doc.qt.io/qtforpython/) | LGPL-3.0 | Qt for Python; UI framework. Used as a library. |
| [NVIDIA NeMo toolkit](https://github.com/NVIDIA/NeMo) | Apache-2.0 | ASR framework. |
| NVIDIA **Parakeet-TDT** model weights (`nvidia/parakeet-tdt-0.6b-v2`, `0.6b-v3`, `1.1b`) | [CC-BY-4.0](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) | Attribution required. Model card: Hugging Face. |
| [PyTorch](https://pytorch.org/) | BSD-3-Clause | Pulled in by NeMo. |
| [sounddevice](https://python-sounddevice.readthedocs.io/) | MIT | Audio I/O. |
| [NumPy](https://numpy.org/) | BSD-3-Clause | |
| [SciPy](https://scipy.org/) | BSD-3-Clause | WAV writing. |
| [pynput](https://github.com/moses-palmer/pynput) | LGPL-3.0 | Global hotkey listener. Used as a library. |
| [pyperclip](https://github.com/asweigart/pyperclip) | BSD-3-Clause | Clipboard. |
| `xdotool`, `ydotool`, `xclip`, `wl-copy` | system-provided | Used via `subprocess`; their own licenses apply. |

## Attribution

This project uses the **Parakeet-TDT** speech recognition model by NVIDIA,
released under CC-BY-4.0. See the model card on Hugging Face for full details:
<https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2>.

## On the LGPL libraries (PySide6, pynput)

LGPL-3.0 permits an application under any license to link against LGPL
libraries provided the user can replace the LGPL component with a modified
version. When LinParakeet is installed via `pip` into a virtualenv, this
requirement is trivially met: the user can replace PySide6 / pynput in the
venv with their own build at any time. If you ever redistribute LinParakeet
as a frozen bundle (PyInstaller, AppImage, etc.), you should either:

- ship the LGPL libraries dynamically (so they can still be swapped), or
- include their source (or a written offer to provide it) alongside the bundle.

## Forking under a different license

You can fork this code and release your fork under any license **compatible
with MIT** — that includes proprietary. You just can't remove attribution
required by the dependencies (this NOTICE file, the Parakeet CC-BY-4.0
attribution, and the LGPL notices PySide6/pynput ship with themselves).
