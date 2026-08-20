#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

OUT_PARENT="/output"
OUT_DIR="$OUT_PARENT/app"
NUITKA_OUT_DIR="$ROOT_DIR/build/nuitka-linux"
NUITKA_DIST_DIR=""

# GStreamer elements used by the Wayland PipeWire capture pipeline
# (source/utils/wayland/pipewire_capture.py).
GST_ELEMENTS=(pipewiresrc queue capsfilter videoconvert appsink)

# Libraries dlopen'd at runtime, so nothing links them and Nuitka never sees them.
# libgirepository is the exception: _gi.so does link it, but Nuitka still leaves it
# behind, which would silently fall back to the host copy against our bundled GLib.
RUNTIME_LIBS=(
  libgirepository-1.0.so.1
  libgstreamer-1.0.so.0
  libgstbase-1.0.so.0
  libgstvideo-1.0.so.0
  libgstapp-1.0.so.0
)

# Libraries deliberately resolved from the host instead of bundled:
#  - glibc core: never bundle.
#  - libpipewire/libspa: must match the host's running PipeWire daemon, and libpipewire
#    dlopens its SPA plugins from a compiled-in host path. It links no glib, so there is
#    no conflict with the bundled GLib.
_is_excluded_lib() {
  case "$1" in
    libc.so.*|libm.so.*|libpthread.so.*|libdl.so.*|librt.so.*|ld-linux*|libgcc_s.so.*) return 0 ;;
    libpipewire-0.3.so*|libspa-*) return 0 ;;
  esac
  return 1
}

# Copy an ELF's library dependencies into the dist dir, skipping excluded and existing ones.
_copy_lib_deps() {
  local target="$1"
  local lib
  while read -r lib; do
    [ -e "$lib" ] && _bundle_lib "$lib"
  done < <(ldd "$target" 2>/dev/null | awk '/=> \// {print $3}')
}

# Copy a library into the dist root, together with its own dependencies.
# These arrive from /usr/lib64 with no RUNPATH, so without $ORIGIN they cannot find the
# siblings we place next to them (Nuitka already does this for what it bundles itself).
_bundle_lib() {
  local src="$1"
  local base
  base="$(basename "$src")"
  _is_excluded_lib "$base" && return 0
  [ -e "$NUITKA_DIST_DIR/$base" ] && return 0
  cp -aL "$src" "$NUITKA_DIST_DIR/$base"
  patchelf --set-rpath '$ORIGIN' "$NUITKA_DIST_DIR/$base"
  _copy_lib_deps "$NUITKA_DIST_DIR/$base"
}

