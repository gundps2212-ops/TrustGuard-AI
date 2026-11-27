from __future__ import annotations

import streamlit as st


def apply_futuristic_theme() -> None:
    """Apply a visual-only premium navy/cyan theme to Streamlit."""
    st.markdown(
        """
        <style>
        :root {
            --tg-bg: #06111f;
            --tg-panel: rgba(10, 28, 48, .82);
            --tg-line: rgba(76, 196, 255, .20);
            --tg-cyan: #55dfff;
            --tg-text: #eaf7ff;
            --tg-muted: #91abc0;
        }
        .stApp {
            color: var(--tg-text);
            background:
                radial-gradient(ellipse at 12% 0%, rgba(0, 150, 220, .16), transparent 32%),
                radial-gradient(ellipse at 88% 12%, rgba(30, 95, 210, .13), transparent 30%),
                linear-gradient(145deg, #050d18 0%, #07192b 52%, #06111f 100%);
        }
        [data-testid="stHeader"] {
            background: rgba(4, 13, 24, .72);
            backdrop-filter: blur(14px);
        }
        [data-testid="stToolbar"] { right: 1rem; }
        .block-container {
            max-width: 1440px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3 {
            color: #effaff !important;
            letter-spacing: -.025em;
        }
        h1 {
            text-shadow: 0 0 28px rgba(58, 195, 255, .18);
        }
        p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: #c5d9e8;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(13, 39, 63, .88), rgba(7, 24, 42, .78));
            border: 1px solid var(--tg-line);
            border-radius: 16px;
            padding: 16px 18px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, .16);
        }
        [data-testid="stMetricLabel"] { color: #8fb6cc !important; }
        [data-testid="stMetricValue"] { color: #e8faff !important; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--tg-line) !important;
            border-radius: 18px !important;
            background: rgba(8, 25, 43, .48);
        }
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div {
            background: rgba(5, 19, 34, .88) !important;
            border-color: rgba(92, 190, 235, .25) !important;
            border-radius: 12px !important;
        }
        input, textarea {
            color: #effaff !important;
        }
        .stButton > button, .stFormSubmitButton > button,
        [data-testid="stDownloadButton"] > button {
            border: 1px solid rgba(78, 204, 255, .38);
            border-radius: 12px;
            color: #effaff;
            background: linear-gradient(110deg, rgba(10, 117, 168, .95), rgba(35, 76, 164, .95));
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
            box-shadow: 0 5px 18px rgba(0, 142, 220, .14);
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover,
        [data-testid="stDownloadButton"] > button:hover {
            transform: translateY(-1px);
            border-color: rgba(117, 230, 255, .8);
            box-shadow: 0 8px 24px rgba(0, 174, 255, .22);
        }
        [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid var(--tg-line);
        }
        [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            color: #9bb9cc;
        }
        [aria-selected="true"][data-baseweb="tab"] {
            color: #70e2ff !important;
        }
        [data-testid="stExpander"] {
            border: 1px solid var(--tg-line);
            border-radius: 14px;
            background: rgba(7, 24, 42, .55);
        }
        hr {
            border-color: rgba(88, 180, 225, .18) !important;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #07182a, #050f1c);
            border-right: 1px solid var(--tg-line);
        }
        @media (max-width: 700px) {
            .block-container { padding: 1rem .8rem 2rem; }
            [data-testid="stMetric"] { padding: 12px; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { transition: none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
