#!/bin/bash
# Build a diagnostic PHOKHARA variant without touching the production build:
#
#   ./build.sh <tag> <patch> [<patch> ...]     e.g. ./build.sh h1h2 h1.patch h2.patch
#
# Each patch is a unified diff against src/ (paths a/<file>, b/<file>; see h1.patch).
# The patched files are copied to build_<tag>/, compiled there, and linked with the
# unpatched production objects of src/ into src/phokhara_<tag>. src/ itself is not
# modified, so phokhara / phokhara_nostop and their objects stay as they are.
# Run a variant with EXE=<path> in RUN_PHOKHARA/submit.sh.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../src"
TAG=${1:?usage: $0 <tag> <patch>...}; shift
[ $# -ge 1 ] || { echo "usage: $0 <tag> <patch>..." >&2; exit 1; }
B="$HERE/build_$TAG"; rm -rf "$B"; mkdir -p "$B"
FFLAGS="-O2 -fPIC -ff2c -std=legacy"

# files touched by the patches, copied once, then all patches applied in order
files=$(grep -h '^+++ b/' "$@" | sed 's#^+++ b/##; s#[[:space:]].*##' | sort -u)
for f in $files; do mkdir -p "$B/$(dirname "$f")"; cp "$SRC/$f" "$B/$f"; done
for p in "$@"; do patch -s -p1 -d "$B" < "$HERE/$(basename "$p")"; done

# compile each patched file (include paths as for the original location)
objs=()
for f in $files; do
    o="$B/${f%.f}.o"
    gfortran $FFLAGS -I"$SRC/$(dirname "$f")" -I"$SRC" -c "$B/$f" -o "$o"
    objs+=("${f%.f}.o=$o")
done

# production link line, with the patched objects substituted
link=$(grep -m1 '^gfortran -o phokhara_nostop ' "$SRC/build_nostop.log")
link=${link/gfortran -o phokhara_nostop /gfortran -o $SRC/phokhara_$TAG }
for pair in "${objs[@]}"; do orig=${pair%%=*}; new=${pair#*=}
    [[ " $link " == *" $orig "* ]] || { echo "object $orig not in the link line" >&2; exit 1; }
    link=${link/ $orig / $new }
done
(cd "$SRC" && eval "$link")
{ echo "$(date -Is) phokhara_$TAG = phokhara_nostop + $*"; for p in "$@"; do grep '^[-+][^-+]' "$HERE/$(basename "$p")" | tr -d '\r'; done; } > "$SRC/phokhara_$TAG.info"
echo "[build] $SRC/phokhara_$TAG  ($*)"
