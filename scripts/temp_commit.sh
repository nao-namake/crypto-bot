#!/bin/bash
cd /Users/nao/Desktop/bot

# Add files
git add init_enhanced.py crypto_bot/main.py

# Commit with message
git commit -m "feat: Phase 2.2 ATR calculation enhancement - API-only mode eradication

- Add enhanced_init_sequence with timeout and retry logic
- Implement proper ATR calculation with fallback values  
- Replace basic INIT-5~INIT-8 with enhanced versions in main.py
- Add yfinance dependency verification
- Implement exponential backoff for data fetching failures

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

# Show status
git status