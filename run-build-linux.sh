#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

APPNAME="CGrinder"
ARCH="x86_64"
APPDIR="$ROOT_DIR/AppDir"
APPIMAGETOOL="$HOME/appimagetool-x86_64.AppImage"
DISTDIR="$ROOT_DIR/dist"
DOCKER_OUTDIR="$ROOT_DIR/.docker_dist"

mkdir -p "$APPDIR/usr/bin"
mkdir -p "$DISTDIR"
rm -rf "$DOCKER_OUTDIR"
mkdir -p "$DOCKER_OUTDIR"

if [ ! -x "$APPIMAGETOOL" ]; then
  echo "ERROR: appimagetool not found or not executable at: $APPIMAGETOOL"
  echo "Download it and run: chmod +x $APPIMAGETOOL"
  exit 1
fi

echo "=== Step 1: Building Docker image ==="
docker build -t cgrinder-builder -f "$ROOT_DIR/release/linux/docker-linux.Dockerfile" "$ROOT_DIR"

echo "=== Step 2: Running Nuitka build inside Docker ==="
docker run --rm \
  -v "$DOCKER_OUTDIR":/output \
  -e INSIDE_DOCKER=1 \
  cgrinder-builder

echo "=== Step 3: Wrapping into AppImage on host ==="

if [ ! -d "$DOCKER_OUTDIR/app" ]; then
  echo "ERROR: Expected Docker build output directory not found: $DOCKER_OUTDIR/app"
  exit 1
fi
if [ ! -r "$DOCKER_OUTDIR/app/cacert.pem" ]; then
  echo "ERROR: Expected CA bundle was not found: $DOCKER_OUTDIR/app/cacert.pem"
  exit 1
fi

rm -rf "$APPDIR/usr/bin"/*
cp -a "$DOCKER_OUTDIR/app"/. "$APPDIR/usr/bin"/

chmod 755 "$APPDIR" "$APPDIR/usr" "$APPDIR/usr/bin"
chmod +x "$APPDIR/AppRun"
if [ -f "$APPDIR/usr/bin/app" ]; then
  chmod +x "$APPDIR/usr/bin/app"
fi

APPIMAGE_EXTRACT_AND_RUN=1 \
  "$APPIMAGETOOL" "$APPDIR" "$DISTDIR/CGrinder-x86_64.AppImage"

chmod +x "$DISTDIR/${APPNAME}-${ARCH}.AppImage"
rm -rf "$DOCKER_OUTDIR"

echo "=== Done! Output: $DISTDIR/CGrinder-x86_64.AppImage ==="
