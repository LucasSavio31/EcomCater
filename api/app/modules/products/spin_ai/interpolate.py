"""Interpolação de quadros entre duas fotos do produto via RIFE (Real-Time
Intermediate Flow Estimation) -- github.com/hzwer/Practical-RIFE, MIT License,
pesos v4.25.lite (`weights/flownet.pkl`, baixado uma vez e versionado aqui).

Roda 100% offline/CPU (a VPS não tem GPU) -- é chamado só em lote, quando as
fotos de um produto são salvas com "Visualização 360°" ligado, nunca em
tempo real numa requisição de loja. O modelo é carregado uma vez (singleton
em memória do processo) e reaproveitado entre chamadas.
"""
from __future__ import annotations

import io
import logging
import threading
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from app.modules.products.spin_ai.ifnet import IFNet

logger = logging.getLogger("products.spin_ai")

_WEIGHTS_PATH = Path(__file__).parent / "weights" / "flownet.pkl"
_DEVICE = torch.device("cpu")

_model: IFNet | None = None
_model_lock = threading.Lock()


def _get_model() -> IFNet:
    """Carrega o modelo uma vez por processo (thread-safe, chamado de dentro
    de `asyncio.to_thread`)."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            net = IFNet()
            state = torch.load(_WEIGHTS_PATH, map_location="cpu")
            state = {k.replace("module.", ""): v for k, v in state.items()}
            net.load_state_dict(state, strict=False)
            net.eval()
            _model = net
    return _model


def _to_tensor(img: Image.Image) -> torch.Tensor:
    arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)


def _to_image(t: torch.Tensor, size: tuple[int, int]) -> Image.Image:
    arr = (t[0].clamp(0, 1).permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
    return Image.fromarray(arr).resize(size, Image.LANCZOS)


def _pad(t: torch.Tensor, mult: int = 32) -> tuple[torch.Tensor, int, int]:
    h, w = t.shape[2], t.shape[3]
    ph = ((h - 1) // mult + 1) * mult
    pw = ((w - 1) // mult + 1) * mult
    return F.pad(t, (0, pw - w, 0, ph - h)), h, w


def interpolate_between(img0_bytes: bytes, img1_bytes: bytes, n_frames: int) -> list[bytes]:
    """`n_frames` quadros igualmente espaçados ENTRE (exclusive) as duas
    fotos -- ex.: n_frames=2 dá os quadros em t=1/3 e t=2/3. Roda de forma
    síncrona/bloqueante (chame via `asyncio.to_thread`); retorna cada quadro
    já codificado em WebP."""
    if n_frames <= 0:
        return []

    model = _get_model()
    img0 = Image.open(io.BytesIO(img0_bytes))
    img1 = Image.open(io.BytesIO(img1_bytes)).resize(img0.size)
    size = img0.size

    t0 = _to_tensor(img0)
    t1 = _to_tensor(img1)
    t0p, h, w = _pad(t0)
    t1p, _, _ = _pad(t1)

    out: list[bytes] = []
    with torch.no_grad():
        for i in range(1, n_frames + 1):
            timestep = i / (n_frames + 1)
            x = torch.cat((t0p, t1p), 1)
            merged = model(x, timestep=timestep, scale_list=(32, 16, 8, 4, 1))
            frame = merged[-1][:, :, :h, :w]
            im = _to_image(frame, size)
            buf = io.BytesIO()
            im.save(buf, format="WEBP", quality=85)
            out.append(buf.getvalue())
    return out
