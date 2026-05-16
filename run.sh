#!/usr/bin/env bash
# Quick launcher for YT-DLP Downloader
set -e

echo "🔍 Installing dependencies from pyproject.toml…"
pip install -e . --quiet

echo "🚀 Launching YT-DLP Downloader…"
python app.py
