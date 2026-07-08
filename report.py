"""Full weather report generation, rendered as HTML or PDF.

The report aggregates everything the system knows: collection status,
current settings, summaries over several windows, and the latest records.
"""

from datetime import datetime
from typing import Dict, List

from fpdf import FPDF

from analyse import Analyse
from config import settings
from data_json_manager import JSONDataManager

SUMMARY_WINDOWS = [6, 24, 72, 168]
LATEST_RECORDS_IN_REPORT = 24


async def build_report_data(city: Dict, data_manager: JSONDataManager,
                            analyser: Analyse, scheduler_status: Dict) -> Dict:
    data = await data_manager.read_data()

    summaries = {}
    for window in SUMMARY_WINDOWS:
        if len(data) >= 2 and window <= max(len(data), SUMMARY_WINDOWS[0]):
            summaries[window] = await analyser.get_weather_summary(window)

    city_scheduler = scheduler_status.get("cities", {}).get(city["id"], {})

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "city": {
            "id": city["id"],
            "name": city["name"],
            "country": city["country"],
            "latitude": city["latitude"],
            "longitude": city["longitude"],
        },
        "collection": {
            "total_records": len(data),
            "first_record": data[0].get("timestamp", "-") if data else "-",
            "last_record": data[-1].get("timestamp", "-") if data else "-",
            "interval_minutes": settings.fetch_interval_minutes,
            "scheduler_running": scheduler_status.get("running"),
            "last_success_at": city_scheduler.get("last_success_at"),
            "collection_failures": city_scheduler.get("failures", 0),
        },
        "summaries": summaries,
        "latest_records": list(reversed(data[-LATEST_RECORDS_IN_REPORT:])),
    }


def _summary_rows(summary: Dict) -> List:
    temp_range = summary.get("temp_range") or {}
    calm = summary.get("calm_periods") or {}
    rows = [
        ("Average temperature", f'{summary.get("avg_temperature", "-")} C'),
        ("Temperature min / max", f'{temp_range.get("min", "-")} / {temp_range.get("max", "-")} C'),
        ("Temperature range", f'{temp_range.get("range", "-")} C'),
        ("Average wind speed", f'{summary.get("avg_windspeed", "-")} km/h'),
        ("Peak wind speed", f'{summary.get("peak_windspeed", "-")} km/h'),
        ("Dominant wind direction", f'{summary.get("dominant_wind_direction", "-")} deg'),
        ("Wind direction variability", f'{summary.get("wind_variability", "-")} deg (std dev)'),
        ("Calm periods", f'{calm.get("calm_periods", "-")} of {calm.get("total_periods", "-")}'
                         f' ({calm.get("calm_percentage", "-")}%)'),
        ("Data points analysed", str(summary.get("data_points", "-"))),
    ]
    # Optional metrics only appear once such data has been collected.
    if "avg_apparent_temperature" in summary:
        rows.append(("Average feels-like temperature", f'{summary["avg_apparent_temperature"]} C'))
    if "avg_humidity" in summary:
        rows.append(("Average humidity", f'{summary["avg_humidity"]} %'))
    if "total_precipitation" in summary:
        rows.append(("Total precipitation", f'{summary["total_precipitation"]} mm'))
    if "avg_pressure" in summary:
        rows.append(("Average surface pressure", f'{summary["avg_pressure"]} hPa'))
    return rows


