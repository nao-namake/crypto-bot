#!/usr/bin/env python3
"""Git commit helper script"""

import os
import subprocess

# Change to bot directory
os.chdir("/Users/nao/Desktop/bot")

# Git status before
print("=== Git status before ===")
subprocess.run(["git", "status"], check=True)

# Add files
print("\n=== Adding files ===")
subprocess.run(["git", "add", "init_enhanced.py", "crypto_bot/main.py"], check=True)

# Commit message
commit_message = """feat: Phase 2.2 ATR calculation enhancement - API-only mode eradication

- Add enhanced_init_sequence with timeout and retry logic
- Implement proper ATR calculation with fallback values  
- Replace basic INIT-5~INIT-8 with enhanced versions in main.py
- Add yfinance dependency verification
- Implement exponential backoff for data fetching failures

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

# Commit
print("\n=== Committing ===")
subprocess.run(["git", "commit", "-m", commit_message], check=True)

# Git status after
print("\n=== Git status after ===")
subprocess.run(["git", "status"], check=True)

# Clean up temporary files
print("\n=== Cleaning up ===")
os.remove("/Users/nao/Desktop/bot/temp_commit.sh")
os.remove("/Users/nao/Desktop/bot/git_commit.py")
print("Temporary files removed.")