if [ "$INSIDE_DOCKER" = "1" ]; then
    echo "Building executable inside Docker with Nuitka..."

    rm -rf "$OUT_DIR" "$NUITKA_OUT_DIR"
    mkdir -p "$OUT_PARENT" "$NUITKA_OUT_DIR"

    python -m nuitka \
      --standalone \
      --enable-plugin=pyside6 \
      --assume-yes-for-downloads \
      --nofollow-import-to=source.utils.os_windows_backend \
      --include-package=gi \
      --include-package=dbus \
      --output-dir="$NUITKA_OUT_DIR" \
      --output-filename=app \
      --include-data-dir="$ROOT_DIR/ImageAssets/UI"=ImageAssets/UI \
      --include-data-dir="$ROOT_DIR/ImageAssets/AppUI"=ImageAssets/AppUI \
      --include-data-files="$ROOT_DIR/ImageAssets/app.png"=ImageAssets/app.png \
      --include-data-files="$ROOT_DIR/version"=version \
      --include-data-files="$ROOT_DIR/source/utils/movement/model.npz"=move_assets/model.npz \
      --include-data-files="$ROOT_DIR/source/utils/wayland/gnome/extension.js"=source/utils/wayland/gnome/extension.js \
      --include-data-files="$ROOT_DIR/source/utils/wayland/gnome/metadata.json"=source/utils/wayland/gnome/metadata.json \
      "$ROOT_DIR/App.py"

    NUITKA_DIST_DIR="$(find "$NUITKA_OUT_DIR" -maxdepth 1 -mindepth 1 -type d -name '*.dist' | head -n 1)"
    if [ -z "$NUITKA_DIST_DIR" ]; then
      echo "ERROR: Nuitka dist directory was not found in $NUITKA_OUT_DIR"
      exit 1
    fi

    # Not bundled by Nuitka for some reason
    XCB_CURSOR_LIB="$(find /usr/lib64 /lib64 /usr/lib /lib -maxdepth 2 -type f -name 'libxcb-cursor.so.0*' 2>/dev/null | head -n 1)"
    if [ -z "$XCB_CURSOR_LIB" ]; then
      echo "ERROR: libxcb-cursor.so.0 was not found in the Docker image"
      exit 1
    fi
    cp -a "$XCB_CURSOR_LIB" "$NUITKA_DIST_DIR/"

    # Typelibs themselves are handled by Nuitka's always-on "gi" plugin, which copies the
    # whole girepository dir and points GI_TYPELIB_PATH at it (only if unset - so do not
    # export GI_TYPELIB_PATH in AppRun, or the plugin's bundle is bypassed).
    echo "=== Bundling runtime libraries (Wayland backend) ==="
    for shlib in "${RUNTIME_LIBS[@]}"; do
      lib_path="$(find /usr/lib64 /lib64 -maxdepth 1 -name "$shlib" 2>/dev/null | head -n 1)"
      if [ -z "$lib_path" ]; then
        echo "ERROR: $shlib was not found in the Docker image"
        exit 1
      fi
      echo "  $shlib"
      _bundle_lib "$lib_path"
    done

    echo "=== Bundling GStreamer plugins (Wayland capture) ==="
    # GStreamer dlopens plugins at runtime; resolve each element to its plugin file.
    GST_DEST="$NUITKA_DIST_DIR/gstreamer-1.0"
    mkdir -p "$GST_DEST"
    for element in "${GST_ELEMENTS[@]}"; do
      plugin_so="$(gst-inspect-1.0 "$element" 2>/dev/null | awk '/^[[:space:]]*Filename/ {print $2; exit}')"
      if [ -z "$plugin_so" ] || [ ! -f "$plugin_so" ]; then
        echo "ERROR: GStreamer element '$element' not found in the Docker image"
        exit 1
      fi
      echo "  $element -> $(basename "$plugin_so")"
      cp -aL "$plugin_so" "$GST_DEST/$(basename "$plugin_so")"
    done

    SCANNER="$(find /usr/libexec/gstreamer-1.0 /usr/lib64/gstreamer-1.0 -name gst-plugin-scanner 2>/dev/null | head -n 1)"
    if [ -z "$SCANNER" ]; then
      echo "ERROR: gst-plugin-scanner was not found in the Docker image"
      exit 1
    fi
    cp -aL "$SCANNER" "$GST_DEST/gst-plugin-scanner"

    for plugin in "$GST_DEST"/*.so "$GST_DEST/gst-plugin-scanner"; do
      _copy_lib_deps "$plugin"
      # Plugins live one level below the bundled libraries; keep resolution self-contained
      # so LD_LIBRARY_PATH stays unset and host subprocesses (qdbus) are unaffected.
      patchelf --set-rpath '$ORIGIN/..' "$plugin"
    done

    cp -a "$NUITKA_DIST_DIR" "$OUT_DIR"

    CA_BUNDLE="$(python -c 'import certifi; print(certifi.where())')"
    if [ ! -r "$CA_BUNDLE" ]; then
      echo "ERROR: certifi CA bundle was not found: $CA_BUNDLE"
      exit 1
    fi
    cp "$CA_BUNDLE" "$OUT_DIR/cacert.pem"
    chmod 644 "$OUT_DIR/cacert.pem"

    chmod +x "$OUT_DIR/app" "$OUT_DIR/gstreamer-1.0/gst-plugin-scanner"
    echo "Nuitka output prepared at $OUT_DIR"
else
    echo "This script is intended to run in Docker with INSIDE_DOCKER=1."
    exit 1
fi
