"""Module entrypoint for `python -m hubctl`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
