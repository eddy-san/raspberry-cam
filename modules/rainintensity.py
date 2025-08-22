#!/usr/bin/env python3
# modules/rainintensity.py

from __future__ import annotations

import io
import json
import time
from pathlib import Path
from typing import List, Tuple, Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ============================ Basis-Setup ============================

# Nürnberg-Ausschnitt: Tile-Koordinaten (x, y) bei Zoom 6 (2×2)
DEFAULT_TILES: List[Tuple[int, int]] = [(33, 21), (34, 21), (33, 22), (34, 22)]
TILE_SIZE = 256

CARTO_BASE = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
RAINVIEWER_API = "https://api.rainviewer.com/public/weather-maps.json"


# ============================ HTTP-Helfer ============================

def _get_session(cfg: dict) -> requests.Session:
    """
    Baut eine Requests-Session mit UA aus cfg:
      cfg["user_agent"], cfg["contact_email"]
    """
    ua = f"{cfg.get('user_agent', 'my-app/1.0')} (contact: {cfg.get('contact_email', 'contact@example.com')})"
    s = requests.Session()
    s.headers.update({
        "User-Agent": ua,
        "Accept": "image/png,image/*;q=0.8,application/json;q=0.7,*/*;q=0.5",
        "Connection": "keep-alive",
    })
    return s


def _http_get(session: requests.Session, url: str, *, connect_timeout: float = 3.0,
              read_timeout: float = 8.0, tries: int = 3) -> requests.Response:
    """
    GET mit einfachem Exponential-Backoff.
    """
    last_exc = None
    for i in range(max(1, tries)):
        try:
            r = session.get(url, timeout=(connect_timeout, read_timeout))
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            if i == tries - 1:
                raise
            time.sleep(0.5 * (2 ** i))
    # sollte nie hier landen
    raise last_exc  # type: ignore[misc]


def _fetch_json(session: requests.Session, url: str, *, read_timeout: float) -> dict:
    r = _http_get(session, url, read_timeout=read_timeout)
    return r.json()


def _download_png(session: requests.Session, url: str, *, read_timeout: float,
                  retries: int) -> Image.Image:
    r = _http_get(session, url, read_timeout=read_timeout, tries=retries + 1)
    return Image.open(io.BytesIO(r.content)).convert("RGBA")


# ============================ Bild-Helfer ============================

def _sanitize_text(s: str) -> str:
    """
    Ersetzt typische Unicode-Anführungen/Striche durch ASCII — hilft auf Systemen
    mit eingeschränkten Fonts/Encodings (z. B. älteren Pis).
    """
    return (s.replace("—", "-")
             .replace("–", "-")
             .replace("’", "'")
             .replace("“", '"')
             .replace("”", '"'))


def _alpha_apply(im: Image.Image, opacity: float) -> Image.Image:
    if opacity >= 1.0:
        return im
    if opacity <= 0.0:
        return Image.new("RGBA", im.size, (0, 0, 0, 0))
    r, g, b, a = im.split()
    a = a.point(lambda px: int(px * opacity))
    return Image.merge("RGBA", (r, g, b, a))


def _grid_cols_rows(n: int) -> tuple[int, int]:
    if n <= 0:
        raise ValueError("tiles must not be empty")
    cols = 1
    while (cols + 1) * (cols + 1) <= n:
        cols += 1
    while n % cols != 0 and cols > 1:
        cols -= 1
    rows = (n + cols - 1) // cols
    return cols, rows


# ============================ Basemap (mit Cache) ============================

def _compose_basemap(session: requests.Session, tiles: List[Tuple[int, int]], *, zoom: int,
                     read_timeout: float, retries: int) -> Image.Image:
    cols, rows = _grid_cols_rows(len(tiles))
    canvas = Image.new("RGBA", (cols * TILE_SIZE, rows * TILE_SIZE), (0, 0, 0, 255))
    for idx, (x, y) in enumerate(tiles):
        row, col = divmod(idx, cols)
        base_url = CARTO_BASE.format(z=zoom, x=x, y=y)
        base_im = _download_png(session, base_url, read_timeout=read_timeout, retries=retries)
        canvas.paste(base_im, (col * TILE_SIZE, row * TILE_SIZE))
    return canvas


