# Internships mission notifications: run-report email HTML + telegram text.
# Ported from the original orchestrator; logic unchanged.
from datetime import datetime as dt


def _score_color(score):
    return "#16a34a" if score >= 30 else "#ca8a04"


def build_report_html(stats, highlights, recent_items, dashboard_url):
    now_str = dt.now().strftime("%B %d, %Y at %I:%M %p")
    saved_count = stats["new_saved"]
    total_found = stats["total_discovered"]

    listings_html = ""
    for item in highlights:
        score = item.relevance_score or 0
        listings_html += (
            "<tr>\n"
            '<td style="padding:12px;border-bottom:1px solid #27272a;">\n'
            '<a href="{url}" style="color:#fafafa;font-weight:600;text-decoration:none;">{title}</a><br>\n'
            '<span style="color:#a1a1aa;font-size:13px;">{company} \u00b7 {location}</span>\n'
            "</td>\n"
            '<td style="padding:12px;border-bottom:1px solid #27272a;text-align:right;">\n'
            '<span style="background:{color};color:white;padding:3px 8px;border-radius:4px;font-size:12px;">{score:.0f}%</span>\n'
            "</td></tr>"
        ).format(
            url=item.url or "#",
            title=item.title or "Untitled",
            company=item.company or "",
            location=item.location or "Location N/A",
            color=_score_color(score),
            score=score,
        )
    if not listings_html:
        listings_html = (
            "<tr><td colspan=2 style='padding:20px;text-align:center;color:#71717a;'>"
            "No high-scoring new listings this run</td></tr>"
        )

    all_rows = ""
    for item in recent_items:
        score = item.relevance_score or 0
        all_rows += (
            "<tr>\n"
            '<td style="padding:8px 12px;border-bottom:1px solid #1c1c1f;font-size:13px;">\n'
            '<a href="{url}" style="color:#a1a1aa;text-decoration:none;">{title}</a></td>\n'
            '<td style="padding:8px 12px;border-bottom:1px solid #1c1c1f;font-size:12px;color:#71717a;">{company}</td>\n'
            '<td style="padding:8px 12px;border-bottom:1px solid #1c1c1f;font-size:12px;color:#71717a;text-align:right;">{score:.0f}%</td>\n'
            "</tr>"
        ).format(url=item.url or "#", title=item.title or "Untitled",
                 company=item.company or "", score=score)

    all_section = ""
    if all_rows:
        all_section = (
            '<div style="background:#18181b;border:1px solid #27272a;border-radius:8px;margin-bottom:24px;">\n'
            '<div style="padding:16px 20px;border-bottom:1px solid #27272a;">'
            '<h2 style="color:#fafafa;font-size:14px;margin:0;">All New Listings</h2></div>\n'
            '<table style="width:100%;border-collapse:collapse;">\n'
            '<tr style="background:#0f0f10;">\n'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;color:#71717a;">Title</th>\n'
            '<th style="padding:8px 12px;text-align:left;font-size:11px;color:#71717a;">Company</th>\n'
            '<th style="padding:8px 12px;text-align:right;font-size:11px;color:#71717a;">Match</th>\n'
            "</tr>{rows}</table></div>"
        ).format(rows=all_rows)

    html = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head>\n"
        '<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,sans-serif;">\n'
        '<div style="max-width:600px;margin:0 auto;padding:40px 20px;">\n'
        '<h1 style="color:#fafafa;font-size:22px;margin:0 0 4px 0;">Scout Report</h1>\n'
        '<p style="color:#71717a;font-size:13px;margin:0 0 32px 0;">{now}</p>\n'
        '<div style="display:flex;gap:12px;margin-bottom:32px;">\n'
        '<div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;text-align:center;">\n'
        '<div style="font-size:28px;font-weight:700;color:#fafafa;">{saved}</div>\n'
        '<div style="font-size:11px;color:#71717a;text-transform:uppercase;">New Found</div></div>\n'
        '<div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;text-align:center;">\n'
        '<div style="font-size:28px;font-weight:700;color:#fafafa;">{strong}</div>\n'
        '<div style="font-size:11px;color:#71717a;text-transform:uppercase;">Strong Matches</div></div>\n'
        '<div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;text-align:center;">\n'
        '<div style="font-size:28px;font-weight:700;color:#fafafa;">{total}</div>\n'
        '<div style="font-size:11px;color:#71717a;text-transform:uppercase;">Scanned</div></div></div>\n'
        '<div style="background:#18181b;border:1px solid #27272a;border-radius:8px;margin-bottom:24px;">\n'
        '<div style="padding:16px 20px;border-bottom:1px solid #27272a;">'
        '<h2 style="color:#fafafa;font-size:14px;margin:0;">Top Matches</h2></div>\n'
        '<table style="width:100%;border-collapse:collapse;">{listings}</table></div>\n'
        "{all_section}\n"
        '<div style="text-align:center;padding:20px;">\n'
        '<a href="{dash}" style="background:#fafafa;color:#0a0a0a;padding:12px 24px;border-radius:6px;'
        'text-decoration:none;font-weight:600;">Open Dashboard</a>\n'
        "</div></div></body></html>"
    ).format(now=now_str, saved=saved_count, strong=len(highlights),
             total=total_found, listings=listings_html,
             all_section=all_section, dash=dashboard_url)

    subject = ("Scout: {} new internships found".format(saved_count)
               if saved_count > 0 else "Scout: No new listings this run")
    return subject, html


def build_telegram_message(stats, highlights, dashboard_url):
    saved_count = stats["new_saved"]
    lines = ["<b>Scout: {} new internships found</b>".format(saved_count), ""]
    high = [i for i in highlights if (i.relevance_score or 0) >= 30]
    if high:
        lines.append("<b>Top matches:</b>")
        for item in high[:5]:
            lines.append("\u2022 {} @ {} ({:.0f}%)".format(
                item.title or "Untitled", item.company or "",
                item.relevance_score or 0))
    lines.append("")
    lines.append(dashboard_url)
    return "\n".join(lines)
