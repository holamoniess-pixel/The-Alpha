#!/bin/bash
# ALPHA OMEGA - macOS/Linux Uninstaller

INSTALL_DIR="${1:-/opt/alpha-omega}"

echo "ALPHA OMEGA UNINSTALLER"
echo "========================"

read -p "Keep user data? [y/N] " keep
keep_data=$([[ "$keep" =~ ^[Yy] ]] && echo true || echo false)

echo "Stopping processes..."
pkill -f "run_alpha.py" 2>/dev/null || true

echo "Removing auto-start..."
rm -f ~/.config/autostart/alpha-omega.desktop 2>/dev/null
rm -f ~/Library/LaunchAgents/com.alphaomega.plist 2>/dev/null

echo "Removing shortcuts..."
rm -f ~/.local/share/applications/alpha-omega.desktop

echo "Removing files..."
if [[ "$keep_data" == "true" ]]; then
    cd "$INSTALL_DIR" 2>/dev/null && rm -rf src apps .venv assets web plugins *.py *.sh 2>/dev/null
    echo "Data preserved at: $INSTALL_DIR/data"
else
    sudo rm -rf "$INSTALL_DIR"
    echo "All files removed"
fi

echo "✓ Alpha Omega uninstalled"
