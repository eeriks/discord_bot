#!/usr/bin/env sh
set -e
isort dbot
black dbot
flake8 dbot
PYTHONPATH="$(python -c "import os.path; print(os.path.realpath('$1'))")/dbot" python -m unittest dbot/tests.py
