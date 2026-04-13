@echo off
REM ALPHA OMEGA - GitHub Push Script
REM Run this script to push to GitHub

cd /d "C:\Users\Pince N ClawBot\Desktop\All Desktop\The Alpha"

echo Setting up git...
git init
git config user.email "alpha@omega.local"
git config user.name "AlphaOmega"

echo Adding all files...
git add .

echo Committing...
git commit -m "Initial commit - Alpha Omega v2.0.0

Features:
- Voice activation with custom wake word
- Multi-provider LLM support (OpenAI, Anthropic, Google, Groq, local)
- Security: malware scanning, voice auth, Windows login bypass
- Sleep mode operation
- Watch & Learn from tutorials
- Full automation: GUI, files, web, system commands
- Screen analysis with OCR
- Gaming integration
- 10-category settings UI
- Cross-platform installers (Windows, macOS, Linux, Termux)

One-liner install:
Windows: iwr -useb https://raw.githubusercontent.com/YOUR_USERNAME/THE-ALPHA/main/install.ps1 | iex
"

echo Creating GitHub remote...
git remote add origin https://github.com/PinceNClawBot/THE-ALPHA.git

echo Pushing to GitHub...
git branch -M main
git push -u origin main

echo.
echo ========================================
echo Creating release tag v2.0.0...
git tag v2.0.0
git push origin v2.0.0

echo.
echo ========================================
echo SUCCESS! Repository created at:
echo https://github.com/PinceNClawBot/THE-ALPHA
echo.
echo Update the install commands with your actual username:
echo   - install.ps1
echo   - install.sh
echo   - install-termux.sh
echo   - README_INSTALL.md
echo ========================================

pause
