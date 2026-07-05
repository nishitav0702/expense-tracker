import streamlit as st


# ── Reusable HTML components ──────────────────────────────────────────────────
# Each function returns a styled HTML string.
# Call with st.markdown(component_fn(...), unsafe_allow_html=True)


def glass_card(content: str, border_colour: str = "rgba(177,83,215,0.35)",
               padding: str = "1.25rem") -> str:
    """
    Generic glassmorphism card wrapper.
    Pass any HTML string as content.

    Usage:
        st.markdown(glass_card("<p>Hello</p>"), unsafe_allow_html=True)
    """
    return f"""
    <div style="
        background: rgba(14, 33, 160, 0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {border_colour};
        border-radius: 14px;
        padding: {padding};
        box-shadow: 0 8px 32px rgba(10, 10, 60, 0.35);
        margin-bottom: 1rem;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    ">
        {content}
    </div>
    """


def section_header(title: str, subtitle: str = "",
                   accent: str = "#B153D7") -> str:
    """
    Styled section header with coloured underline accent.
    Replaces plain st.subheader() for a more designed feel.

    Usage:
        st.markdown(section_header("ML Insights", "Trained on your data"),
                    unsafe_allow_html=True)
    """
    sub_html = (
        f"<p style='font-family:Inter,sans-serif; font-size:0.85rem; "
        f"color:#9090B8; margin:4px 0 0; font-weight:400;'>{subtitle}</p>"
        if subtitle else ""
    )
    return f"""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="
            font-family: 'Libre Baskerville', Georgia, serif;
            font-size: 1.35rem;
            font-weight: 700;
            color: #F0F0FF;
            margin: 0 0 6px;
            letter-spacing: -0.01em;
        ">{title}</h2>
        <div style="
            width: 48px;
            height: 3px;
            background: linear-gradient(90deg, {accent}, #F375C2);
            border-radius: 2px;
            margin-bottom: 4px;
        "></div>
        {sub_html}
    </div>
    """


def risk_badge(category: str, label: str,
               spent: float, budget: float,
               colour: str = "#B153D7") -> str:
    """
    Styled risk card for ML insights page.
    Shows category name, risk label, spent vs budget.

    label: "Safe" | "Warning" | "Danger"
    """
    label_colours = {
        "Safe":    ("#1D9E75", "rgba(29,158,117,0.15)"),
        "Warning": ("#F59E0B", "rgba(245,158,11,0.15)"),
        "Danger":  ("#EF4444", "rgba(239,68,68,0.15)"),
    }
    label_icons = {
        "Safe":    "🟢",
        "Warning": "🟠",
        "Danger":  "🔴",
    }

    lc, lb = label_colours.get(label, ("#B153D7", "rgba(177,83,215,0.15)"))
    icon   = label_icons.get(label, "⚪")
    pct    = int(spent / budget * 100) if budget > 0 else 0

    return f"""
    <div style="
        background: rgba(14, 33, 160, 0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {lc}55;
        border-left: 4px solid {lc};
        border-radius: 14px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.75rem;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    ">
        <div style="
            font-family: Inter, sans-serif;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #9090B8;
            margin-bottom: 6px;
        ">{category}</div>
        <div style="
            display: flex;
            align-items: center;
            justify-content: space-between;
        ">
            <div style="
                font-family: 'Libre Baskerville', Georgia, serif;
                font-size: 1.3rem;
                font-weight: 700;
                color: {lc};
            ">{icon} {label}</div>
            <div style="
                background: {lb};
                border-radius: 20px;
                padding: 3px 10px;
                font-family: Inter, sans-serif;
                font-size: 0.78rem;
                font-weight: 600;
                color: {lc};
            ">{pct}%</div>
        </div>
        <div style="
            font-family: Inter, sans-serif;
            font-size: 0.8rem;
            color: #9090B8;
            margin-top: 6px;
        ">Rs{spent:,.0f} spent · Rs{budget:,.0f} budget</div>
    </div>
    """


