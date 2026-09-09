#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
exec /usr/bin/python3 editor_server.py --open
