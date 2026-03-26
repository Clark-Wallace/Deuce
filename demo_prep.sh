#!/bin/bash
# demo_prep.sh — Clean workspace and prep for a demo recording
#
# Run this before recording the Deuce demo video.
# It clears the workspace so the file browser starts empty
# and the demo shows files appearing from nothing.

set -e

WORKSPACE="./workspace"

echo "Cleaning workspace for demo..."

# Remove everything except .gitkeep
find "$WORKSPACE" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true

echo "Workspace clean."
echo ""
echo "Demo script:"
echo "  1. python app.py"
echo "  2. Type: Build a Python weather CLI with colored output and tests"
echo "  3. Watch the ledger, file browser, and chat"
echo "  4. Click a file to preview it"
echo "  5. Wait for tests to run (hope for a failure-fix cycle!)"
echo ""
echo "Ready to record."
