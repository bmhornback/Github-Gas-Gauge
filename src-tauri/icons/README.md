# Tray Icons

These are placeholder icon files. Replace them with real PNG/ICO/ICNS images before building.

## Required icons

| File | Size | Use |
|---|---|---|
| `tray-green.png` | 16x16 or 22x22 | Tray icon — usage < 75% |
| `tray-yellow.png` | 16x16 or 22x22 | Tray icon — usage 75–89% |
| `tray-red.png` | 16x16 or 22x22 | Tray icon — usage ≥ 90% |
| `32x32.png` | 32x32 | App icon |
| `128x128.png` | 128x128 | App icon |
| `128x128@2x.png` | 256x256 | App icon (HiDPI) |
| `icon.icns` | macOS bundle icon | |
| `icon.ico` | Windows bundle icon | |

You can generate bundle icons from a single source image using `tauri icon <image.png>`.
