#!/bin/bash
# ALPHA OMEGA - macOS/Linux Installer
set -e
REPO_OWNER="holamoniess-pixel"; REPO_NAME="The-Alpha"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
INSTALL_DIR="${1:-/opt/alpha-omega}"

show_banner() {
clear
echo -e "${RED}╔══════════════════════════════════════════════════════════════╗
║     ALPHA OMEGA v2.0.0 (BETA)                                ║
║     ⚠️ WARNING: FULL SYSTEM ACCESS                           ║
║     This software controls your entire computer.            ║
║     By installing, you accept ALL RISKS.                    ║
╚══════════════════════════════════════════════════════════════╝${NC}"
}

check_python() {
    if command -v python3 &>/dev/null; then
        v=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if [[ $(echo "$v >= 3.9" | bc -l) -eq 1 ]]; then echo "✓ Python $v"; return 0; fi
    fi
    echo "⚠ Python 3.9+ required"; return 1
}

install_python() {
    echo "Installing Python..."
    if command -v apt-get &>/dev/null; then sudo apt-get update && sudo apt-get install -y python3.11 python3-pip
    elif command -v dnf &>/dev/null; then sudo dnf install -y python3.11
    elif command -v brew &>/dev/null; then brew install python@3.11
    fi
}

download() {
    echo "Downloading..."
    tmp=$(mktemp -d)
    curl -L "https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/heads/main.zip" -o "$tmp/a.zip"
    unzip -q "$tmp/a.zip" -d "$tmp"
    sudo mkdir -p "$(dirname $INSTALL_DIR)"
    sudo mv "$tmp"/alpha* "$INSTALL_DIR"
    rm -rf "$tmp"
    echo "✓ Downloaded"
}

install_deps() {
    echo "Installing dependencies..."
    cd "$INSTALL_DIR" && python3 -m venv .venv && source .venv/bin/activate
    pip install --upgrade pip -q
    [ -f requirements.txt ] && pip install -r requirements.txt -q
    echo "✓ Dependencies installed"
}

configure() {
    cat > "$INSTALL_DIR/config.yaml" << 'EOF'
system: {name: AlphaOmega, version: "2.0.0", wake_word: "hey alpha", offline_mode: true}
security: {malware_scanning: true, command_whitelist: true}
performance: {work_in_sleep: true, background_tasks: true}
learning: {watch_mode: true}
EOF
}

create_launcher() {
    mkdir -p ~/.local/share/applications
    cat > ~/.local/share/applications/alpha-omega.desktop << EOF
[Desktop Entry]
Name=Alpha Omega
Exec=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/run_alpha.py
Icon=$INSTALL_DIR/assets/icon.png
Type=Application
Categories=Utility;
EOF
}

# MAIN
show_banner
read -p "Accept risks? [Y/n] " a; [[ "$a" =~ ^[Nn] ]] && exit 1
check_python || install_python
download
install_deps
configure
create_launcher
echo -e "${GREEN}✓ Installed to $INSTALL_DIR${NC}"
echo -e "${CYAN}API: http://localhost:8000 | Wake: 'hey alpha'${NC}"
read -p "Start now? [Y/n] " s; [[ "$s" =~ ^[Nn] ]] || { cd "$INSTALL_DIR" && source .venv/bin/activate && nohup python run_alpha.py & }
echo -e "${GREEN}Done! Say 'hey alpha' to activate.${NC}"
