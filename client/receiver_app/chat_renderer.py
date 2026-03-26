"""
A chat HTML megjelenítéséért felelős modul.
"""

from receiver_app.utils import escape_html


def render_chat_html(messages: list, dark: bool) -> str:
    """
    A chatüzenetekből HTML-t készít a QTextBrowser számára.
    """
    html = ["<div style='font-family: Segoe UI, Arial; padding: 4px;'>"]

    dark_in_bg = "#1f2937"
    dark_out_bg = "#1d4ed8"
    dark_important_bg = "#3f1d1d"
    dark_border = "#374151"
    dark_meta = "#94a3b8"
    dark_text = "#e5e7eb"
    dark_out_text = "#ffffff"

    light_in_bg = "#ffffff"
    light_out_bg = "#dbeafe"
    light_important_bg = "#fff1f2"
    light_border = "#e2e8f0"
    light_meta = "#64748b"
    light_text = "#0f172a"

    for msg in messages:
        is_in = msg["direction"] == "in"
        align = "left" if is_in else "right"

        if dark:
            bg = dark_in_bg if is_in else dark_out_bg
            border = dark_border
            text_color = dark_text if is_in else dark_out_text
            meta_color = dark_meta
            if msg["important"]:
                bg = dark_important_bg
                border = "#7f1d1d"
        else:
            bg = light_in_bg if is_in else light_out_bg
            border = light_border
            text_color = light_text
            meta_color = light_meta
            if msg["important"]:
                bg = light_important_bg
                border = "#fda4af"

        badge = ""
        if msg["important"]:
            badge = (
                "<div style='display:inline-block; margin-bottom:6px; "
                "padding:4px 8px; border-radius:999px; font-size:11px; font-weight:700; "
                "background:#fee2e2; color:#b91c1c;'>FONTOS</div>"
            )

        html.append(f"""
            <div style="margin-bottom: 14px; text-align: {align};">
                <div style="display:inline-block; max-width: 75%; text-align:left;">
                    {badge}
                    <div style="
                        background:{bg};
                        border:1px solid {border};
                        border-radius:18px;
                        padding:10px 12px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
                    ">
                        <div style="font-size:11px; color:{meta_color}; margin-bottom:6px; font-weight:600;">
                            {escape_html(msg['sender'])}
                        </div>
                        <div style="font-size:14px; color:{text_color}; white-space:pre-wrap; line-height:1.45;">
                            {escape_html(msg['text'])}
                        </div>
                        <div style="font-size:10px; color:{meta_color}; margin-top:8px; text-align:right;">
                            {escape_html(msg['timestamp'])}
                        </div>
                    </div>
                </div>
            </div>
        """)

    html.append("</div>")
    return "".join(html)