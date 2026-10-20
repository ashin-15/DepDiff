#!/bin/sh
# Install depdiff into an isolated virtual environment and expose its command.
#
# The defaults are user-local and do not require sudo. Set PREFIX and VENV_DIR
# explicitly for a system-wide installation.

set -eu

die() {
    printf 'depdiff install: error: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'EOF'
Usage: scripts/install.sh

Install depdiff from this checkout into a virtual environment and link the
depdiff command into a bin directory.

Environment overrides:
  PYTHON_BIN  Python 3.11 executable (default: python3.11)
  PREFIX      Prefix containing bin/ (default: $HOME/.local)
  BIN_DIR     Directory for the depdiff command (default: $PREFIX/bin)
  VENV_DIR    Virtual environment path (default: $HOME/.local/share/depdiff/venv)

Examples:
  PYTHON_BIN=python3.11 PREFIX="$HOME/.local" scripts/install.sh
  sudo env PYTHON_BIN=python3.11 PREFIX=/usr/local \
    VENV_DIR=/opt/depdiff/venv scripts/install.sh
EOF
}

case "${1:-}" in
    "")
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        die "unknown argument '$1' (use --help for usage)"
        ;;
esac

if [ -z "${HOME:-}" ] && { [ -z "${PREFIX:-}" ] || [ -z "${VENV_DIR:-}" ]; }; then
    die 'HOME must be set when PREFIX or VENV_DIR is not provided'
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || die 'could not locate the script'
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || die 'could not locate the repository'

PYTHON_BIN=${PYTHON_BIN:-python3.11}
PREFIX=${PREFIX:-"$HOME/.local"}
BIN_DIR=${BIN_DIR:-"$PREFIX/bin"}
VENV_DIR=${VENV_DIR:-"$HOME/.local/share/depdiff/venv"}

case "$VENV_DIR" in
    /*)
        ;;
    *)
        VENV_DIR="$(pwd)/$VENV_DIR"
        ;;
esac

command -v "$PYTHON_BIN" >/dev/null 2>&1 || die \
    "Python executable '$PYTHON_BIN' was not found; install Python 3.11 or set PYTHON_BIN"

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' \
    >/dev/null 2>&1 || die "'$PYTHON_BIN' is not Python 3.11.x"

if [ -e "$VENV_DIR" ] || [ -L "$VENV_DIR" ]; then
    [ -x "$VENV_DIR/bin/python" ] || die \
        "VENV_DIR '$VENV_DIR' exists but is not a usable virtual environment"
else
    mkdir -p "$(dirname -- "$VENV_DIR")" || die "could not create the parent of '$VENV_DIR'"
    "$PYTHON_BIN" -m venv "$VENV_DIR" || die \
        "could not create '$VENV_DIR'; install the Python 3.11 venv module"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
"$VENV_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' \
    >/dev/null 2>&1 || die "existing virtual environment '$VENV_DIR' is not Python 3.11.x"
"$VENV_PYTHON" -m pip --version >/dev/null 2>&1 || die \
    "virtual environment '$VENV_DIR' has no pip; install the Python 3.11 venv module"

"$VENV_PYTHON" -m pip install \
    --no-index --no-deps --no-build-isolation --no-cache-dir "$REPO_ROOT" || die \
    'could not install depdiff from this checkout'

COMMAND_PATH="$BIN_DIR/depdiff"
[ -e "$COMMAND_PATH" ] && [ ! -L "$COMMAND_PATH" ] && die \
    "refusing to overwrite existing non-symlink '$COMMAND_PATH'"

mkdir -p "$BIN_DIR" || die "could not create '$BIN_DIR'"
TEMP_LINK="$COMMAND_PATH.tmp.$$"
rm -f "$TEMP_LINK"
trap 'rm -f "$TEMP_LINK"' EXIT HUP INT TERM
ln -s "$VENV_DIR/bin/depdiff" "$TEMP_LINK" || die \
    "could not create the command link in '$BIN_DIR'"
mv -f "$TEMP_LINK" "$COMMAND_PATH" || die \
    "could not install the command link at '$COMMAND_PATH'"

printf 'Installed depdiff at %s\n' "$COMMAND_PATH"
case ":${PATH:-}:" in
    *:"$BIN_DIR":*)
        printf 'Run: depdiff --help\n'
        ;;
    *)
        printf 'Add this directory to PATH before running depdiff:\n  export PATH=%s:\$PATH\n' "$BIN_DIR"
        ;;
esac
