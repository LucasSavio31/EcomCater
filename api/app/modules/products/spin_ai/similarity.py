"""Heurística leve (só PIL+numpy, sem modelo) pra decidir se duas fotos do
produto são ângulos parecidos o bastante pra interpolar bem.

Fotos de catálogo comuns misturam composições bem diferentes (só a peça,
peça + solado lado a lado, par junto, detalhe...) -- nenhuma IA de
interpolação de vídeo (feita pra quadros de câmera em movimento suave) lida
bem com isso, o resultado sai borrado/com fantasma. Como são fotos de
produto em fundo branco, comparar a SILHUETA (pixels não-brancos) das duas
fotos é um sinal barato e eficaz: pares do mesmo ângulo dão uma
sobreposição alta; composições diferentes dão uma sobreposição bem menor,
mesmo quando a cor/iluminação geral é parecida.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

# Validado com fotos reais da loja (ver conversa/testes): pares do mesmo
# ângulo ficaram > 0.90; composições diferentes ficaram entre 0.55 e 0.70.
SIMILARITY_THRESHOLD = 0.80

_SIZE = 64
_WHITE_CUTOFF = 245


def _foreground_mask(data: bytes) -> np.ndarray:
    im = Image.open(io.BytesIO(data)).convert("L").resize((_SIZE, _SIZE))
    return np.array(im, dtype=np.float64) < _WHITE_CUTOFF


def foreground_similarity(img0: bytes, img1: bytes) -> float:
    """IoU das silhuetas -- 1.0 = mesma pose/ângulo; valores baixos = fotos
    de composição diferente (não interpola bem, melhor pular o par)."""
    m0, m1 = _foreground_mask(img0), _foreground_mask(img1)
    union = np.logical_or(m0, m1).sum()
    if union == 0:
        return 0.0
    inter = np.logical_and(m0, m1).sum()
    return float(inter / union)
