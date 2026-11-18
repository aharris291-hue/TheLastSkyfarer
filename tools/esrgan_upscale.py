"""Real-ESRGAN x4 (anime 6B) upscaler, CPU inference with PyTorch.

Model: RealESRGAN_x4plus_anime_6B.pth by Xintao Wang et al., BSD-3-Clause
(https://github.com/xinntao/Real-ESRGAN). Download it into tools/models/
(not committed):
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth
  sha256 f872d837d3c90ed2e05227bed711af5671a6fd1c9f7d7e91c911a61f155e99da
Needs: pip install torch numpy pillow
Weights are loaded with weights_only=True, so no pickled
code is executed.

Usage as a module: from esrgan_upscale import upscale; upscale(pil_img) -> 4x
Usage from the shell: python3 tools/esrgan_upscale.py in.png out.png
"""
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

MODEL = os.path.join(os.path.dirname(__file__), "models", "RealESRGAN_x4plus_anime_6B.pth")


class RDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.rdb1 = RDB(nf, gc)
        self.rdb2 = RDB(nf, gc)
        self.rdb3 = RDB(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, nb=6, nf=64):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        f = self.conv_first(x)
        f = f + self.conv_body(self.body(f))
        f = self.lrelu(self.conv_up1(F.interpolate(f, scale_factor=2, mode="nearest")))
        f = self.lrelu(self.conv_up2(F.interpolate(f, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(f)))


_net = None


def _model():
    global _net
    if _net is None:
        _net = RRDBNet()
        sd = torch.load(MODEL, map_location="cpu", weights_only=True)
        _net.load_state_dict(sd.get("params_ema", sd.get("params", sd)))
        _net.eval()
    return _net


def upscale(img, tile=192, pad=12):
    """Return a 4x RGB upscale of a PIL image (alpha is ignored)."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    t = torch.from_numpy(a).permute(2, 0, 1)[None]
    h, w = a.shape[:2]
    out = torch.zeros(1, 3, h * 4, w * 4)
    with torch.no_grad():
        for y in range(0, h, tile):
            for x in range(0, w, tile):
                y0, x0 = max(y - pad, 0), max(x - pad, 0)
                y1, x1 = min(y + tile + pad, h), min(x + tile + pad, w)
                o = _model()(t[:, :, y0:y1, x0:x1])
                oy, ox = (y - y0) * 4, (x - x0) * 4
                th, tw = min(tile, h - y) * 4, min(tile, w - x) * 4
                out[:, :, y * 4:y * 4 + th, x * 4:x * 4 + tw] = o[:, :, oy:oy + th, ox:ox + tw]
    arr = out[0].permute(1, 2, 0).clamp(0, 1).numpy()
    return Image.fromarray((arr * 255 + 0.5).astype(np.uint8))


if __name__ == "__main__":
    upscale(Image.open(sys.argv[1])).save(sys.argv[2])