def render_report_html(report: Dict, admin_path: str) -> str:
    sections = []
    for window, summary in report["summaries"].items():
        if not summary:
            continue
        rows = "".join(
            f"<tr><td>{label}</td><td>{value}</td></tr>"
            for label, value in _summary_rows(summary)
        )
        sections.append(
            f'<div class="card"><h3>Summary - last {window} records</h3>'
            f'<table><tbody>{rows}</tbody></table></div>'
        )

    record_rows = "".join(
        f"<tr><td>{r.get('id', '-')}</td><td>{r.get('timestamp', r.get('time', '-'))}</td>"
        f"<td>{r.get('temperature', '-')}</td><td>{r.get('windspeed', '-')}</td>"
        f"<td>{r.get('winddirection', '-')}</td><td>{r.get('weathercode', '-')}</td>"
        f"<td>{'Day' if r.get('is_day') else 'Night'}</td></tr>"
        for r in report["latest_records"]
    )

    collection = report["collection"]
    city = report["city"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weather Report - {city["name"]}</title>
<link rel="stylesheet" href="{admin_path}/static/admin.css">
</head>
<body>
<nav class="navbar">
  <div class="container">
    <div class="nav-brand"><h1>Weather Admin</h1></div>
    <ul class="nav-menu">
      <li><a href="{admin_path}/dashboard">Dashboard</a></li>
      <li><a href="{admin_path}/report?city={city["id"]}" class="active">Report</a></li>
      <li><a href="#" id="logout-link">Logout</a></li>
    </ul>
  </div>
</nav>
<div class="container main-content">
  <div class="header">
    <h2>Full Weather Report - {city["name"]}, {city["country"]}</h2>
    <div class="controls">
      <a class="btn" href="{admin_path}/report/pdf?city={city["id"]}">Download PDF</a>
      <a class="btn btn-secondary" href="{admin_path}/api/download/csv?city={city["id"]}">Download CSV</a>
      <a class="btn btn-secondary" href="{admin_path}/api/download/json?city={city["id"]}">Download JSON</a>
    </div>
  </div>

  <div class="card">
    <h3>Report Information</h3>
    <table><tbody>
      <tr><td>Generated at</td><td>{report["generated_at"]}</td></tr>
      <tr><td>City</td><td>{city["name"]}, {city["country"]} (lat {city["latitude"]}, lon {city["longitude"]})</td></tr>
      <tr><td>Total records collected</td><td>{collection["total_records"]}</td></tr>
      <tr><td>First record</td><td>{collection["first_record"]}</td></tr>
      <tr><td>Last record</td><td>{collection["last_record"]}</td></tr>
      <tr><td>Collection interval</td><td>every {collection["interval_minutes"]} minutes</td></tr>
      <tr><td>Scheduler running</td><td>{collection["scheduler_running"]}</td></tr>
      <tr><td>Collection failures for this city</td><td>{collection["collection_failures"]}</td></tr>
      <tr><td>Last successful collection</td><td>{collection["last_success_at"] or "-"}</td></tr>
    </tbody></table>
  </div>

  {"".join(sections) if sections else '<div class="card"><p>Not enough data collected yet for summaries.</p></div>'}

  <div class="card">
    <h3>Latest {len(report["latest_records"])} Records</h3>
    <div class="table-container">
      <table>
        <thead><tr><th>ID</th><th>Timestamp</th><th>Temp (C)</th><th>Wind (km/h)</th>
        <th>Direction (deg)</th><th>Code</th><th>Day/Night</th></tr></thead>
        <tbody>{record_rows or '<tr><td colspan="7">No records collected yet.</td></tr>'}</tbody>
      </table>
    </div>
  </div>
</div>
<script>
document.getElementById('logout-link').addEventListener('click', async function (e) {{
  e.preventDefault();
  await fetch('{admin_path}/api/logout', {{ method: 'POST' }});
  window.location.href = '{admin_path}';
}});
</script>
</body>
</html>"""


class _ReportPDF(FPDF):
    title_text = "Weather Analysis Report"

    def header(self):
        self.set_font("helvetica", "B", 14)
        self.cell(0, 8, self.title_text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(120, 120, 120)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.set_font("helvetica", "B", 11)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(1)

    def key_value_table(self, rows: List):
        self.set_font("helvetica", "", 9)
        for label, value in rows:
            self.set_font("helvetica", "B", 9)
            self.cell(70, 6, str(label), border=1)
            self.set_font("helvetica", "", 9)
            self.cell(0, 6, str(value), border=1, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)


def render_report_pdf(report: Dict) -> bytes:
    city = report["city"]
    pdf = _ReportPDF()
    pdf.title_text = f'Weather Analysis Report - {city["name"]}, {city["country"]}'
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    collection = report["collection"]

    pdf.section_title("Report Information")
    pdf.key_value_table([
        ("Generated at", report["generated_at"]),
        ("City", f'{city["name"]}, {city["country"]} (lat {city["latitude"]}, lon {city["longitude"]})'),
        ("Total records collected", collection["total_records"]),
        ("First record", collection["first_record"]),
        ("Last record", collection["last_record"]),
        ("Collection interval", f'every {collection["interval_minutes"]} minutes'),
        ("Scheduler running", collection["scheduler_running"]),
        ("Collection failures for this city", collection["collection_failures"]),
        ("Last successful collection", collection["last_success_at"] or "-"),
    ])

    for window, summary in report["summaries"].items():
        if not summary:
            continue
        pdf.section_title(f"Summary - last {window} records")
        pdf.key_value_table(_summary_rows(summary))

    records = report["latest_records"]
    pdf.section_title(f"Latest {len(records)} Records")
    if records:
        headers = ["ID", "Timestamp", "Temp (C)", "Wind (km/h)", "Dir (deg)", "Code", "Day/Night"]
        widths = [12, 52, 22, 26, 22, 16, 24]
        pdf.set_font("helvetica", "B", 8)
        for head, width in zip(headers, widths):
            pdf.cell(width, 6, head, border=1)
        pdf.ln()
        pdf.set_font("helvetica", "", 8)
        for r in records:
            timestamp = str(r.get("timestamp", r.get("time", "-")))[:19].replace("T", " ")
            cells = [
                str(r.get("id", "-")), timestamp, str(r.get("temperature", "-")),
                str(r.get("windspeed", "-")), str(r.get("winddirection", "-")),
                str(r.get("weathercode", "-")), "Day" if r.get("is_day") else "Night",
            ]
            for value, width in zip(cells, widths):
                pdf.cell(width, 6, value, border=1)
            pdf.ln()
    else:
        pdf.set_font("helvetica", "", 9)
        pdf.cell(0, 6, "No records collected yet.", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
