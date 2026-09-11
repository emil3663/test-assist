#!/usr/bin/env bash
#
# Build the Test Assist desktop app into a macOS application bundle.
#
#     ./build.sh              build into dist/Test Assist.app
#     ./build.sh --zip        also produce dist/TestAssist-<version>-macos.zip
#
# The counterpart to build.ps1, running the same PyInstaller spec - the spec
# is platform-aware, so a Mac build and a Windows build come from one source
# of truth for what goes into them.
#
# The result is NOT signed or notarised. Gatekeeper will refuse to open it on
# any machine it was not built on, and the first launch needs right-click ->
# Open (or System Settings -> Privacy & Security -> Open Anyway). Signing
# needs a paid Apple Developer account, so it is a deliberate omission rather
# than an oversight; see README.
set -euo pipefail

ZIP=0
for arg in "$@"; do
    case "$arg" in
        --zip) ZIP=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "build.sh builds the macOS bundle; use build.ps1 on Windows." >&2
    exit 1
fi

# Prefer the repo venv, so the build matches what you run from source.
python="$here/../.venv/bin/python"
[ -x "$python" ] || python="$(command -v python3)"
echo "==> python: $python"

if ! "$python" -m PyInstaller --version >/dev/null 2>&1; then
    # Not installed for you: a venv made by uv has no pip at all, so
    # "python -m pip install" is not a thing that can be assumed to work.
    echo "PyInstaller is not installed in $python" >&2
    echo "  pip:  $python -m pip install pyinstaller" >&2
    echo "  uv:   uv pip install --python $python pyinstaller" >&2
    exit 1
fi

version="$(sed -n 's/^__version__ *= *"\(.*\)"/\1/p' main.py)"
echo "==> building Test Assist $version"

rm -rf build "dist/Test Assist.app"
"$python" -m PyInstaller --noconfirm TestAssist.spec

app="dist/Test Assist.app"
[ -d "$app" ] || { echo "build produced no .app at $app" >&2; exit 1; }

# Verify the bundle actually runs, the way build.ps1 does. --selftest exits
# non-zero on a broken bundle, which is the failure a zip would otherwise
# hide until someone downloaded it.
echo "==> verifying the bundle"
"$app/Contents/MacOS/TestAssist" --selftest >/dev/null
echo "    selftest OK"

# The name in the menu bar comes from here, so it is worth asserting rather
# than assuming - this is the whole reason the bundle exists.
name="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "$app/Contents/Info.plist")"
[ "$name" = "Test Assist" ] || { echo "CFBundleName is '$name', expected 'Test Assist'" >&2; exit 1; }
echo "    CFBundleName: $name"

if [ "$ZIP" = "1" ]; then
    zip_path="dist/TestAssist-$version-macos.zip"
    rm -f "$zip_path"
    # ditto rather than zip: it preserves the resource forks and symlinks a
    # .app relies on, which a plain zip silently flattens.
    ditto -c -k --sequesterRsrc --keepParent "$app" "$zip_path"
    echo "==> $zip_path ($(du -h "$zip_path" | cut -f1))"
fi

echo "==> done: $app"