def _load_or_build_basemap(session: requests.Session, *, basemap_image_cache_path: str,
                           tiles: List[Tuple[int, int]], zoom: int,
                           read_timeout: float, retries: int) -> Image.Image:
    """
    Lädt Basemap aus Cache (PNG) oder baut sie aus Tiles und cached sie.
    """
    p = Path(basemap_image_cache_path)
    if p.exists():
        try:
            return Image.open(p).convert("RGBA")
        except Exception:
            pass  # defekt → neu bauen
    base = _compose_basemap(session, tiles, zoom=zoom, read_timeout=read_timeout, retries=retries)
    p.parent.mkdir(parents=True, exist_ok=True)
    base.save(p, "PNG", optimize=True)
    return base


# ============================ Radar (Tiles + Cache) ============================

def _get_latest_radar_meta(session: requests.Session, *, read_timeout: float) -> tuple[str, str, int]:
    data = _fetch_json(session, RAINVIEWER_API, read_timeout=read_timeout)
    host = data.get("host") or "https://tilecache.rainviewer.com"
    past = (data.get("radar") or {}).get("past") or []
    if not past:
        raise RuntimeError("RainViewer returned no radar frames")
    last = past[-1]
    return host, last["path"], int(last["time"])


def _compose_radar_overlay(session: requests.Session, tiles: List[Tuple[int, int]], *,
                           zoom: int, host: str, rv_path: str,
                           palette: int, smooth: int, snow: int,
                           read_timeout: float, retries: int, opacity: float) -> Image.Image:
    cols, rows = _grid_cols_rows(len(tiles))
    overlay = Image.new("RGBA", (cols * TILE_SIZE, rows * TILE_SIZE), (0, 0, 0, 0))
    for idx, (x, y) in enumerate(tiles):
        row, col = divmod(idx, cols)
        rv_url = f"{host}{rv_path}/256/{zoom}/{x}/{y}/{palette}/{smooth}_{snow}.png"
        rv_im = _download_png(session, rv_url, read_timeout=read_timeout, retries=retries)
        overlay.alpha_composite(_alpha_apply(rv_im, opacity), (col * TILE_SIZE, row * TILE_SIZE))
    return overlay


def _save_radar_cache(cache_png: Path, overlay: Image.Image, epoch: Optional[int]) -> None:
    try:
        cache_png.parent.mkdir(parents=True, exist_ok=True)
        overlay.save(cache_png, "PNG", optimize=True)
        if epoch is not None:
            cache_png.with_suffix(".json").write_text(json.dumps({"epoch": int(epoch)}))
    except Exception:
        pass  # Best-effort


def _load_radar_cache(cache_png: Path) -> tuple[Optional[Image.Image], Optional[int]]:
    try:
        if not cache_png.exists():
            return None, None
        overlay = Image.open(cache_png).convert("RGBA")
        epoch = None
        meta = cache_png.with_suffix(".json")
        if meta.exists():
            try:
                epoch = int(json.loads(meta.read_text()).get("epoch"))
            except Exception:
                epoch = None
        return overlay, epoch
    except Exception:
        return None, None


# ============================ Legende (reine Farbskala) ============================

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (int(_lerp(c1[0], c2[0], t)), int(_lerp(c1[1], c2[1], t)), int(_lerp(c1[2], c2[2], t)))


