#!/usr/bin/env python3
import argparse
import json
import csv
import time
import sys
import urllib.request
import urllib.error
from datetime import datetime

def parse_args():
    p = argparse.ArgumentParser(
        description="API monitoring script with response time measurement"
    )
    p.add_argument(
        "-u", "--urls",
        required=True,
        nargs="+",
        help="List of URLs to monitor"
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Request timeout in seconds"
    )
    p.add_argument(
        "--json-out",
        default="api_report.json",
        help="Output JSON file"
    )
    p.add_argument(
        "--csv-out",
        default="api_report.csv",
        help="Output CSV file"
    )
    p.add_argument(
        "--discord-webhook",
        default="",
        help="Discord webhook URL for alerts"
    )

    return p.parse_args()

def check_url(url, timeout):
    start = time.time()
    status = None
    error = ""

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
        error = str(e)
    except Exception as e:
        error = str(e)

    duration = round((time.time() - start) * 1000, 2)

    # ok is True only for 2xx and 3xx responses
    ok = status is not None and 200 <= status < 400

    return {
        "url": url,
        "ok": ok,
        "status": status,
        "response_time_ms": duration,
        "error": error,
        "checked_at": datetime.utcnow().isoformat()
    }

def send_discord_alert(message, webhook_url):
    if not webhook_url:
        print("DISCORD: webhook url is empty", file=sys.stderr)
        return

    if not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        print("DISCORD: invalid webhook url format", file=sys.stderr)
        return

    payload = {"content": message}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DevOpsLab2-ApiMonitor/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"DISCORD: sent, status={resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        print(f"DISCORD: HTTPError code={e.code} reason={e.reason} body={body}", file=sys.stderr)
    except Exception as e:
        print(f"DISCORD: ERROR {e}", file=sys.stderr)

def main():
    args = parse_args()

    webhook_url = args.discord_webhook
    results = []

    for url in args.urls:
        result = check_url(url, args.timeout)
        results.append(result)

        if not result["ok"]:
            msg = (
                f"API ALERT\n"
                f"URL: {result['url']}\n"
                f"Status: {result['status']}\n"
                f"Error: {result['error']}"
            )
            send_discord_alert(msg, webhook_url)

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    with open(args.csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "url",
                "ok",
                "status",
                "response_time_ms",
                "checked_at",
                "error"
            ]
        )
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"OK: JSON report saved to {args.json_out}")
    print(f"OK: CSV report saved to {args.csv_out}")

if __name__ == "__main__":
    main()

