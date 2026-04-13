#!/bin/bash
# ALPHA OMEGA - Termux (Android) Installer - LITE VERSION
set -e
REPO_OWNER="YOUR_USERNAME"; REPO_NAME="alpha"

echo "╔══════════════════════════════════════════════════╗"
echo "║   ALPHA OMEGA v2.0.0 - Termux Installer         ║"
echo "║   ⚠️ LITE VERSION (reduced features)           ║"
echo "╚══════════════════════════════════════════════════╝"

# Check Termux
[ -z "$TERMUX_VERSION" ] && echo "This script is for Termux only" && exit 1

# Install Python if needed
if ! command -v python &>/dev/null; then
    echo "Installing Python..."
    pkg install python -y
fi

# Create directories
mkdir -p ~/alpha-omega && cd ~/alpha-omega

# Download
echo "Downloading..."
curl -L "https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/heads/main.zip" -o /tmp/a.zip
unzip -q /tmp/a.zip -d /tmp && mv /tmp/alpha*/* . 2>/dev/null || true
rm -rf /tmp/a.zip /tmp/alpha*

# Create venv
python -m venv venv && source venv/bin/activate

# Install lite requirements
echo "Installing lite dependencies..."
pip install --upgrade pip -q
pip install fastapi uvicorn websockets pyyaml requests pydantic -q

# Create config
cat > config.yaml << 'EOF'
system: {name: AlphaOmega, version: "2.0.0", wake_word: "hey alpha", offline_mode: true}
security: {malware_scanning: false, command_whitelist: true}
performance: {work_in_sleep: false, background_tasks: true, cpu_limit: 50}
learning: {watch_mode: false, learn_from_tutorials: false}
termux_mode: true
EOF

echo ""
echo "✓ Installed to ~/alpha-omega"
echo ""
echo "Start with: cd ~/alpha-omega && source venv/bin/activate && python run_alpha.py"
echo "Note: Some features disabled in Termux (no torch/transformers)"
