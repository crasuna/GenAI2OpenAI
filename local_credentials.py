"""Read the user's opt-in, git-ignored local credential for verification tools."""
import getpass
import sys
from pathlib import Path


def load_token():
    path = Path(__file__).resolve().parent / 'credentials.txt'
    if path.is_file():
        token = path.read_text(encoding='utf-8-sig').strip()
        if token:
            return token
    if not sys.stdin.isatty():
        raise RuntimeError('No local credential; run interactively to enter one.')
    return getpass.getpass('Paste YOUR GenAI token (hidden), then Enter: ').strip()
