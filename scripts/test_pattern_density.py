"""
Offline prototype: adjust motif spacing *inside* a seamless pattern tile.

Unlike padding whole tiles, this:
  1) separates plate vs ink
  2) finds toroidal (wrap-aware) connected components
  3) moves each motif by scaling its centroid offset from center
  4) rebuilds a new repeat period (smaller = denser, larger = sparser)
  5) keeps motif pixel size unchanged

Usage:
  python scripts/test_pattern_density.py
  python scripts/test_pattern_density.py --inputs path1.png path2.png --spacings 0.65,1.0,1.35
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ASSETS = Path(
    r"C:\Users\levyn\.cursor\projects\c-My-Web-Sites-arye-textile-branding\assets"
)
DEFAULT_IDS = [
    "neutral_patterns_5-36c7dbfa-a039-4be5-bd6a-7e7514f66671",
    "neutral_patterns_10-eae09428-c504-4565-8e0c-002b2041d788",
    "neutral_patterns_9-40013e6d-116c-45ab-9f32-db9a43a4719f",
    "neutral_patterns_11-97d4047d-1ac6-442b-a959-b9e8ad31daf5",
    "neutral_patterns_12-8e975d87-9f1a-4135-9b9c-0f4aa1039243",
    "neutral_patterns_13-6e01be2c-40f4-46f2-a13e-88d33aa5399f",
    "neutral_patterns_1-966b55a5-0beb-4eef-a367-c79f264abc47",
    "neutral_patterns_2-1bc74375-bdd5-45db-89c2-06f1ab273b38",
    "neutral_patterns_4-8cc89819-b41b-42a3-9bfc-9fb5d39ce606",
    "neutral_patterns_3-b7b4e7f3-fd2c-4cf0-921b-8dec5d1598dc",
]


def short_name(path: Path) -> str:
    m = re.search(r"(neutral_patterns_\d+)", path.stem)
    return m.group(1) if m else path.stem[:40]


def find_default_inputs() -> list[Path]:
    found = []
    for token in DEFAULT_IDS:
        matches = sorted(ASSETS.glob(f"*{token}*.png"))
        if matches:
            found.append(matches[0])
    return found


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """rgb uint8 (...,3) -> Lab float."""
    x = rgb.astype(np.float64) / 255.0
    mask = x > 0.04045
    x = np.where(mask, ((x + 0.055) / 1.055) ** 2.4, x / 12.92)
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = x @ m.T
    xyz[..., 0] /= 0.95047
    xyz[..., 2] /= 1.08883
    eps = 216 / 24389
    kappa = 24389 / 27
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def estimate_plate_rgb(rgb: np.ndarray) -> np.ndarray:
    """Dominant color via coarse quantization (plate = majority)."""
    q = (rgb.astype(np.uint16) // 16) * 16 + 8
    flat = q.reshape(-1, 3)
    # pack to single int key
    keys = (
        (flat[:, 0].astype(np.int32) << 16)
        | (flat[:, 1].astype(np.int32) << 8)
        | flat[:, 2].astype(np.int32)
    )
    vals, counts = np.unique(keys, return_counts=True)
    best = int(vals[np.argmax(counts)])
    return np.array([(best >> 16) & 255, (best >> 8) & 255, best & 255], dtype=np.float64)


def ink_mask(rgb: np.ndarray, plate: np.ndarray, lab_thresh: float = 12.0) -> np.ndarray:
    lab = rgb_to_lab(rgb)
    plate_lab = rgb_to_lab(plate.reshape(1, 1, 3))[0, 0]
    dist = np.linalg.norm(lab - plate_lab, axis=-1)
    return dist >= lab_thresh


def morph_close(mask: np.ndarray, radius: int = 2) -> np.ndarray:
    """Binary close with toroidal padding to merge anti-aliased motif fragments."""
    if radius <= 0:
        return mask
    m = mask.astype(bool)
    h, w = m.shape
    # dilate then erode with wrap
    for _ in range(radius):
        padded = np.pad(m, 1, mode="wrap")
        m = (
            padded[:-2, :-2] | padded[:-2, 1:-1] | padded[:-2, 2:]
            | padded[1:-1, :-2] | padded[1:-1, 1:-1] | padded[1:-1, 2:]
            | padded[2:, :-2] | padded[2:, 1:-1] | padded[2:, 2:]
        )
    for _ in range(radius):
        padded = np.pad(m, 1, mode="wrap")
        m = (
            padded[:-2, :-2] & padded[:-2, 1:-1] & padded[:-2, 2:]
            & padded[1:-1, :-2] & padded[1:-1, 1:-1] & padded[1:-1, 2:]
            & padded[2:, :-2] & padded[2:, 1:-1] & padded[2:, 2:]
        )
    # keep only original ink pixels as drawable; closed mask is for grouping only
    return m


def wrap_delta(d: float, period: int) -> float:
    """Shortest signed delta on a circle of length period."""
    half = period * 0.5
    return (d + half) % period - half


def circular_centroid(xs: np.ndarray, ys: np.ndarray, w: int, h: int) -> tuple[float, float]:
    ang_x = 2 * np.pi * xs / w
    ang_y = 2 * np.pi * ys / h
    cx = (np.arctan2(np.sin(ang_x).mean(), np.cos(ang_x).mean()) / (2 * np.pi)) * w
    cy = (np.arctan2(np.sin(ang_y).mean(), np.cos(ang_y).mean()) / (2 * np.pi)) * h
    cx %= w
    cy %= h
    return float(cx), float(cy)


def toroidal_components(mask: np.ndarray, min_pixels: int = 20) -> list[dict]:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    comps: list[dict] = []
    # 8-connected
    neigh = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0, x0] or visited[y0, x0]:
                continue
            q = deque([(x0, y0)])
            visited[y0, x0] = True
            xs: list[int] = []
            ys: list[int] = []
            while q:
                x, y = q.popleft()
                xs.append(x)
                ys.append(y)
                for dx, dy in neigh:
                    nx = (x + dx) % w
                    ny = (y + dy) % h
                    if mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        q.append((nx, ny))
            if len(xs) < min_pixels:
                continue
            xa = np.asarray(xs, dtype=np.int32)
            ya = np.asarray(ys, dtype=np.int32)
            cx, cy = circular_centroid(xa, ya, w, h)
            comps.append({"xs": xa, "ys": ya, "cx": cx, "cy": cy})
    return comps


def adjust_spacing(
    rgba: np.ndarray,
    spacing: float,
    lab_thresh: float = 12.0,
    min_pixels: int = 20,
) -> tuple[np.ndarray, dict]:
    """
    spacing < 1 → denser (smaller period, motifs closer in absolute px)
    spacing = 1 → original
    spacing > 1 → sparser (larger period)
    Motif shapes keep their pixel size; only centroid layout + period change.
    """
    h, w = rgba.shape[:2]
    rgb = rgba[..., :3]
    plate = estimate_plate_rgb(rgb)
    raw_mask = ink_mask(rgb, plate, lab_thresh=lab_thresh)
    # Close for grouping (merge leaflets / AA gaps); draw using raw ink only
    group_mask = morph_close(raw_mask, radius=2)
    comps = toroidal_components(group_mask, min_pixels=min_pixels)
    # Restrict each component's drawable pixels to real ink
    for comp in comps:
        keep = raw_mask[comp["ys"], comp["xs"]]
        if not np.any(keep):
            comp["xs"] = comp["xs"][:0]
            comp["ys"] = comp["ys"][:0]
            continue
        comp["xs"] = comp["xs"][keep]
        comp["ys"] = comp["ys"][keep]
        comp["cx"], comp["cy"] = circular_centroid(comp["xs"], comp["ys"], w, h)
    comps = [c for c in comps if len(c["xs"]) >= min_pixels]
    mask = raw_mask

    meta = {
        "components": len(comps),
        "plate": tuple(int(v) for v in plate),
        "src": (w, h),
        "spacing": spacing,
        "ink_frac": float(mask.mean()),
    }

    if abs(spacing - 1.0) < 1e-3 or not comps:
        meta["out"] = (w, h)
        return rgba.copy(), meta

    new_w = max(32, int(round(w * spacing)))
    new_h = max(32, int(round(h * spacing)))
    meta["out"] = (new_w, new_h)

    out = np.zeros((new_h, new_w, 4), dtype=np.uint8)
    out[..., 0] = int(plate[0])
    out[..., 1] = int(plate[1])
    out[..., 2] = int(plate[2])
    out[..., 3] = 255

    cx0 = w * 0.5
    cy0 = h * 0.5
    ncx0 = new_w * 0.5
    ncy0 = new_h * 0.5

    for comp in comps:
        old_cx, old_cy = comp["cx"], comp["cy"]
        dx = wrap_delta(old_cx - cx0, w)
        dy = wrap_delta(old_cy - cy0, h)
        new_cx = (ncx0 + dx * spacing) % new_w
        new_cy = (ncy0 + dy * spacing) % new_h

        xs = comp["xs"].astype(np.float64)
        ys = comp["ys"].astype(np.float64)
        ox = (xs - old_cx + w * 0.5) % w - w * 0.5
        oy = (ys - old_cy + h * 0.5) % h - h * 0.5
        # keep motif size — do not scale ox/oy
        nx = np.rint(new_cx + ox).astype(np.int32) % new_w
        ny = np.rint(new_cy + oy).astype(np.int32) % new_h
        out[ny, nx] = rgba[comp["ys"], comp["xs"]]
        out[ny, nx, 3] = 255

    return out, meta


def make_fixed_window_preview(
    tile_rgba: np.ndarray, window: int = 1536, cell_motif_scale: float = 1.0
) -> np.ndarray:
    """
    Tile the (possibly resized-period) pattern into a fixed window at native
    pixel scale so denser periods show more motifs in the same area.
    """
    th, tw = tile_rgba.shape[:2]
    # optional uniform scale of the whole preview for readability
    if abs(cell_motif_scale - 1.0) > 1e-3:
        tw2 = max(8, int(round(tw * cell_motif_scale)))
        th2 = max(8, int(round(th * cell_motif_scale)))
        img = Image.fromarray(tile_rgba, "RGBA").resize((tw2, th2), Image.Resampling.NEAREST)
        tile_rgba = np.asarray(img)
        th, tw = tile_rgba.shape[:2]

    out = np.zeros((window, window, 4), dtype=np.uint8)
    # cover window
    y = 0
    while y < window:
        x = 0
        while x < window:
            y2 = min(window, y + th)
            x2 = min(window, x + tw)
            out[y:y2, x:x2] = tile_rgba[: y2 - y, : x2 - x]
            x += tw
        y += th
    return out


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def spacing_label(spacing: float) -> str:
    if abs(spacing - 1.0) < 1e-3:
        return f"original  spacing={spacing:.2f}"
    if spacing < 1.0:
        return f"DENSE  spacing={spacing:.2f}  (more motifs, same size)"
    return f"SPARSE  spacing={spacing:.2f}  (fewer motifs, same size)"


def labeled_panel(img_rgb: Image.Image, title: str, subtitle: str, panel: int) -> Image.Image:
    """Resize preview into a fixed panel with a caption bar (fair side-by-side)."""
    bar_h = 64
    canvas = Image.new("RGB", (panel, panel + bar_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, panel, bar_h], fill=(32, 32, 32))
    font = load_font(18)
    font_sm = load_font(14)
    draw.text((12, 10), title, fill=(255, 255, 255), font=font)
    draw.text((12, 36), subtitle, fill=(200, 200, 200), font=font_sm)
    fitted = img_rgb.resize((panel, panel), Image.Resampling.BILINEAR)
    canvas.paste(fitted, (0, bar_h))
    return canvas


def make_compare_strip(
    windows: list[tuple[float, np.ndarray, dict]],
    panel: int = 640,
) -> Image.Image:
    """
    Fair comparison: every column shows the SAME fabric window size,
    motifs at native 1:1 pixel scale (same motif size). Only count/spacing change.
    """
    panels = []
    for spacing, win, meta in windows:
        title = spacing_label(spacing)
        ow, oh = meta.get("out", ("?", "?"))
        subtitle = f"repeat period {ow}x{oh}px | motifs kept at original pixel size"
        panels.append(labeled_panel(Image.fromarray(win, "RGBA").convert("RGB"), title, subtitle, panel))
    gap = 12
    w = sum(p.width for p in panels) + gap * (len(panels) - 1)
    h = panels[0].height if panels else panel
    strip = Image.new("RGB", (w, h), (255, 255, 255))
    x = 0
    for p in panels:
        strip.paste(p, (x, 0))
        x += p.width + gap
    return strip


def load_rgba(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGBA")
    # Cap huge inputs for prototype speed
    max_side = 1024
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return np.asarray(img)


def process_one(
    path: Path,
    out_dir: Path,
    spacings: list[float],
    window: int,
    panel: int,
) -> dict:
    rgba = load_rgba(path)
    name = short_name(path)
    print(f"\n=== {name}  src={rgba.shape[1]}x{rgba.shape[0]} ===")

    compare_rows: list[tuple[float, np.ndarray, dict]] = []

    for spacing in spacings:
        tile, meta = adjust_spacing(rgba, spacing)
        tag = f"s{int(round(spacing * 100)):03d}"
        print(
            f"  {tag}: comps={meta['components']} plate={meta['plate']} "
            f"ink={meta['ink_frac']:.3f} period {meta['src']} -> {meta['out']}"
        )
        # Raw period tile (debug only — do NOT judge density from this alone)
        Image.fromarray(tile, "RGBA").save(out_dir / f"{name}_{tag}_tile_DEBUG.png")

        # Fair preview: fixed fabric window, native motif scale
        win = make_fixed_window_preview(tile, window=window)
        Image.fromarray(win, "RGBA").save(out_dir / f"{name}_{tag}_SAME_SIZE.png")
        compare_rows.append((spacing, win, meta))

    strip = make_compare_strip(compare_rows, panel=panel)
    compare_path = out_dir / f"{name}_COMPARE.png"
    strip.save(compare_path)
    print(f"  COMPARE -> {compare_path.name}")
    return {"name": name, "compare": compare_path.name, "spacings": spacings}


def write_gallery_html(out_dir: Path, results: list[dict], spacings: list[float]) -> Path:
    rows_html = []
    for r in results:
        name = r["name"]
        imgs = []
        for spacing in spacings:
            tag = f"s{int(round(spacing * 100)):03d}"
            src = f"{name}_{tag}_SAME_SIZE.png"
            label = html.escape(spacing_label(spacing))
            imgs.append(
                f'<figure><img src="{html.escape(src)}" alt="{label}"/>'
                f"<figcaption>{label}</figcaption></figure>"
            )
        rows_html.append(
            f'<section class="pattern">'
            f"<h2>{html.escape(name)}</h2>"
            f'<p class="hint">Same crop size · same motif pixel size · only spacing/count changes</p>'
            f'<div class="row">{"".join(imgs)}</div>'
            f'<p><a href="{html.escape(r["compare"])}">Open labeled strip</a></p>'
            f"</section>"
        )

    doc = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8"/>
<title>Pattern density preview — fair comparison</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f6f6f6; color: #222; }}
  h1 {{ font-size: 1.4rem; }}
  .note {{ background: #fff3cd; border: 1px solid #e0c36a; padding: 12px 16px; border-radius: 8px; max-width: 1100px; }}
  .pattern {{ background: #fff; margin: 28px 0; padding: 16px; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .hint {{ color: #666; margin-top: -8px; }}
  .row {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  figure {{ margin: 0; width: min(360px, 100%); }}
  img {{ width: 100%; height: auto; border: 1px solid #ddd; background: #fff; display: block; }}
  figcaption {{ font-size: 0.85rem; margin-top: 6px; text-align: center; }}
  code {{ background: #eee; padding: 1px 5px; border-radius: 4px; }}
</style>
</head>
<body>
  <h1>בדיקת צפיפות פאטרן — השוואה הוגנת</h1>
  <div class="note">
    <p><strong>איך לקרוא:</strong> בכל עמודה אותו גודל תצוגה, וגודל האלמנטים בפיקסלים זהה.</p>
    <p>מה שמשתנה: כמה אלמנטים נכנסים לאותו שטח (צפוף ↔ מרווח).</p>
    <p>אל תסתכלי על קבצי <code>*_tile_DEBUG.png</code> — הם אריח גולמי בגדלים שונים ולכן מטעים.</p>
    <p>קבצים חשובים: <code>*_COMPARE.png</code> ו־<code>*_SAME_SIZE.png</code></p>
  </div>
  {"".join(rows_html)}
</body>
</html>
"""
    path = out_dir / "index.html"
    path.write_text(doc, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="*", type=Path, default=None)
    ap.add_argument("--spacings", default="0.50,1.0,1.35")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("_tmp_density_test"),
    )
    ap.add_argument("--window", type=int, default=1024)
    ap.add_argument("--panel", type=int, default=560)
    args = ap.parse_args()

    inputs = list(args.inputs) if args.inputs else find_default_inputs()
    if not inputs:
        print("No input images found.", file=sys.stderr)
        return 1

    spacings = [float(x.strip()) for x in args.spacings.split(",") if x.strip()]
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clear old misleading previews so only fair ones remain prominent
    for old in out_dir.glob("*"):
        if old.is_file() and old.suffix.lower() in {".png", ".html", ".txt"}:
            old.unlink()

    print(f"Output: {out_dir.resolve()}")
    print(f"Spacings: {spacings}")
    print("Fair preview mode: fixed window, constant motif pixel size")
    print(f"Inputs ({len(inputs)}):")
    for p in inputs:
        print(f"  - {p.name}")

    results = []
    for path in inputs:
        if not path.exists():
            print(f"MISSING: {path}", file=sys.stderr)
            continue
        results.append(process_one(path, out_dir, spacings, args.window, args.panel))

    try:
        build_contact_sheet(out_dir, results, spacings, thumb=360)
    except Exception as e:
        print(f"Contact sheet skipped: {e}")

    gallery = write_gallery_html(out_dir, results, spacings)
    readme = out_dir / "READ_ME.txt"
    readme.write_text(
        "\n".join(
            [
                "Pattern density fair preview",
                "============================",
                "",
                "Open index.html in a browser.",
                "",
                "Look at:",
                "  *_COMPARE.png     = side-by-side labeled strip",
                "  *_SAME_SIZE.png   = same fabric window, same motif size",
                "",
                "Ignore:",
                "  *_tile_DEBUG.png  = raw repeat unit (different pixel sizes; misleading)",
                "",
                "What changes between columns:",
                "  spacing < 1  -> denser (more motifs in the same area)",
                "  spacing = 1  -> original",
                "  spacing > 1  -> sparser (fewer motifs in the same area)",
                "Motif shape/size in pixels stays the same.",
                "",
                f"Folder: {out_dir.resolve()}",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nGallery: {gallery.resolve()}")
    print(f"Read me: {readme.resolve()}")
    print(f"Done. Open: {out_dir.resolve()}")
    return 0


def build_contact_sheet(
    out_dir: Path, results: list[dict], spacings: list[float], thumb: int = 360
) -> None:
    rows = []
    for r in results:
        name = r["name"]
        cells = []
        labels = []
        for spacing in spacings:
            tag = f"s{int(round(spacing * 100)):03d}"
            p = out_dir / f"{name}_{tag}_SAME_SIZE.png"
            if p.exists():
                cells.append(Image.open(p).convert("RGB"))
                labels.append(spacing_label(spacing))
        if not cells:
            continue
        panels = [
            labeled_panel(c.resize((thumb, thumb), Image.Resampling.BILINEAR), lab, "same motif px size", thumb)
            for c, lab in zip(cells, labels)
        ]
        gap = 8
        row_w = sum(p.width for p in panels) + gap * (len(panels) - 1)
        row = Image.new("RGB", (row_w, panels[0].height), (255, 255, 255))
        x = 0
        for p in panels:
            row.paste(p, (x, 0))
            x += p.width + gap
        rows.append(row)
    if not rows:
        return
    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + 8 * (len(rows) - 1)), (255, 255, 255))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 8
    sheet.save(out_dir / "_contact_sheet_FAIR.png")
    print(f"Contact sheet: {out_dir / '_contact_sheet_FAIR.png'}")


if __name__ == "__main__":
    raise SystemExit(main())
