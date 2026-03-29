import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(24, 17))
ax.set_xlim(0, 24)
ax.set_ylim(0, 17)
ax.axis('off')
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

OVAL_CLR  = '#BDD7EE'
RECT_CLR  = '#FFF2CC'
EDGE_CLR  = '#595959'

def draw_oval(cx, cy, w, h, text, fs=9):
    e = mpatches.Ellipse((cx, cy), w, h,
                          facecolor=OVAL_CLR, edgecolor=EDGE_CLR, lw=1.2, zorder=2)
    ax.add_patch(e)
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fs,
            multialignment='center', linespacing=1.5, zorder=3)

def draw_rect(cx, cy, w, h, text, fs=8):
    r = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                        boxstyle="round,pad=0.07",
                        facecolor=RECT_CLR, edgecolor=EDGE_CLR, lw=1, zorder=2)
    ax.add_patch(r)
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fs,
            multialignment='center', linespacing=1.3, zorder=3)

def draw_line(x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color=EDGE_CLR, lw=1, zorder=1)


# ── Root ──────────────────────────────────────────────────────────────────
ROOT_X, ROOT_Y = 12, 16
ROOT_W, ROOT_H = 5.0, 1.6
draw_oval(ROOT_X, ROOT_Y, ROOT_W, ROOT_H,
          "MHIDSS\nMulti-Horizon Intelligent Decision Support System\nDay 1 – Day 32  |  In Progress",
          fs=9.5)

# ── Branch definitions ────────────────────────────────────────────────────
BX     = [3.0, 8.5, 15.5, 21.0]
BY     = 12.8
BW, BH = 3.4, 1.9

branch_labels = [
    "Planning &\nSetup\nNot Started\nDays 1–10",
    "Data Acquisition\n& Normalization\nNot Started\nDays 8–17",
    "Scoring &\nAggregation\nNot Started\nDays 17–23",
    "Output &\nTesting\nNot Started\nDays 23–32",
]

for bx, label in zip(BX, branch_labels):
    draw_oval(bx, BY, BW, BH, label, fs=9)
    draw_line(ROOT_X, ROOT_Y - ROOT_H / 2,
              bx,      BY     + BH     / 2)

# ── Task boxes ────────────────────────────────────────────────────────────
TW, TH  = 3.0, 1.35
TY_LIST = [10.4, 8.7, 7.0, 5.3]

all_tasks = [
    [   # Branch 1 – Planning & Setup
        "1.1 Requirements Analysis\nDays 1–2",
        "1.2 System Architecture Design\nDays 3–4",
        "1.3 Functional Decomposition\nDays 5–7",
        "1.4 Project Setup & Config Files\nDays 8–10",
    ],
    [   # Branch 2 – Data Acquisition & Normalization
        "2.1 Disk Cache (Parquet + TTL)\nDays 9–10",
        "2.2 Data Fetchers\n(FRED, WRDS, Technical)\nDays 11–13",
        "2.3 Base Normalizer\n& Look-ahead Bias Guard\nDays 14–15",
        "2.4 Normalizer Types\n& Integration Tests\nDays 16–17",
    ],
    [   # Branch 3 – Scoring & Aggregation
        "3.1 MacroScorer &\nTechnicalScorer\nDays 18–19",
        "3.2 FundamentalScorer\n(GICS Sectors)\nDays 18–20",
        "3.3 Scorer Integration Tests\nDay 21",
        "3.4 Horizon Aggregators\n(Short / Mid / Long)\nDays 22–23",
    ],
    [   # Branch 4 – Output & Testing
        "4.1 HTML Dashboard Formatter\nDays 24–26",
        "4.2 JSON/CSV & Terminal Output\nDay 24",
        "4.3 CLI Entry Point (main.py)\nDays 27–28",
        "4.4 End-to-End Testing\n& Documentation\nDays 29–32",
    ],
]

for bx, tasks in zip(BX, all_tasks):
    for ty, task_text in zip(TY_LIST, tasks):
        draw_rect(bx, ty, TW, TH, task_text, fs=8)
        draw_line(bx, BY - BH / 2, bx, ty + TH / 2)

plt.tight_layout(pad=0.5)
plt.savefig(
    r"C:\Users\Hyunwoo Jang\Documents\Anthropic\DS440 Assignment\Work_Breakdown_MHIDSS.png",
    dpi=150, bbox_inches='tight', facecolor='white'
)
print("Work Breakdown Structure saved.")
