#!/usr/bin/env python3
"""
ALPHA OMEGA - GitHub Repository Creator
Creates the repo and pushes all files using GitHub API
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path

# GitHub Token
TOKEN = "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"
REPO_NAME = "THE-ALPHA"
PROJECT_DIR = r"C:\Users\Pince N ClawBot\Desktop\All Desktop\The Alpha"


def create_repo():
    """Create GitHub repository"""
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "name": REPO_NAME,
        "description": "Alpha Omega - Voice-Activated AI Assistant with Full System Control",
        "private": False,
        "has_issues": True,
        "has_projects": True,
        "auto_init": False,
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        print(f"✓ Repository created: {response.json()['html_url']}")
        return response.json()["clone_url"]
    elif response.status_code == 422:
        print("Repository already exists, continuing...")
        return f"https://github.com/PinceNClawBot/{REPO_NAME}.git"
    else:
        print(f"Error creating repo: {response.status_code}")
        print(response.text)
        return None


def init_git():
    """Initialize git repository"""
    os.chdir(PROJECT_DIR)

    # Initialize
    subprocess.run(["git", "init"], shell=True)

    # Configure
    subprocess.run(["git", "config", "user.email", "alpha@omega.local"], shell=True)
    subprocess.run(["git", "config", "user.name", "AlphaOmega"], shell=True)

    # Add all files
    subprocess.run(["git", "add", "."], shell=True)

    # Commit
    commit_msg = """Initial commit - Alpha Omega v2.0.0

Features:
- Voice activation with custom wake word
- Multi-provider LLM support
- Security: malware scanning, voice auth
- Sleep mode operation
- Watch & Learn from tutorials
- Full automation capabilities
- Cross-platform installers"""

    subprocess.run(["git", "commit", "-m", commit_msg], shell=True)

    print("✓ Git initialized and committed")


def push_to_github(clone_url):
    """Push to GitHub"""
    os.chdir(PROJECT_DIR)

    # Add remote
    subprocess.run(
        ["git", "remote", "remove", "origin"], shell=True, capture_output=True
    )
    subprocess.run(["git", "remote", "add", "origin", clone_url], shell=True)

    # Push
    subprocess.run(["git", "branch", "-M", "main"], shell=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], shell=True)

    print("✓ Pushed to GitHub")


def create_release():
    """Create initial release tag"""
    os.chdir(PROJECT_DIR)

    subprocess.run(["git", "tag", "v2.0.0"], shell=True)
    subprocess.run(["git", "push", "origin", "v2.0.0"], shell=True)

    print("✓ Created release tag v2.0.0")


def main():
    print("=" * 50)
    print("ALPHA OMEGA - GitHub Repository Setup")
    print("=" * 50)

    # Create repo
    print("\n[1/4] Creating GitHub repository...")
    clone_url = create_repo()
    if not clone_url:
        sys.exit(1)

    # Init git
    print("\n[2/4] Initializing git...")
    init_git()

    # Push
    print("\n[3/4] Pushing to GitHub...")
    push_to_github(clone_url)

    # Create release
    print("\n[4/4] Creating release...")
    create_release()

    print("\n" + "=" * 50)
    print("SUCCESS!")
    print("=" * 50)
    print(f"\nRepository: https://github.com/PinceNClawBot/{REPO_NAME}")
    print("\nOne-Liner Install Commands:")
    print("-" * 40)
    print("Windows:")
    print(
        "iwr -useb https://raw.githubusercontent.com/PinceNClawBot/THE-ALPHA/main/install.ps1 | iex"
    )
    print("\nmacOS/Linux:")
    print(
        "curl -sSL https://raw.githubusercontent.com/PinceNClawBot/THE-ALPHA/main/install.sh | bash"
    )
    print("\nTermux:")
    print(
        "curl -sSL https://raw.githubusercontent.com/PinceNClawBot/THE-ALPHA/main/install-termux.sh | bash"
    )


if __name__ == "__main__":
    main()
