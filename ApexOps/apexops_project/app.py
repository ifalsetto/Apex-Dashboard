import os
import sys

# Ensure project root is on PYTHONPATH for Streamlit runs
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from apexops import dashboard  # noqa: E402


def main():
    # If your dashboard code is top-level (no main()), importing may already run it.
    # If you have/added dashboard.main(), call it.
    if hasattr(dashboard, "main"):
        dashboard.main()


if __name__ == "__main__":
    main()