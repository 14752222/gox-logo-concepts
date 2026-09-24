# 从定稿图生成网站资产:先擦水印 -> 再白角/灰环转透明 -> 裁切导出 logo.png / favicon.png
#
# 用法:
#     python make_assets.py [输出目录]
#
# 默认输出目录是 ../website/assets —— 即本仓库以子模块形式挂在 Gox 主仓库
# gox-logo-concepts/ 下时，主仓库官网的资产目录。
# 本仓库若被单独 clone 到别处，请显式传入输出目录，否则脚本会直接报错退出
# （而不是默默写到某个不存在的地方）。
#
# 依赖: Pillow (python -m pip install Pillow)
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "Refine_this_pixel_raster_logo__2026-09-19T05-01-56.png")

if len(sys.argv) > 1:
    OUT_DIR = os.path.abspath(sys.argv[1])
else:
    OUT_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "website", "assets"))

LOGO_OUT = os.path.join(OUT_DIR, "logo.png")
FAVICON_OUT = os.path.join(OUT_DIR, "favicon.png")

if not os.path.isfile(SRC):
    sys.exit("找不到定稿图: %s" % SRC)
if not os.path.isdir(OUT_DIR):
    sys.exit(
        "输出目录不存在: %s\n"
        "本仓库若未作为子模块挂在 Gox 主仓库下，请显式传入输出目录：\n"
        "    python make_assets.py <path/to/website/assets>" % OUT_DIR
    )

img = Image.open(SRC).convert("RGBA")
w, h = img.size
px = img.load()
print("source size:", w, h, "corner px:", px[5, 5], "bg sample:", px[w // 2, 40])

bg = px[w // 2, 40][:3]

# 1) 先擦水印:右下角文字区(x>900 且 y>940)内,非近白像素一律盖成章体底色。
#    章体内的灰字 -> 变底色;角落白底上的字 -> 白底部分保留给下一步转透明。
#    范围刻意避开 (884,884) 附近的散逸字节像素。
fixed = 0
for y in range(940, h):
    for x in range(900, w):
        r, g, b, a = px[x, y]
        near_white = r > 235 and g > 235 and b > 235
        if not near_white:
            px[x, y] = (*bg, 255)
            fixed += 1
print("watermark px fixed:", fixed)

# 2) 白角 + 浅灰软阴影转透明(低饱和浅灰;绿色像素 g 远高于 r/b 不会误伤)
white = 0
for y in range(h):
    for x in range(w):
        r, g, b, a = px[x, y]
        low_sat = (max(r, g, b) - min(r, g, b)) < 20
        if (r > 235 and g > 235 and b > 235) or (low_sat and min(r, g, b) > 120):
            px[x, y] = (0, 0, 0, 0)
            white += 1
print("whitened px:", white)

# 3) 章体 bbox(受边缘残留影响可能仍是全画布,无碍,靠内缩去掉边缘)
bbox = img.getbbox()
print("tile bbox:", bbox)

# 4) 内缩 1.2% 去边缘杂色/残留阴影,补 2% 透明边距
tile = img.crop(bbox)
tw, th = tile.size
inset = int(min(tw, th) * 0.012)
tile = tile.crop((inset, inset, tw - inset, th - inset))
tw, th = tile.size
pad = int(min(tw, th) * 0.02)
canvas = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
canvas.paste(tile, (pad, pad))

# 5) 导出
canvas.resize((512, 512), Image.LANCZOS).save(LOGO_OUT, "PNG")
canvas.resize((64, 64), Image.LANCZOS).save(FAVICON_OUT, "PNG")
print("written:", LOGO_OUT, FAVICON_OUT)
