"""
Shared terminal-preview helpers for the plot_*.py scripts in this directory.

Renders a PNG/PDF directly in the terminal so plots can be inspected over SSH
without pulling the PDF to a local machine. Tries, in order:
  1. iTerm2's native inline-image protocol (OSC 1337) -- exact pixels.
  2. term-image (auto-detects Kitty/Sixel graphics protocols).
  3. A lossy half-block ANSI-art renderer that works in any color terminal.

Adapted from ../plot_histos.py.
"""
import base64
import os
import shutil
import sys

from PIL import Image

try:
    from term_image.image import AutoImage
    _HAVE_TERM_IMAGE = True
except ImportError:
    _HAVE_TERM_IMAGE = False


def render_iterm2_inline(image_path, width=None):
    """Push an image straight to iTerm2 via its native inline-image escape sequence."""
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    name_b64 = base64.b64encode(os.path.basename(image_path).encode()).decode("ascii")
    args = [f"name={name_b64}", f"size={len(data)}", "inline=1", "preserveAspectRatio=1"]
    if width:
        args.append(f"width={width}")
    osc = f"\x1b]1337;File={';'.join(args)}:{b64}\x07"
    if os.environ.get("TMUX"):
        osc = "\x1bPtmux;" + osc.replace("\x1b", "\x1b\x1b") + "\x1b\\"
    sys.stdout.write(osc + "\n")
    sys.stdout.flush()


def _to_256(rgb):
    """Map an (r,g,b) triple to the nearest xterm-256 color index."""
    r, g, b = rgb

    def channel(v):
        return 0 if v < 48 else 1 if v < 115 else 2 + (v - 35) * 5 // 220

    if max(r, g, b) - min(r, g, b) < 10:
        gray = round((r + g + b) / 3)
        return 232 + max(0, min(23, (gray - 8) // 10))
    ri, gi, bi = (min(5, max(0, channel(v))) for v in (r, g, b))
    return 16 + 36 * ri + 6 * gi + bi


def _render_block_preview(image_path, max_width, max_height):
    """Render a PNG/JPEG as half-block ANSI art directly to stdout."""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    scale = min(max_width / w, max_height / h, 1.0)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    if new_h % 2:
        new_h -= 1
    new_h = max(2, new_h)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    px = img.load()

    truecolor = os.environ.get("COLORTERM", "") in ("truecolor", "24bit")
    out = []
    for y in range(0, new_h, 2):
        row = []
        for x in range(new_w):
            top = px[x, y]
            bot = px[x, y + 1]
            if truecolor:
                row.append(f"\x1b[38;2;{top[0]};{top[1]};{top[2]}m"
                            f"\x1b[48;2;{bot[0]};{bot[1]};{bot[2]}m▀")
            else:
                row.append(f"\x1b[38;5;{_to_256(top)}m\x1b[48;5;{_to_256(bot)}m▀")
        row.append("\x1b[0m")
        out.append("".join(row))
    sys.stdout.write("\n".join(out) + "\n")


MINI_WIDTH = 60
MINI_HEIGHT = 30


def render_ansi_preview(image_path, max_width=None, max_height=None):
    """Render a small thumbnail preview of a PNG/JPEG in the terminal, trying
    the best available protocol. Deliberately kept mini (a few dozen
    columns/rows) rather than filling the screen -- pass explicit
    max_width/max_height to override."""
    term_cols, term_lines = shutil.get_terminal_size(fallback=(100, 40))
    width = max_width or min(MINI_WIDTH, term_cols)
    height = max_height or min(MINI_HEIGHT, term_lines - 2)

    if sys.stdout.isatty():
        try:
            render_iterm2_inline(image_path, width=width)
            return
        except Exception:
            pass

    if _HAVE_TERM_IMAGE:
        try:
            image = AutoImage.from_file(image_path, width=width)
            image.draw()
            return
        except Exception:
            pass

    _render_block_preview(image_path, width, height * 2)


def pdf_to_png(pdf_path, out_png, dpi=150):
    """Rasterize page 1 of a PDF to PNG via pdftoppm (poppler-utils)."""
    prefix = os.path.splitext(out_png)[0]
    rc = os.system(f"pdftoppm -png -r {dpi} -singlefile '{pdf_path}' '{prefix}' >/dev/null 2>&1")
    if rc != 0 or not os.path.exists(out_png):
        raise RuntimeError(f"pdftoppm failed to rasterize {pdf_path}")


def preview_pdf(pdf_path, dpi=150):
    """Rasterize a PDF's first page and print it directly to the terminal."""
    if not os.path.exists(pdf_path):
        print(f"⚠️  preview skipped: {pdf_path} not found")
        return
    tmp_png = os.path.join(
        os.environ.get("TMPDIR", "/tmp"),
        f"_preview_{os.path.basename(pdf_path)}.png",
    )
    try:
        pdf_to_png(pdf_path, tmp_png, dpi=dpi)
        render_ansi_preview(tmp_png)
    finally:
        if os.path.exists(tmp_png):
            os.remove(tmp_png)
