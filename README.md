# gox-logo-concepts

[Gox](https://github.com/14752222/Gox)（Go 实现的 JavaScript 运行时 + 自研 GUI）的 logo 概念稿与官网资产生成脚本。

## 内容

| 文件 | 尺寸 | 说明 |
|---|---|---|
| `Minimalist_flat_vector_logo_ma_2026-09-19T04-57-45.png` | 1024×1024 | 扁平矢量方向 · 概念稿 1 |
| `Minimalist_flat_vector_logo_ma_2026-09-19T04-57-46.png` | 1024×1024 | 扁平矢量方向 · 概念稿 2 |
| `Minimalist_flat_vector_logo_ma_2026-09-19T04-57-47.png` | 1024×1024 | 扁平矢量方向 · 概念稿 3 |
| `Minimalist_flat_vector_logo_ma_2026-09-19T04-57-50.png` | 1024×1024 | 扁平矢量方向 · 概念稿 4 |
| `Refine_this_pixel_raster_logo__2026-09-19T05-01-31.png` | 1024×1024 | 像素栅格方向 · 第一轮 |
| `Refine_this_pixel_raster_logo__2026-09-19T05-01-56.png` | 1024×1024 | 像素栅格方向 · 定稿，`make_assets.py` 的输入 |
| `make_assets.py` | — | 从定稿图生成官网资产 |

## 生成官网资产

`make_assets.py` 做四件事：擦掉右下角水印 → 把白角与浅灰软阴影转透明 → 按 bbox 裁切并内缩/补边 → 导出 512×512 的 `logo.png` 与 64×64 的 `favicon.png`。

```bash
python -m pip install Pillow          # 依赖
python make_assets.py                 # 输出到 ../website/assets/
python make_assets.py D:/somewhere    # 或显式指定输出目录
```

默认输出目录是 `../website/assets`，即本仓库以**子模块**形式挂在 Gox 主仓库 `gox-logo-concepts/` 下时，
主仓库官网的资产目录。产物由 [gox-website](https://github.com/14752222/gox-website) 负责版本管理，本仓库只放概念稿与生成脚本。

## 与主仓库的关系

本仓库以子模块形式挂在 Gox 的 `gox-logo-concepts/` 路径下：

```bash
git clone --recurse-submodules git@github.com:14752222/Gox.git
```

在此之前（2026-09-24 之前）该目录被主仓库 `.gitignore` 忽略、从未进过版本库 —— 也就是说只存在于某一台机器上。
