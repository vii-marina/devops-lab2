#!/usr/bin/env python3
import argparse
import collections
import html
import os
import re
import sys
from datetime import datetime

# Supports typical Nginx/Apache combined-like format:
# 127.0.0.1 - - [10/Oct/2000:13:55:36 +0000] "GET /path HTTP/1.1" 200 123 "-" "User-Agent"
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<proto>[^"]+)"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\S+)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)"\s*$'
)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Parse Apache/Nginx access logs and generate an HTML report."
    )
    p.add_argument("-i", "--input", required=True, help="Path to access log file")
    p.add_argument("-o", "--output", default="report.html", help="Path to output HTML report")
    p.add_argument("--top", type=int, default=10, help="Top N entries for IPs and User-Agents")
    p.add_argument("--max-lines", type=int, default=0, help="Max lines to process (0 = all)")
    return p.parse_args()

def safe_int(x: str, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def read_lines(path: str, max_lines: int = 0):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            if max_lines and idx > max_lines:
                break
            yield line.rstrip("\n")

def parse_log_line(line: str):
    m = LOG_PATTERN.match(line)
    if not m:
        return None
    d = m.groupdict()
    d["status"] = safe_int(d["status"], 0)
    d["size"] = 0 if d["size"] == "-" else safe_int(d["size"], 0)
    return d

def make_html_report(title: str, summary: dict, top_ips, top_uas, status_counts, errors_sample):
    def tr(cells):
        return "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in cells) + "</tr>"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_ips = "\n".join(tr([ip, cnt]) for ip, cnt in top_ips) or tr(["-", 0])
    rows_uas = "\n".join(tr([ua, cnt]) for ua, cnt in top_uas) or tr(["-", 0])
    rows_status = "\n".join(tr([status, cnt]) for status, cnt in sorted(status_counts.items())) or tr(["-", 0])

    errors_html = ""
    if errors_sample:
        items = "\n".join(f"<li><code>{html.escape(x)}</code></li>" for x in errors_sample[:20])
        errors_html = f"<ul>{items}</ul>"
    else:
        errors_html = "<p>No malformed lines found.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .meta {{ color: #555; margin-bottom: 18px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f3f3f3; text-align: left; }}
    code {{ background: #f7f7f7; padding: 2px 4px; border-radius: 4px; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 18px; }}
    @media (min-width: 900px) {{
      .grid {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="meta">Generated at: {html.escape(now)}</div>

  <h2>Summary</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    {tr(["Input file", summary.get("input_file","-")])}
    {tr(["Total lines", summary.get("total_lines",0)])}
    {tr(["Parsed lines", summary.get("parsed_lines",0)])}
    {tr(["Malformed lines", summary.get("malformed_lines",0)])}
  </table>

  <div class="grid">
    <div>
      <h2>Top IP addresses</h2>
      <table>
        <tr><th>IP</th><th>Count</th></tr>
        {rows_ips}
      </table>
    </div>

    <div>
      <h2>Top User-Agents</h2>
      <table>
        <tr><th>User-Agent</th><th>Count</th></tr>
        {rows_uas}
      </table>
    </div>
  </div>

  <h2>HTTP status codes</h2>
  <table>
    <tr><th>Status</th><th>Count</th></tr>
    {rows_status}
  </table>

  <h2>Malformed lines sample</h2>
  {errors_html}

</body>
</html>
"""

def main() -> int:
    args = parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 1

    ip_counts = collections.Counter()
    ua_counts = collections.Counter()
    status_counts = collections.Counter()

    total_lines = 0
    parsed_lines = 0
    malformed_lines = 0
    errors_sample = []

    for line in read_lines(args.input, args.max_lines):
        total_lines += 1
        parsed = parse_log_line(line)
        if not parsed:
            malformed_lines += 1
            if len(errors_sample) < 50:
                errors_sample.append(line)
            continue

        parsed_lines += 1
        ip_counts[parsed["ip"]] += 1
        ua_counts[parsed["ua"]] += 1
        status_counts[parsed["status"]] += 1

    top_n = max(1, args.top)
    top_ips = ip_counts.most_common(top_n)
    top_uas = ua_counts.most_common(top_n)

    summary = {
        "input_file": args.input,
        "total_lines": total_lines,
        "parsed_lines": parsed_lines,
        "malformed_lines": malformed_lines,
    }

    report_title = "Web Server Log Report (Apache/Nginx)"
    html_out = make_html_report(report_title, summary, top_ips, top_uas, status_counts, errors_sample)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"OK: report generated: {args.output}")
    print(f"Total lines: {total_lines}, Parsed: {parsed_lines}, Malformed: {malformed_lines}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

