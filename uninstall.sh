#!/usr/bin/env bash
# LinParakeet uninstaller: reverses what install.sh created.
# Leaves system packages alone (apt/dnf/pacman would have to be reverted manually).
set -euo pipefail

VENV="$HOME/.local/share/linparakeet/venv"
VENV_PARENT="$HOME/.local/share/linparakeet"
LAUNCHER="$HOME/.local/bin/linparakeet"
DESKTOP="$HOME/.config/autostart/linparakeet.desktop"
SETTINGS_DIR="$HOME/.config/linparakeet"
AUDIO_CACHE="$HOME/.cache/linparakeet"

remove_user_data="${1:-}"

echo "==> Removing autostart entry"
rm -f "$DESKTOP"

echo "==> Removing launcher"
rm -f "$LAUNCHER"

echo "==> Removing virtualenv at $VENV"
rm -rf "$VENV"
rmdir "$VENV_PARENT" 2>/dev/null || true

echo "==> Removing transient audio cache"
rm -rf "$AUDIO_CACHE"

if [[ "$remove_user_data" == "--purge" ]]; then
  echo "==> Removing settings ($SETTINGS_DIR)"
  rm -rf "$SETTINGS_DIR"
else
  echo "==> Keeping user settings at $SETTINGS_DIR (pass --purge to wipe)"
fi

echo ""
echo "Done. The downloaded Parakeet model under ~/.cache/torch/NeMo/ is left in"
echo "place — delete it manually if you want to reclaim that space."
