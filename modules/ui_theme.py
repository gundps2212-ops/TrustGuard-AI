from __future__ import annotations

import streamlit as st


TRUSTGUARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --tg-bg: #07111f;
  --tg-panel: rgba(15, 29, 49, .78);
  --tg-panel-strong: #10213a;
  --tg-line: rgba(148, 183, 220, .16);
  --tg-text: #e8f1ff;
  --tg-muted: #91a5bf;
  --tg-cyan: #42d9f5;
  --tg-blue: #6488ff;
  --tg-green: #49dcb1;
}
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp {
  color: var(--tg-text);
  background:
    radial-gradient(ellipse at 12% 0%, rgba(41, 104, 174, .22), transparent 34%),
    radial-gradient(ellipse at 88% 12%, rgba(37, 197, 218, .12), transparent 28%),
    linear-gradient(145deg, #07111f 0%, #091629 48%, #07111f 100%);
}
.stApp:before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  opacity: .16;
  background-image: linear-gradient(rgba(120,170,220,.08) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(120,170,220,.08) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: linear-gradient(to bottom, black, transparent 88%);
}
[data-testid="stHeader"] { background: rgba(7,17,31,.72); backdrop-filter: blur(16px); }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { max-width: 1440px; padding-top: 2.2rem; padding-bottom: 3rem; position: relative; z-index: 1; }
h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -.035em; color: #f1f7ff; }
h1 { font-size: clamp(2rem, 4vw, 3.25rem) !important; font-weight: 700 !important; }
h2 { font-size: clamp(1.45rem, 2.5vw, 2rem) !important; }
p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: #c4d3e7; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b1a2d 0%, #091525 100%);
  border-right: 1px solid var(--tg-line);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stForm"],
[data-testid="stExpander"], [data-testid="stTabs"] [data-baseweb="tab-panel"] {
  border: 1px solid var(--tg-line) !important;
  border-radius: 18px !important;
  background: linear-gradient(145deg, rgba(19,38,63,.78), rgba(10,24,42,.72)) !important;
  box-shadow: 0 14px 38px rgba(0,0,0,.16);
}
[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(24,48,77,.86), rgba(13,29,49,.82));
  border: 1px solid rgba(91,169,220,.2);
  border-radius: 17px; padding: 18px 20px;
}
[data-testid="stMetricLabel"] { color: #9fb6d2 !important; font-weight: 600; }
[data-testid="stMetricValue"] { color: #eff8ff !important; font-family: 'Space Grotesk', sans-serif; }
.stButton > button, .stDownloadButton > button {
  border-radius: 12px; min-height: 2.8rem; font-weight: 700;
  border: 1px solid rgba(91,210,238,.38);
  background: linear-gradient(105deg, #167da8, #365bd2);
  color: white; transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
  box-shadow: 0 7px 22px rgba(31,123,190,.2);
}
.stButton > button:hover, .stDownloadButton > button:hover {
  transform: translateY(-2px); filter: brightness(1.12);
  box-shadow: 0 12px 28px rgba(40,170,220,.24);
  border-color: rgba(105,229,248,.72);
}
.stButton > button:focus:not(:active), .stDownloadButton > button:focus:not(:active) { outline: 2px solid var(--tg-cyan); }
[data-baseweb="input"] > div, [data-baseweb="textarea"], [data-baseweb="select"] > div {
  background: rgba(5,16,30,.72) !important; border: 1px solid rgba(132,169,207,.24) !important;
  border-radius: 12px !important; color: #eaf4ff !important;
}
input, textarea { color: #eaf4ff !important; }
[data-baseweb="tab-list"] { gap: 8px; background: transparent; }
button[data-baseweb="tab"] {
  border-radius: 10px 10px 0 0; color: #a9bdd5; font-weight: 600;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: #61e4f7; border-bottom: 2px solid #42d9f5;
}
[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #27b8d8, #6a82ff); }
hr { border-color: rgba(148,183,220,.16) !important; }
[data-testid="stAlert"] { border-radius: 14px; border: 1px solid var(--tg-line); }
[data-testid="stFileUploader"] {
  background: rgba(8,20,36,.62); border: 1px dashed rgba(85,190,225,.4);
  border-radius: 16px; padding: 8px;
}
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--tg-line); border-radius: 14px; overflow: hidden; }
[data-testid="stMainBlockContainer"] { animation: tg-enter .55s ease both; }
@keyframes tg-enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 768px) {
  .block-container { padding: 1.1rem .85rem 2rem; }
  h1 { font-size: 1.9rem !important; }
  [data-testid="stMetric"] { padding: 13px 14px; }
  .stButton > button, .stDownloadButton > button { width: 100%; }
  [data-testid="stSidebar"] { min-width: 0; }
}
@media (prefers-reduced-motion: reduce) {
  *, *:before, *:after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}
</style>
"""


def apply_trustguard_theme() -> None:
    """Apply the premium responsive TrustGuard visual theme."""
    st.markdown(TRUSTGUARD_CSS, unsafe_allow_html=True)
