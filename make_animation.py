# -*- coding: utf-8 -*-
"""make_animation.py — 从官网 logo.png 提取像素块，生成动画版 logo。

产物（默认输出到脚本所在目录）：
  logo-animated.svg          矢量动画（像素对角波汇聚成 G，随后呼吸脉冲），官网 hero 用
  logo-animated.gif          同款动画 GIF（README / 社交场景用）
  logo-animation-preview.html 本地预览页（SVG + GIF 对照）

用法：
  python make_animation.py                 # 从 ../website/public/logo.png 读入
  python make_animation.py <out_dir>       # 显式指定输出目录
"""
import colorsys
import os
import sys
from collections import deque

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "website", "public", "logo.png"))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else HERE

# ── 动画参数 ────────────────────────────────────────────────
POP_S = 0.55          # 单块 pop-in 时长（秒）
STAGGER_S = 1.7       # 全部块的错峰窗口（秒）
BREATHE_S = 2.6       # 组装完后的单次呼吸时长（秒）
GIF_SIZE = 256        # GIF 输出边长
GIF_FRAME_MS = 45     # GIF 每帧时长


def load_blocks():
    im = Image.open(SRC).convert("RGBA")
    W, H = im.size
    px = im.load()

    # 1) 背景深色 = 出现最多的不透明颜色
    from collections import Counter
    cnt = Counter()
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            r, g, b, a = px[x, y]
            if a > 200:
                cnt[(r, g, b)] += 1
    bg = cnt.most_common(1)[0][0]

    # 2) 前景掩码：不透明且与背景色差明显
    def is_fg(x, y):
        r, g, b, a = px[x, y]
        if a < 100:
            return False
        return abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 60

    # 3) 连通域（4 连通，BFS）。先腐蚀 2px 断开抗锯齿造成的块间粘连，
    #    再在腐蚀图上做连通域，bbox 外扩 2px 还原。
    from PIL import ImageFilter
    mask_im = Image.new("L", (W, H), 0)
    mp = mask_im.load()
    for y in range(H):
        for x in range(W):
            if is_fg(x, y):
                mp[x, y] = 255
    eroded = mask_im.filter(ImageFilter.MinFilter(5))
    ep = eroded.load()

    def e_fg(x, y):
        return ep[x, y] > 128

    seen = [[False] * W for _ in range(H)]
    blocks = []
    for y0 in range(H):
        for x0 in range(W):
            if seen[y0][x0] or not e_fg(x0, y0):
                continue
            q = deque([(x0, y0)])
            seen[y0][x0] = True
            pts = []
            while q:
                x, y = q.popleft()
                pts.append((x, y))
                for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                    if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx] and e_fg(nx, ny):
                        seen[ny][nx] = True
                        q.append((nx, ny))
            if len(pts) < 40:   # 噪点
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            bx0, bx1, by0, by1 = min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2
            n = 0
            mr = mg = mb = 0
            for yy in range(max(by0, 0), min(by1 + 1, H)):
                for xx in range(max(bx0, 0), min(bx1 + 1, W)):
                    if is_fg(xx, yy):
                        r, g, b2, a = px[xx, yy]
                        mr += r; mg += g; mb += b2; n += 1
            blocks.append({
                "x": bx0, "y": by0, "w": bx1 - bx0 + 1, "h": by1 - by0 + 1,
                "cx": (bx0 + bx1) / 2, "cy": (by0 + by1) / 2,
                "color": (round(mr / n), round(mg / n), round(mb / n)),
            })

    # 4) 大底板（深色圆角方块）的范围与圆角半径
    alpha = im.split()[3]
    ap = alpha.load()
    minx, miny, maxx, maxy = W, H, 0, 0
    for y in range(H):
        for x in range(W):
            if ap[x, y] > 10:
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    # 圆角半径：顶行第一个不透明像素的 x
    radius = 0
    for x in range(W):
        if ap[x, miny] > 10:
            radius = x - minx
            break

    print(f"source: {SRC}  {W}x{H}")
    print(f"background tile: bbox=({minx},{miny})-({maxx},{maxy}) radius={radius} bg=#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}")
    print(f"blocks: {len(blocks)}")
    sizes = sorted(b["w"] for b in blocks)
    print(f"block size min/med/max = {sizes[0]}/{sizes[len(sizes)//2]}/{sizes[-1]}")
    return im, bg, (minx, miny, maxx, maxy), radius, blocks


