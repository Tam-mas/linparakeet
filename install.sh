#!/usr/bin/env bash
# LinParakeet installer: system deps, Python venv, autostart entry.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HOME/.local/share/linparakeet/venv"
BIN_DIR="$HOME/.local/bin"
AUTOSTART="$HOME/.config/autostart"
LAUNCHER="$BIN_DIR/linparakeet"
DESKTOP="$AUTOSTART/linparakeet.desktop"
TEMPLATE="$HERE/linparakeet.desktop"

echo "==> Installing system packages (requires sudo)"
if command -v apt-get >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y \
    python3 python3-pip python3-venv \
    portaudio19-dev \
    xdotool xclip \
    libxcb-xinerama0 libxcb-cursor0 \
    libgl1
elif command -v dnf >/dev/null; then
  sudo dnf install -y \
    python3 python3-pip python3-virtualenv \
    portaudio-devel \
    xdotool xclip \
    xcb-util-cursor mesa-libGL
elif command -v pacman >/dev/null; then
  sudo pacman -S --needed --noconfirm \
    python python-pip \
    portaudio \
    xdotool xclip \
    xcb-util-cursor libglvnd
else
  echo "!! Unknown package manager. Install manually: python3, pip, venv, portaudio dev headers, xdotool, xclip, xcb-cursor, libGL."
fi

echo "==> Creating virtualenv at $VENV"
mkdir -p "$(dirname "$VENV")"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Upgrading pip"
pip install --upgrade pip wheel setuptools

echo "==> Installing Python requirements (this may take a while — NeMo is large)"
pip install -r "$HERE/requirements.txt"

echo "==> Writing launcher to $LAUNCHER"
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" "$HERE/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

echo "==> Writing autostart entry to $DESKTOP"
mkdir -p "$AUTOSTART"
# Render the bundled desktop template, substituting the real launcher path so
# install.sh and app/autostart.py stay in lockstep on the entry's contents.
EXEC_LINE_ESCAPED="$(printf '%s' "$LAUNCHER" | sed -e 's/[\/&]/\\&/g')"
sed "s|__EXEC__|$EXEC_LINE_ESCAPED|" "$TEMPLATE" > "$DESKTOP"

echo ""
echo "==> Done."
echo "Run now:       $LAUNCHER"
echo "Autostart:     $DESKTOP"
echo "Settings:      right-click the tray icon"
echo "Uninstall:     $HERE/uninstall.sh"
echo ""
echo "First launch will download the Parakeet model (~600MB)."
