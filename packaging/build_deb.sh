#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/native_app_release"
PKG_ROOT="$ROOT_DIR/build/deb/manual-notes-compiler"
DIST_DIR="$ROOT_DIR/dist"
VERSION="0.1.0"
ARCH="$(dpkg --print-architecture)"

CC="${CC:-/usr/bin/gcc}" CXX="${CXX:-/usr/bin/g++}" \
  cmake -S "$ROOT_DIR/native_app" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR" --parallel

rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/DEBIAN" "$PKG_ROOT/usr/bin" "$PKG_ROOT/usr/share/applications" "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps"
install -m 0755 "$BUILD_DIR/manual-notes-compiler" "$PKG_ROOT/usr/bin/manual-notes-compiler"
install -m 0644 "$ROOT_DIR/assets/logo_dropzone/manual-notes-compiler.svg" "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps/manual-notes-compiler.svg"

cat > "$PKG_ROOT/DEBIAN/control" <<CONTROL
Package: manual-notes-compiler
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: libc6, libstdc++6, libqt5widgets5, libqt5gui5, libqt5core5a, libqt5svg5, libgl1, poppler-utils
Maintainer: Swaraj
Description: Manual PDF lecture notes compiler
 A native desktop app for reviewing screenshot-based lecture PDFs,
 selecting/rejecting pages, toggling inversion, and rendering 1/2/4-up
 printable PDF outputs.
CONTROL

install -m 0644 "$ROOT_DIR/packaging/manual-notes-compiler.desktop" "$PKG_ROOT/usr/share/applications/manual-notes-compiler.desktop"

mkdir -p "$DIST_DIR"
dpkg-deb --build "$PKG_ROOT" "$DIST_DIR/manual-notes-compiler_${VERSION}_${ARCH}.deb"
echo "$DIST_DIR/manual-notes-compiler_${VERSION}_${ARCH}.deb"