def rgb2hex(c):
    return "#%02x%02x%02x" % c


def build_svg(bg, tile, radius, blocks):
    x0, y0, x1, y1 = tile
    order = sorted(range(len(blocks)), key=lambda i: blocks[i]["cx"] + blocks[i]["cy"])
    n = len(order)
    rects = []
    for rank, idx in enumerate(order):
        b = blocks[idx]
        d = STAGGER_S * rank / max(n - 1, 1)
        rx = b["w"] * 0.24
        rects.append(
            f'    <rect class="p" x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" '
            f'rx="{rx:.1f}" fill="{rgb2hex(b["color"])}" '
            f'style="--d:{d:.3f}s"/>'
        )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Gox logo">
  <!-- Gox 像素栅格 logo · 动画版。由 gox-logo-concepts/make_animation.py 生成，勿手改。 -->
  <style>
    .tile {{ animation: gtile {BREATHE_S + POP_S + STAGGER_S:.2f}s ease-in-out infinite; }}
    .p {{
      transform-box: fill-box;
      transform-origin: center;
      animation:
        gpop {POP_S}s cubic-bezier(0.2, 1.4, 0.4, 1) var(--d) both,
        gbreathe {BREATHE_S}s ease-in-out {STAGGER_S + POP_S + 0.2:.2f}s infinite;
    }}
    @keyframes gpop {{
      from {{ transform: scale(0); opacity: 0; }}
      to   {{ transform: scale(1); opacity: 1; }}
    }}
    @keyframes gbreathe {{
      0%, 100% {{ opacity: 1; }}
      50%      {{ opacity: 0.78; }}
    }}
    @keyframes gtile {{
      0%, 100% {{ transform: scale(1); }}
      50%      {{ transform: scale(1.025); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .tile, .p {{ animation: none; }}
    }}
  </style>
  <g class="tile" style="transform-box: fill-box; transform-origin: center;">
    <rect x="{x0}" y="{y0}" width="{x1 - x0 + 1}" height="{y1 - y0 + 1}" rx="{radius}" fill="{rgb2hex(bg)}"/>
{chr(10).join(rects)}
  </g>
</svg>
'''
    path = os.path.join(OUT, "logo-animated.svg")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print(f"wrote {path}  ({os.path.getsize(path)} bytes, {len(rects)} rects)")
    return path


def rounded(im, box, radius, fill):
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, radius=radius, fill=fill)


def build_gif(im_src, bg, tile, radius, blocks):
    W = H = 512
    order = sorted(range(len(blocks)), key=lambda i: blocks[i]["cx"] + blocks[i]["cy"])
    n = len(order)

    def base_frame():
        f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rounded(f, tile, radius, bg + (255,))
        return f

    def block_frame(f, b, scale, alpha):
        """在 f 上画缩放为 scale、透明度 alpha 的块 b"""
        if scale <= 0.03 or alpha <= 0.02:
            return
        w = b["w"] * scale
        cx, cy = b["cx"], b["cy"]
        box = (cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw_draw(overlay)
        col = b["color"] + (int(255 * alpha),)
        d.rounded_rectangle(box, radius=w * 0.24, fill=col)
        f.alpha_composite(overlay)

    def ImageDraw_draw(im):
        from PIL import ImageDraw
        return ImageDraw.Draw(im)

    # ── 时间轴（秒）──
    starts = [STAGGER_S * i / max(n - 1, 1) for i in range(n)]
    asm_end = max(s + POP_S for s in starts)
    breathe_cycles = 2
    total = asm_end + BREATHE_S * breathe_cycles
    fps = 1000 / GIF_FRAME_MS
    nframes = int(total * fps)

    canvas_bg = (0x0b, 0x0f, 0x14, 255)   # 官网暗底色，GIF 不支持半透明
    frames = []
    for k in range(nframes):
        t = k / fps
        f = base_frame()
        for i in range(n):
            b = blocks[order[i]]
            local = t - starts[i]
            if local < 0:
                continue
            if local >= POP_S:
                # 组装完成后进入呼吸：全局面亮度波浪
                ph = (t - asm_end) / BREATHE_S
                a = 1.0
                if ph > 0:
                    wave = 0.5 + 0.5 * __import__("math").sin(2 * 3.141592653589793 * ph - 0.9 * (b["cx"] + b["cy"]) / 512)
                    a = 1.0 - 0.16 * wave
                block_frame(f, b, 1.0, a)
            else:
                p = local / POP_S
                # ease-out-back 近似
                scale = 1 + 1.35 * (p - 1) ** 3 + 0.35 * (p - 1) ** 2 + 0.0
                scale = max(0.0, min(1.12, scale if p < 1 else 1.0))
                # 简化：cubic ease-out + 轻微过冲
                import math
                e = 1 - (1 - p) ** 3
                scale = e * 1.08 if p < 0.7 else 1.0 + 0.08 * (1 - (p - 0.7) / 0.3) if p < 1 else 1.0
                block_frame(f, b, min(scale, 1.08), min(1.0, p * 2))
        out = Image.new("RGBA", (W, H), canvas_bg)
        out.alpha_composite(f)
        frames.append(out.resize((GIF_SIZE, GIF_SIZE), Image.LANCZOS).convert("RGB"))

    q = [frm.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG) for frm in frames]
    path = os.path.join(OUT, "logo-animated.gif")
    q[0].save(path, save_all=True, append_images=q[1:], duration=GIF_FRAME_MS, loop=0, optimize=True)
    print(f"wrote {path}  ({os.path.getsize(path)} bytes, {len(q)} frames, {GIF_SIZE}px)")


def build_preview(svg_path):
    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Gox Logo 动画预览</title>
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; background: #0b0f14; color: #dbe4ee;
         display: flex; flex-direction: column; align-items: center; gap: 28px; padding: 48px 24px; }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 0; }}
  .row {{ display: flex; gap: 48px; flex-wrap: wrap; justify-content: center; align-items: flex-start; }}
  .card {{ background: #10161e; border: 1px solid #1f2b37; border-radius: 16px; padding: 32px;
           display: flex; flex-direction: column; align-items: center; gap: 16px; }}
  .card p {{ margin: 0; font-size: 13px; color: #8fa1b5; }}
  img, svg {{ width: 256px; height: 256px; }}
  .light {{ background: #f6f8fa; }}
  .light p {{ color: #57606a; }}
  button {{ background: #1f8f63; border: 0; color: #fff; padding: 8px 18px; border-radius: 8px;
            cursor: pointer; font-size: 13px; }}
</style>
</head>
<body>
  <h1>Gox Logo 动画预览</h1>
  <div class="row">
    <div class="card">
      <img src="logo-animated.svg" alt="Gox logo 动画 SVG">
      <p>logo-animated.svg（官网 hero 用）</p>
      <button onclick="replay()">↻ 重播</button>
    </div>
    <div class="card light">
      <img src="logo-animated.gif" alt="Gox logo 动画 GIF">
      <p>logo-animated.gif（README / 浅色背景效果）</p>
    </div>
    <div class="card">
      <img src="../website/public/logo.png" alt="Gox logo 静态">
      <p>原静态 logo.png（对照）</p>
    </div>
  </div>
  <script>
    function replay() {{
      document.querySelectorAll('img[src$=".svg"]').forEach(el => {{
        const src = el.src; el.src = ''; requestAnimationFrame(() => {{ el.src = src; }});
      }});
    }}
  </script>
</body>
</html>
'''
    path = os.path.join(OUT, "logo-animation-preview.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"wrote {path}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    im, bg, tile, radius, blocks = load_blocks()
    build_svg(bg, tile, radius, blocks)
    build_gif(im, bg, tile, radius, blocks)
    build_preview(os.path.join(OUT, "logo-animated.svg"))
