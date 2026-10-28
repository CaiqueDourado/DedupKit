"""Cover image for the README (docs/img/cover.png and cover.pt-BR.png). Run: python docs/make_cover.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

OUT = Path(__file__).parent / "img"
INK, MUTED, LINE, BG = "#111111", "#555555", "#d9dde3", "#fdfdfc"
C = {"ink": INK, "muted": MUTED, "blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a"}
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False); plt.rcParams["font.family"] = fam; break
    except ValueError:
        pass

NAME, MARK, MARK_COLOR = 'DedupKit', '=', 'blue'
T = {'': {'tag': 'Same product,\nor only looks the same?',
      'sub': 'product matching for Brazilian Portuguese,\nin Python and .NET with identical results',
      'head': 'dedupkit · two groups',
      'lines': [('Fone de Ouvido sem Fio JBL Tune 510BT Preto', 'ink'),
                ('FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO', 'ink'),
                ('Fone Ouvido JBL Tune 510BT Bluetooth Preto', 'ink'),
                ('→ same product', 'aqua', 1),
                ('', 'ink'),
                ('Chuveiro Elétrico Lorenzetti Acqua Duo 220V 7800W', 'ink'),
                ('Chuveiro Eletrico Lorenzetti Acqua Duo 127V 5500W', 'ink'),
                ('✗ same barcode, refused: power_w 7800 vs 5500', 'orange', 1)],
      'mono': 7.4,
      'checks_t': 'what it checks',
      'checks': ['accents, plurals, phonetic key',
                 'GTIN digit and placeholder codes',
                 '110V vs 220V, 400g vs 500g',
                 'sizes, colours, pack quantities',
                 'every link says which rule',
                 '448 golden texts, 2 runtimes'],
      'foot': 'no dependencies · Python and .NET · rules from a 2019–2022 price-comparison catalog'},
 '.pt-BR': {'tag': 'Mesmo produto,\nou só parece igual?',
            'sub': 'matching de produtos em português do Brasil,\nem Python e .NET com o mesmo resultado',
            'head': 'dedupkit · dois grupos',
            'lines': [('Fone de Ouvido sem Fio JBL Tune 510BT Preto', 'ink'),
                      ('FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO', 'ink'),
                      ('Fone Ouvido JBL Tune 510BT Bluetooth Preto', 'ink'),
                      ('→ mesmo produto', 'aqua', 1),
                      ('', 'ink'),
                      ('Chuveiro Elétrico Lorenzetti Acqua Duo 220V 7800W', 'ink'),
                      ('Chuveiro Eletrico Lorenzetti Acqua Duo 127V 5500W', 'ink'),
                      ('✗ mesmo código, recusado: potência 7800 vs 5500', 'orange', 1)],
            'mono': 7.4,
            'checks_t': 'o que ela confere',
            'checks': ['acentos, plurais, chave fonética',
                       'dígito do GTIN e códigos falsos',
                       '110V vs 220V, 400g vs 500g',
                       'tamanhos, cores, quantidades',
                       'cada ligação diz a regra',
                       '448 textos de teste, 2 linguagens'],
            'foot': 'sem dependências · Python e .NET · regras de um comparador de preços de 2019–2022'}}

OUT.mkdir(parents=True, exist_ok=True)
for suf, t in T.items():
    fig = plt.figure(figsize=(11, 5.6), dpi=110); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 110); ax.set_ylim(0, 56); ax.axis("off")
    ax.add_patch(FancyBboxPatch((5, 41), 9, 9, boxstyle="round,pad=0,rounding_size=2", fc=C[MARK_COLOR], ec="none"))
    ax.text(9.5, 45.5, MARK, color="white", fontsize=17 if len(MARK) > 1 else 22, weight="bold", ha="center", va="center")
    ax.text(17, 45.5, NAME, fontsize=24 if len(NAME) <= 10 else 18.5, weight="bold", color=INK, va="center")
    ax.text(5, 32.5, t["tag"], fontsize=15, color=INK, va="center", linespacing=1.25)
    ax.text(5, 22.5, t["sub"], fontsize=10.5, color=MUTED, va="center", linespacing=1.35)
    # panel: what it looks like
    px, py, pw, ph = 39, 8, 39, 42
    ax.add_patch(FancyBboxPatch((px, py), pw, ph, boxstyle="round,pad=0,rounding_size=1.2", fc="white", ec=LINE, lw=1.2))
    ax.text(px + 2, py + ph - 3.5, t["head"], fontsize=10.5, weight="bold", color=INK)
    step = min(4.6, 34 / max(len(t["lines"]), 1))
    for i, (s, col, *bold) in enumerate(t["lines"]):
        ax.text(px + 2, py + ph - 9 - i * step, s, fontsize=t.get("mono", 8.3), color=C[col], family="monospace",
                weight="bold" if bold else "normal")
    # checklist
    tx = 81
    ax.text(tx, 46, t["checks_t"], fontsize=11, weight="bold", color=INK)
    for j, s in enumerate(t["checks"]):
        ax.text(tx, 40.5 - j * 5, "✓  " + s, fontsize=9, color=INK)
    ax.text(5, 3.2, t["foot"], fontsize=8.6, color=MUTED)
    ax.text(105, 3.2, "github.com/CaiqueDourado", fontsize=8.6, color=MUTED, ha="right")
    fig.savefig(OUT / f"cover{suf}.png", facecolor=BG); plt.close(fig)
print("ok")
