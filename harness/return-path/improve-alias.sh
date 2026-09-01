#!/usr/bin/env bash
# Return path for terminal/pipeline users. Install: fill LAB_PATH below,
# then source this file from your shell profile (or keep it in your
# scripts folder). Usage:
#   improve "the agent keeps calling our retry helper wrong"
LAB_PATH="{{LAB_PATH}}"

improve() {
  if [ -z "$1" ]; then
    echo "usage: improve \"what you want to improve, in your own words\""
    return 1
  fi
  mkdir -p "$LAB_PATH/workspace/inbox"
  note="$LAB_PATH/workspace/inbox/$(date +%Y%m%d-%H%M)-note.md"
  {
    echo "date: $(date +%Y-%m-%d)"
    echo "from: $(basename "$PWD")"
    echo "goal: $*"
  } > "$note"
  echo "Noted in $note"
  echo "Open your agent in $LAB_PATH and say hello - it will pick this up."
}
