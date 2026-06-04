"""
Generate clean technical architecture diagrams for FYP report.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'report_screenshots')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def draw_architecture():
    """Three-Layer Detection Architecture — clean block diagram"""
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis('off')
    # Title removed — caption provided in Word document as Figure D1

    bd = '#37474F'  # border

    def box(x, y, w, h, txt, col, fs=9, sub=None):
        r = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                                     facecolor=col, edgecolor=bd, linewidth=1.6)
        ax.add_patch(r)
        dy = 0.14 if sub else 0
        ax.text(x + w / 2, y + h / 2 + dy, txt, ha='center', va='center',
                fontsize=fs, fontweight='bold', wrap=True)
        if sub:
            ax.text(x + w / 2, y + h / 2 - 0.18, sub, ha='center', va='center',
                    fontsize=7, style='italic', color='#555')

    def arr(x1, y1, x2, y2, lbl=None, c='#455A64'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.6))
        if lbl:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx + 0.05, my + 0.14, lbl, fontsize=7, color=c, ha='center')

    # ---- Row 1: Video Input ----
    box(4.5, 7.8, 3.5, 0.8, 'Video Input', '#E3F2FD', 11, 'MP4 / MOV / AVI')

    # ---- Row 2: Extraction layer ----
    box(0.5, 6.2, 2.0, 0.8, 'OpenCV', '#FFF3E0', sub='Frame Extraction')
    box(4.0, 6.2, 2.2, 0.8, 'EasyOCR', '#FFF3E0', sub='OCR (CN + EN)')
    box(8.5, 6.2, 2.2, 0.8, 'Whisper', '#FFF3E0', sub='ASR (base)')

    arr(5.5, 7.8, 1.5, 7.0)
    arr(6.25, 7.8, 5.1, 7.0)
    arr(7.0, 7.8, 9.6, 7.0)

    # ---- Row 2.5: Chinese text filter ----
    box(3.5, 4.8, 2.8, 0.7, 'Chinese Text Filter', '#FFF8E1', sub='Regex remove ASCII')
    arr(5.1, 6.2, 4.9, 5.5, 'OCR text')

    # ---- Row 3: Three detection layers ----
    box(0.3, 3.2, 2.5, 0.9, 'Layer 1: MacBERT', '#E8F5E9', 10, 'w=0.3 | F1=0.933')
    box(4.0, 3.2, 3.0, 0.9, 'Layer 2: TF-IDF\nEnsemble', '#F3E5F5', 10, 'w=0.1 | Acc=94.72%')
    box(8.2, 3.2, 2.8, 0.9, 'Layer 3: Rule Engine', '#FBE9E7', 10, 'w=0.2 | 71 keywords')

    arr(4.9, 4.8, 1.55, 4.1, 'Filtered')
    arr(5.1, 6.2, 5.5, 4.1, 'Raw text')
    arr(5.1, 6.2, 9.6, 4.1, 'Raw text')

    # ---- Row 3 right: ASR-OCR Conflict ----
    box(8.2, 5.0, 3.0, 0.7, 'ASR-OCR Conflict', '#FFCCBC', 9, 'Jaccard + keyword rules')
    arr(6.2, 6.55, 8.2, 5.55, 'OCR')
    arr(9.6, 6.2, 9.7, 5.7, 'ASR')

    # ---- Row 4: Fusion ----
    box(2.5, 1.5, 4.5, 0.9, 'Weighted Fusion + Safety Valve', '#FFEBEE', 11,
        'S = 0.3·BERT + 0.1·TFIDF + 0.2·Rule  (th=0.6)')
    arr(1.55, 3.2, 3.8, 2.4, 'S_bert')
    arr(5.5, 3.2, 4.75, 2.4, 'S_tfidf')
    arr(9.6, 3.2, 5.8, 2.4, 'S_rule')
    arr(9.7, 5.0, 6.5, 2.4, 'Conflict ↑', '#D32F2F')

    # ---- Row 4 right: GPT ----
    box(8.5, 1.5, 3.0, 0.9, 'GPT-4.1\nFact-Check', '#E0F7FA', 11, 'Async  3-6 s')
    arr(7.0, 1.95, 8.5, 1.95, 'Text')

    # ---- Row 5: Output ----
    box(3.5, 0.0, 3.5, 0.7, 'Risk: Safe / Warning / Danger', '#F1F8E9', 11)
    arr(4.75, 1.5, 5.0, 0.7, '')
    arr(10.0, 1.5, 6.0, 0.7, 'Verdict ↑', '#D32F2F')

    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, 'fig3_architecture.png')
    plt.savefig(p, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved {p}')


def draw_sse_sequence():
    """SSE Streaming Sequence Diagram"""
    fig, ax = plt.subplots(figsize=(12, 9.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')
    # Title removed — caption provided in Word document as Figure D2

    cols = [1.8, 4.5, 7.2, 10.0]
    names = ['Frontend\n(React)', 'Backend\n(FastAPI)', 'AI Models\n(BERT+TFIDF\n+Rule)', 'GPT-4.1\n(HKBU API)']
    for x, n in zip(cols, names):
        ax.text(x, 9.5, n, ha='center', va='center', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.35', fc='#E3F2FD', ec='#1565C0', lw=1.2))
        ax.plot([x, x], [0.2, 9.1], color='#B0BEC5', ls='--', lw=0.9)

    def msg(y, xf, xt, txt, c='#455A64'):
        ax.annotate('', xy=(xt, y), xytext=(xf, y),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.2))
        d = 0.15 if xt > xf else -0.15
        ax.text(xf + d, y + 0.13, txt, fontsize=7.5, color=c,
                ha='left' if xt > xf else 'right', va='bottom')

    def self_msg(y, x, txt, c='#666'):
        ax.annotate('', xy=(x + 0.9, y - 0.12), xytext=(x, y),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1,
                                    connectionstyle='arc3,rad=-0.3'))
        ax.text(x + 1.0, y + 0.05, txt, fontsize=7.5, color=c, ha='left')

    msg(8.6, cols[0], cols[1], 'POST /api/detect/stream', '#1565C0')
    self_msg(8.0, cols[1], 'Frame extraction (0.3 s)')
    msg(7.4, cols[1], cols[0], 'SSE: "frame"', '#2E7D32')
    self_msg(6.9, cols[1], 'OCR frame-1 (1.5 s)')
    msg(6.3, cols[1], cols[0], 'SSE: "ocr" {text}', '#2E7D32')
    msg(5.8, cols[1], cols[2], 'Analyze text', '#1565C0')
    msg(5.3, cols[2], cols[1], 'S_bert, S_tfidf, S_rule', '#7B1FA2')
    msg(4.7, cols[1], cols[0], 'SSE: "ai" {scores} ← ~2.5 s', '#D32F2F')
    self_msg(4.2, cols[1], 'ASR Whisper (parallel)')
    msg(3.6, cols[1], cols[0], 'SSE: "asr" {transcript}', '#2E7D32')
    self_msg(3.1, cols[1], 'Conflict detection')
    msg(2.5, cols[1], cols[0], 'SSE: "conflict" (if any)', '#EF6C00')
    msg(2.0, cols[1], cols[3], 'GPT fact-check (async)', '#1565C0')
    msg(1.3, cols[3], cols[1], 'JSON verdict', '#7B1FA2')
    msg(0.8, cols[1], cols[0], 'SSE: "gpt" {verdict, claims}', '#D32F2F')

    ax.text(0.4, 8.6, 't = 0 s', fontsize=8, color='#999')
    ax.text(0.4, 4.7, 't ≈ 2.5 s', fontsize=8, color='#D32F2F', fontweight='bold')
    ax.text(0.4, 0.8, 't ≈ 8–12 s', fontsize=8, color='#999')

    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, 'fig4_sse_sequence.png')
    plt.savefig(p, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved {p}')


def draw_breakthrough_architecture():
    """Four-breakthrough consumer-side pipeline filling platform blind spots."""
    fig, ax = plt.subplots(figsize=(13, 9.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10)
    ax.axis('off')

    bd = '#37474F'

    def box(x, y, w, h, txt, col, fs=9, sub=None):
        r = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                                     facecolor=col, edgecolor=bd, linewidth=1.6)
        ax.add_patch(r)
        dy = 0.16 if sub else 0
        ax.text(x + w / 2, y + h / 2 + dy, txt, ha='center', va='center',
                fontsize=fs, fontweight='bold')
        if sub:
            ax.text(x + w / 2, y + h / 2 - 0.20, sub, ha='center', va='center',
                    fontsize=7, style='italic', color='#555')

    def group(x, y, w, h, title, col):
        r = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                                     facecolor=col, edgecolor='#90A4AE',
                                     linewidth=1.2, linestyle='--', alpha=0.5)
        ax.add_patch(r)
        ax.text(x + 0.15, y + h - 0.22, title, ha='left', va='center',
                fontsize=8, fontweight='bold', color='#37474F')

    def arr(x1, y1, x2, y2, lbl=None, c='#455A64'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.6))
        if lbl:
            ax.text((x1 + x2) / 2 + 0.05, (y1 + y2) / 2 + 0.14, lbl,
                    fontsize=7, color=c, ha='center')

    # Input
    box(4.7, 9.0, 3.6, 0.8, 'Video / Live Clip', '#E3F2FD', 11, 'consumer-side, while watching')

    # Breakthrough 3: streaming pipeline
    group(0.4, 7.0, 12.2, 1.6, 'Breakthrough 3 — Consumer-side Streaming (SSE, sliding window)', '#E1F5FE')
    box(0.9, 7.2, 2.6, 0.9, 'Time-window Slicer', '#FFF3E0', 9, 'progress_risk events')
    box(5.2, 7.2, 2.6, 0.9, 'EasyOCR', '#FFF3E0', 9, 'subtitle / on-screen')
    box(9.0, 7.2, 2.6, 0.9, 'Whisper ASR', '#FFF3E0', 9, 'spoken script')
    arr(6.5, 9.0, 2.2, 8.1)
    arr(6.5, 9.0, 6.5, 8.1)
    arr(6.5, 9.0, 10.3, 8.1)

    # Breakthrough 1: cross-modal joint reasoning
    group(0.4, 5.0, 12.2, 1.6, 'Breakthrough 1 — Cross-modal Intent Joint Reasoning', '#F3E5F5')
    box(1.5, 5.2, 3.2, 0.9, 'OCR/ASR Dual Embedding', '#EDE7F6', 9, 'shared encoder')
    box(5.3, 5.2, 3.2, 0.9, 'CrossModalAttention', '#EDE7F6', 9, 'fusion')
    box(9.1, 5.2, 3.0, 0.9, 'Mismatch / Intent', '#FFCCBC', 9, 'divergence + coupling')
    arr(6.5, 7.2, 3.1, 6.1, 'OCR')
    arr(10.3, 7.2, 4.0, 6.1, 'ASR')
    arr(4.7, 5.65, 5.3, 5.65)
    arr(8.5, 5.65, 9.1, 5.65)

    # Breakthrough 2: cognitive multi-task model
    group(0.4, 3.0, 12.2, 1.6, 'Breakthrough 2 — Elderly Cognitive Multi-task Model', '#E8F5E9')
    box(1.5, 3.2, 4.4, 0.9, 'ElderCognitiveClassifier', '#C8E6C9', 9, 'risk grade (3-class)')
    box(6.6, 3.2, 5.5, 0.9, 'Manipulation Tactics (multi-label)', '#C8E6C9', 8.5,
        'emotion / authority / luring / urgency / AI-synthetic')
    arr(6.6, 5.2, 3.7, 4.1, 'joint signal')
    arr(5.9, 3.65, 6.6, 3.65)

    # Breakthrough 4: evidence chain
    group(0.4, 1.0, 12.2, 1.6, 'Breakthrough 4 — Evidence-chain Explainability + Case RAG', '#FFF8E1')
    box(0.9, 1.2, 3.3, 0.9, 'GPT Claim Extract/Correct', '#E0F7FA', 8.5, 'fact-check')
    box(4.6, 1.2, 3.3, 0.9, 'Case Retriever (TF-IDF)', '#FFE0B2', 8.5, 'scam_case_library')
    box(8.3, 1.2, 3.8, 0.9, 'Evidence Chain', '#FFCDD2', 9, 'tags + claims + cases')
    arr(3.7, 3.2, 2.5, 2.1, 'tags')
    arr(4.2, 1.65, 4.6, 1.65)
    arr(7.9, 1.65, 8.3, 1.65)

    # Output
    box(4.3, 0.0, 4.4, 0.7, 'Elder Alert + Evidence Panel + Family Notify', '#F1F8E9', 9.5)
    arr(10.2, 1.2, 7.0, 0.7, 'verdict', '#D32F2F')

    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, 'fig5_breakthrough_architecture.png')
    plt.savefig(p, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved {p}')


if __name__ == '__main__':
    draw_architecture()
    draw_sse_sequence()
    draw_breakthrough_architecture()
    print('Done.')