def stat_card(label: str, value: str,
              delta: str = "", delta_positive: bool = True,
              accent: str = "#B153D7") -> str:
    """
    Large number stat card — replaces st.metric() for
    pages where you want more visual control.

    Usage:
        st.markdown(stat_card("Total spent", "Rs 4,920",
                    delta="+Rs 420 vs last month",
                    delta_positive=False), unsafe_allow_html=True)
    """
    delta_colour = "#1D9E75" if delta_positive else "#EF4444"
    delta_html   = (
        f"<div style='font-family:Inter,sans-serif; font-size:0.78rem; "
        f"color:{delta_colour}; margin-top:4px;'>{delta}</div>"
        if delta else ""
    )

    return f"""
    <div style="
        background: rgba(14, 33, 160, 0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(177,83,215,0.35);
        border-top: 3px solid {accent};
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 8px 32px rgba(10,10,60,0.35);
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
        margin-bottom: 0.5rem;
    ">
        <div style="
            font-family: Inter, sans-serif;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: #9090B8;
            margin-bottom: 8px;
        ">{label}</div>
        <div style="
            font-family: 'Libre Baskerville', Georgia, serif;
            font-size: 1.75rem;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: -0.02em;
            line-height: 1;
        ">{value}</div>
        {delta_html}
    </div>
    """


def tip_card(headline: str, detail: str,
             icon: str = "💡", colour: str = "#B153D7") -> str:
    """
    Styled saving tip card for AI insights page.
    Used inside st.expander() for the accordion effect.

    Usage:
        with st.expander(f"{icon} {headline}"):
            st.markdown(tip_card(headline, detail, icon, colour),
                        unsafe_allow_html=True)
    """
    return f"""
    <div style="
        border-left: 3px solid {colour};
        background: rgba(77, 47, 178, 0.15);
        border-radius: 0 10px 10px 0;
        padding: 10px 14px;
        font-family: Inter, sans-serif;
        font-size: 0.9rem;
        color: #C8C8E8;
        line-height: 1.65;
    ">
        {detail}
    </div>
    """


def ai_commentary(text: str) -> str:
    """
    Styled pull quote for AI summary text.
    Italic serif text in a glassy left-bordered card.
    """
    return f"""
    <div style="
        background: rgba(14, 33, 160, 0.3);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-left: 4px solid #B153D7;
        border-radius: 0 14px 14px 0;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
        font-family: 'Libre Baskerville', Georgia, serif;
        font-size: 0.95rem;
        font-style: italic;
        color: #F0F0FF;
        line-height: 1.75;
    ">
        💬 {text}
    </div>
    """


def page_banner(title: str, subtitle: str,
                icon: str = "") -> str:
    """
    Full-width glassy banner for page headers.
    Replaces plain st.header() for key pages.

    Usage:
        st.markdown(page_banner("Dashboard", "Your spending at a glance", "📊"),
                    unsafe_allow_html=True)
    """
    return f"""
    <div style="
        background: linear-gradient(
            135deg,
            rgba(77, 47, 178, 0.35) 0%,
            rgba(177, 83, 215, 0.20) 100%
        );
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(177, 83, 215, 0.3);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.75rem;
        box-shadow: 0 8px 32px rgba(10,10,60,0.3);
    ">
        <div style="
            font-family: 'Libre Baskerville', Georgia, serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: -0.02em;
            margin-bottom: 4px;
        ">{icon} {title}</div>
        <div style="
            font-family: Inter, sans-serif;
            font-size: 0.88rem;
            color: #9090B8;
            font-weight: 400;
        ">{subtitle}</div>
    </div>
    """


def category_pill(category: str, colour: str) -> str:
    """
    Small coloured pill badge for category labels in tables.

    Usage:
        st.markdown(category_pill("Food", "#FF6B6B"),
                    unsafe_allow_html=True)
    """
    return f"""
    <span style="
        background: {colour}22;
        border: 1px solid {colour}88;
        color: {colour};
        font-family: Inter, sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
        letter-spacing: 0.03em;
    ">{category}</span>
    """


def empty_state(message: str, icon: str = "💸") -> str:
    """
    Styled empty state for when there's no data.
    Replaces plain st.info() for a more polished look.
    """
    return f"""
    <div style="
        text-align: center;
        padding: 3rem 2rem;
        background: rgba(14, 33, 160, 0.2);
        backdrop-filter: blur(12px);
        border: 1px dashed rgba(177, 83, 215, 0.4);
        border-radius: 20px;
        margin: 1rem 0;
    ">
        <div style="font-size: 3rem; margin-bottom: 1rem;">{icon}</div>
        <div style="
            font-family: 'Libre Baskerville', Georgia, serif;
            font-size: 1.1rem;
            color: #C8C8E8;
            font-weight: 400;
        ">{message}</div>
    </div>
    """