def _make_legend(height: int, width: int = 54, padding: int = 8) -> Image.Image:
    """
    Vertikale Farbskala (ohne Labels).
    Höhe = genau die Höhe des Radar-Panels inkl. Header & Footer → bündig.
    """
    legend = Image.new("RGBA", (max(20, width), height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(legend)

    bar_x = padding
    bar_w = max(12, width - 2 * padding)
    bar_y0 = 0
    bar_y1 = height

    # Farbverlauf: violett → rot → orange → gelb → grün → türkis → grau
    stops = [
        (0.00, "#EE82EE"),
        (0.20, "#FF0000"),
        (0.40, "#FF7F00"),
        (0.60, "#FFFF00"),
        (0.78, "#00FF00"),
        (0.88, "#00BFFF"),
        (1.00, "#808080"),
    ]
    stops_rgb = [(pos, _hex_to_rgb(col)) for pos, col in stops]

    bar_h = bar_y1 - bar_y0
    for i in range(bar_h):
        y = bar_y0 + i
        t = i / max(1, bar_h - 1)
        # passender Abschnitt suchen und Farbe interpolieren
        for (p0, c0), (p1, c1) in zip(stops_rgb[:-1], stops_rgb[1:]):
            if t <= p1:
                tt = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                col = _lerp_color(c0, c1, tt)
                draw.line([(bar_x, y), (bar_x + bar_w - 1, y)], fill=col)
                break

    # dünner Rahmen exakt um die Skala (bündig oben/unten)
    draw.rectangle([bar_x - 1, bar_y0, bar_x + bar_w, bar_y1 - 1], outline="#555555")
    return legend


# ============================ Header / Footer (nur Radar) ============================

def _add_top_header_exact(
    base: Image.Image,
    *,
    title: str,
    radar_epoch: Optional[int],
    timestamp_fmt: str = "%Y-%m-%d %H:%M",
    pad_x: int = 8,
    pad_y: int = 6,
    text_color: str = "#D0D0D0",
    bg_color: tuple[int, int, int, int] = (60, 60, 60, 200),
) -> Image.Image:
    """
    Fügt oben einen grauen Header („title | timestamp“) hinzu; Breite = Basisbreite.
    Nur über das Radarbild (nicht über die Legende) setzen.
    """
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    ts = time.strftime(timestamp_fmt, time.localtime(radar_epoch)) if radar_epoch is not None else ""
    txt = _sanitize_text(f"{title} | {ts}" if ts else title)

    # Höhe bestimmen
    dummy = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    _, _, _, text_h = dummy.textbbox((0, 0), txt, font=font)
    text_h = max(text_h, 12)
    header_h = pad_y + text_h + pad_y

    out = Image.new("RGBA", (base.width, header_h + base.height), (0, 0, 0, 0))
    strip = Image.new("RGBA", (base.width, header_h), bg_color)
    out.paste(strip, (0, 0), strip)
    ImageDraw.Draw(out).text((pad_x, pad_y), txt, font=font, fill=text_color)
    out.paste(base, (0, header_h), base)
    return out


def _add_bottom_footer_exact(
    base: Image.Image,
    *,
    txt: Optional[str],
    pad_x: int = 8,
    pad_y: int = 6,
    text_color: str = "#D0D0D0",
    bg_color: tuple[int, int, int, int] = (0, 0, 0, 100),
) -> Image.Image:
    """
    Fügt unten eine halbtransparente Attribution hinzu; Breite = Basisbreite.
    Nur unter das Radarbild (nicht unter die Legende) setzen.
    """
    if not txt:
        return base

    txt = _sanitize_text(txt)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    dummy = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    _, _, _, text_h = dummy.textbbox((0, 0), txt, font=font)
    text_h = max(text_h, 10)
    footer_h = pad_y + text_h + pad_y

    out = Image.new("RGBA", (base.width, base.height + footer_h), (0, 0, 0, 0))
    out.paste(base, (0, 0), base)
    strip = Image.new("RGBA", (base.width, footer_h), bg_color)
    out.paste(strip, (0, base.height), strip)
    ImageDraw.Draw(out).text((pad_x, base.height + pad_y), txt, font=font, fill=text_color)
    return out


# ============================ Öffentliche API ============================

def generate(
    cfg: dict,
    *,
    # Ausgabepfade
    output_image_path: str,                 # Radar als eigenständiges JPG
    bg_image_path: str,                     # Hintergrundbild wird überschrieben
    # Cache-Pfade
    radar_image_cache_path: str,            # PNG für letztes gutes Radar (Fallback)
    basemap_image_cache_path: str,          # PNG für Basemap (wiederverwendbar)
    # Karten-Setup
    tiles: List[Tuple[int, int]] = DEFAULT_TILES,
    zoom: int = 6,
    # Darstellung / Layout
    legend: bool = True,
    legend_width: int = 54,
    legend_padding: int = 8,
    overlay_size: Tuple[int, int] = (400, 400),
    margin_right: int = 20,
    margin_bottom: int = 20,
    crop_bottom: int = 0,
    # Stil
    opacity: float = 0.85,
    border: bool = True,
    border_width: int = 4,
    border_color: str = "#808080",
    # Header/Footer
    header_title: str = "Rain Radar",
    timestamp_fmt: str = "%Y-%m-%d %H:%M",
    attribution_text: str = "© OpenStreetMap · Carto | Radar: RainViewer",
    # Radar/HTTP
    palette: int = 2,
    smooth: int = 1,
    snow: int = 1,
    timeout: float = 8.0,
    retries: int = 2,
    # Ausgabe
    jpg_quality: int = 92,
) -> None:
    """
    Erzeugt das Radar-Panel (Basemap + Radar), setzt **Header & Footer nur über/unter das Radar**,
    hängt rechts die **Farbleiste** bündig an, speichert ein **Radar-JPG** und bettet es **unten rechts**
    in das Hintergrundbild ein (optional mit Panel via BG, hier transparentes Rechteck nutzbar).
    """
    session = _get_session(cfg)

    # 1) Basemap laden/erstellen (Cache)
    basemap = _load_or_build_basemap(
        session,
        basemap_image_cache_path=basemap_image_cache_path,
        tiles=tiles,
        zoom=zoom,
        read_timeout=timeout,
        retries=retries,
    )

    # 2) Radar-Overlay laden; API → Cache, sonst Fallback aus Cache
    overlay = None
    rv_epoch: Optional[int] = None
    radar_cache_png = Path(radar_image_cache_path)
    try:
        host, rv_path, rv_epoch_now = _get_latest_radar_meta(session, read_timeout=timeout)
        overlay = _compose_radar_overlay(
            session, tiles,
            zoom=zoom, host=host, rv_path=rv_path,
            palette=palette, smooth=smooth, snow=snow,
            read_timeout=timeout, retries=retries, opacity=opacity,
        )
        rv_epoch = rv_epoch_now
        _save_radar_cache(radar_cache_png, overlay, rv_epoch)
    except Exception:
        overlay, cached_epoch = _load_radar_cache(radar_cache_png)
        rv_epoch = cached_epoch

    # 3) Radar-Canvas zusammensetzen (Basemap + Overlay)
    radar = basemap.copy()
    if overlay is not None:
        radar.alpha_composite(overlay)

    # 4) Unten beschneiden (vor Border/Headers)
    if crop_bottom > 0 and crop_bottom < radar.height:
        radar = radar.crop((0, 0, radar.width, radar.height - crop_bottom))

    # 5) Border NUR ums Radar
    if border and border_width > 0:
        try:
            radar = ImageOps.expand(radar, border=border_width, fill=border_color)
        except Exception:
            radar = ImageOps.expand(radar, border=border_width, fill="#808080")

    # 6) Header & Footer NUR über/unter Radar
    radar = _add_top_header_exact(
        radar,
        title=header_title,
        radar_epoch=rv_epoch,
        timestamp_fmt=timestamp_fmt,
        pad_x=8,
        pad_y=6,
        text_color="#DCDCDC",
        bg_color=(60, 60, 60, 200),
    )
    radar = _add_bottom_footer_exact(
        radar,
        txt=attribution_text,
        pad_x=8,
        pad_y=4,
        text_color="#D0D0D0",
        bg_color=(0, 0, 0, 100),
    )

    # 7) Legende rechts bündig anfügen (Höhe = aktuell inkl. Header/Footer)
    if legend:
        lg = _make_legend(radar.height, width=legend_width, padding=legend_padding)
        combined = Image.new("RGBA", (radar.width + lg.width, radar.height), (0, 0, 0, 0))
        combined.paste(radar, (0, 0))
        combined.paste(lg, (radar.width, 0), lg)
        radar = combined

    # 8) Radar-JPG speichern
    out = Path(output_image_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    radar.convert("RGB").save(out, "JPEG", quality=jpg_quality, optimize=True, progressive=True)

    # 9) In Hintergrundbild unten rechts einbetten
    bg = Image.open(bg_image_path).convert("RGB")
    fg = radar.resize(overlay_size, Image.LANCZOS).convert("RGBA")

    x = max(0, bg.width - overlay_size[0] - margin_right)
    y = max(0, bg.height - overlay_size[1] - margin_bottom)

    # Optionales Panel (wenn gewünscht, einfach hier ein halbtransparentes Rechteck zeichnen)
    # Beispiel:
    # panel_alpha = 140
    # pad = 10
    # panel_img = Image.new("RGBA", (overlay_size[0] + pad*2, overlay_size[1] + pad*2), (0, 0, 0, panel_alpha))
    # bg.paste(panel_img, (max(0, x - pad), max(0, y - pad)), panel_img)

    bg.paste(fg, (x, y), fg)
    bg.save(bg_image_path, "JPEG", quality=jpg_quality, optimize=True, progressive=True)


__all__ = ["generate", "DEFAULT_TILES"]

