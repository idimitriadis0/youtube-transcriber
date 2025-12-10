#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    if len(sys.argv) > 1:
        from app.cli import cli
        cli()
    else:
        try:
            from app.gui import run_gui
            run_gui()
        except ImportError:
            print("Install dependencies: pip install -r requirements.txt")
            sys.exit(1)

if __name__ == "__main__":
    main()
