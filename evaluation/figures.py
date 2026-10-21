"""Draw the README figure (English and Portuguese) from evaluation/results.json.

Run after evaluate.py, from the repository root:  python evaluation/figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
INK, MUTED = "#1f1f1f", "#666666"
PRECISION, RECALL = "#2a78d6", "#eb6834"
for family in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(family, fallback_to_default=False)
        plt.rcParams["font.family"] = family
        break
    except ValueError:
        continue

ROWS = [
    ("2019: all keys, two hops, fingerprint bug, no attribute check",
     "2019: every key, fingerprint bug", "2019: todas as chaves, fingerprint com bug"),
    ("all keys, barcode without the word check, no attribute check",
     "fixed fingerprint, barcode without word check", "fingerprint corrigido, EAN sem conferir palavras"),
    ("all keys, connected, no attribute check",
     "+ word check on barcodes", "+ conferência de palavras no EAN"),
    ("all keys, connected, attribute check",
     "+ attribute check (size, voltage, colour)", "+ atributos (tamanho, voltagem, cor)"),
    ("all keys, connected, attribute and brand check",
     "+ brand check", "+ conferência de marca"),
    ("recommended keys, connected, attribute check",
     "recommended keys + attribute check", "chaves recomendadas + atributos"),
]
TEXT = {
    "en": {"title": "What each safeguard buys", "sub": "{n} synthetic listings of {e} product variants · pairwise scores",
           "p": "precision", "r": "recall", "suffix": ""},
    "pt": {"title": "O que cada proteção rende", "sub": "{n} anúncios sintéticos de {e} variantes de produto · pares",
           "p": "precisão", "r": "cobertura", "suffix": ".pt-BR"},
}


def main() -> None:
    res = json.loads((ROOT / "evaluation" / "results.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for lang, t in TEXT.items():
        fig, ax = plt.subplots(figsize=(10, 5.2), dpi=110)
        fig.subplots_adjust(left=0.4, right=0.95, top=0.8, bottom=0.1)
        n = f"{res['listings']:,}".replace(",", "." if lang == "pt" else ",")
        e = f"{res['entities']:,}".replace(",", "." if lang == "pt" else ",")
        fig.text(0.02, 0.93, t["title"], fontsize=17, weight="bold", color=INK)
        fig.text(0.02, 0.87, t["sub"].format(n=n, e=e), fontsize=10.5, color=MUTED)
        labels, ps, rs = [], [], []
        for key, en, pt in ROWS:
            c = res["configurations"][key]
            labels.append(en if lang == "en" else pt)
            ps.append(c["precision"] * 100)
            rs.append(c["recall"] * 100)
        ys = list(range(len(labels)))[::-1]
        h = 0.36
        ax.barh([y + h / 2 for y in ys], ps, height=h - 0.04, color=PRECISION, label=t["p"])
        ax.barh([y - h / 2 for y in ys], rs, height=h - 0.04, color=RECALL, label=t["r"])
        for y, p, r in zip(ys, ps, rs):
            fmt = (lambda v: f"{v:.0f}%")
            ax.text(p + 1, y + h / 2, fmt(p), va="center", fontsize=9.5, color=INK)
            ax.text(r + 1, y - h / 2, fmt(r), va="center", fontsize=9.5, color=INK)
        ax.set_yticks(ys)
        ax.set_yticklabels(labels, fontsize=10, color=INK)
        ax.set_xlim(0, 108)
        ax.set_xticks([])
        for s in ("top", "right", "bottom", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(left=False)
        ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.12), ncol=2, frameon=False, fontsize=10)
        fig.savefig(OUT / f"safeguards{t['suffix']}.png", facecolor="white")
        plt.close(fig)
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
