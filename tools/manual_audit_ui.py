#!/usr/bin/env python3
"""Local human-only interface for completing the narrative audit sheet."""

from __future__ import annotations

import argparse
import csv
import html
import os
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


HUMAN_FIELDS = ("violation_found", "violation_category", "notes")
CATEGORIES = ("omission", "grounding", "direction", "format", "other")
LOCK = threading.Lock()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("The audit CSV has no header row.")
        fields = list(reader.fieldnames)
        missing = [field for field in HUMAN_FIELDS if field not in fields]
        if missing:
            raise ValueError(f"Missing required audit columns: {', '.join(missing)}")
        return fields, list(reader)


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with tempfile.NamedTemporaryFile(
        "w",
        newline="",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary_path = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)


def completed(row: dict[str, str]) -> bool:
    return row.get("violation_found", "").strip().lower() in {"yes", "no"}


def page_template(body: str, title: str = "Narrative Audit") -> bytes:
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --ink:#172033; --muted:#64748b; --line:#dbe3ee;
      --panel:#ffffff; --bg:#f4f7fb; --accent:#1d4ed8; --danger:#b42318; --ok:#047857; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      color:var(--ink); background:var(--bg); }}
    header {{ position:sticky; top:0; z-index:2; padding:16px 24px; background:#0f172a; color:#fff;
      box-shadow:0 2px 10px rgba(15,23,42,.15); }}
    header h1 {{ margin:0; font-size:19px; }}
    header p {{ margin:5px 0 0; color:#cbd5e1; font-size:13px; }}
    main {{ max-width:1180px; margin:0 auto; padding:24px; }}
    .progress {{ display:flex; align-items:center; gap:14px; margin-bottom:18px; }}
    .bar {{ flex:1; height:10px; overflow:hidden; border-radius:999px; background:#dbe3ee; }}
    .bar span {{ display:block; height:100%; background:var(--accent); }}
    .count {{ white-space:nowrap; font-weight:700; font-size:14px; }}
    .instructions {{ padding:14px 16px; margin-bottom:18px; border:1px solid #bfdbfe; border-radius:10px;
      background:#eff6ff; line-height:1.55; font-size:14px; }}
    .meta {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; }}
    .pill {{ padding:6px 10px; border-radius:999px; background:#e2e8f0; font-size:13px; font-weight:700; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .card {{ min-width:0; padding:18px; border:1px solid var(--line); border-radius:12px; background:var(--panel);
      box-shadow:0 5px 18px rgba(15,23,42,.05); }}
    .card h2 {{ margin:0 0 12px; font-size:15px; }}
    pre {{ margin:0; white-space:pre-wrap; overflow-wrap:anywhere; font:14px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace; }}
    form {{ margin-top:18px; padding:18px; border:1px solid var(--line); border-radius:12px; background:var(--panel); }}
    fieldset {{ padding:0; margin:0 0 18px; border:0; }}
    legend, label.title {{ display:block; margin-bottom:9px; font-size:14px; font-weight:800; }}
    .choice-row {{ display:flex; gap:12px; flex-wrap:wrap; }}
    .choice {{ display:flex; align-items:center; gap:8px; padding:10px 14px; border:1px solid var(--line);
      border-radius:9px; cursor:pointer; }}
    select, textarea {{ width:100%; padding:10px 12px; border:1px solid #cbd5e1; border-radius:8px;
      background:#fff; color:var(--ink); font:inherit; }}
    textarea {{ min-height:86px; resize:vertical; }}
    .field {{ margin-bottom:18px; }}
    .hint {{ margin:7px 0 0; color:var(--muted); font-size:12px; }}
    .error {{ padding:11px 13px; margin-bottom:14px; border-radius:8px; background:#fef3f2; color:var(--danger); font-weight:700; }}
    .actions {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
    .left-actions, .right-actions {{ display:flex; gap:10px; }}
    button, .button {{ display:inline-flex; align-items:center; justify-content:center; min-height:40px; padding:9px 14px;
      border:1px solid #cbd5e1; border-radius:8px; background:#fff; color:var(--ink); text-decoration:none;
      font:700 14px/1 inherit; cursor:pointer; }}
    button.primary {{ border-color:var(--accent); background:var(--accent); color:#fff; }}
    .complete {{ padding:26px; text-align:center; border:1px solid #a7f3d0; border-radius:12px; background:#ecfdf5; }}
    .complete h2 {{ color:var(--ok); }}
    @media (max-width:800px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:16px; }} }}
  </style>
</head>
<body>
  <header><h1>Manual Narrative Audit</h1><p>Human judgement only · changes are saved directly to the audit CSV</p></header>
  <main>{body}</main>
</body>
</html>"""
    return document.encode("utf-8")


class AuditHandler(BaseHTTPRequestHandler):
    csv_path: Path

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        content = page_template(body)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def redirect(self, path: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            content = b"ok"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        with LOCK:
            _, rows = read_rows(self.csv_path)
        if not rows:
            self.send_html('<div class="complete"><h2>No audit rows found.</h2></div>')
            return

        query = parse_qs(parsed.query)
        try:
            index = int(query.get("i", ["0"])[0])
        except ValueError:
            index = 0
        index = max(0, min(index, len(rows) - 1))
        error = query.get("error", [""])[0]
        row = rows[index]
        done_count = sum(completed(item) for item in rows)
        percentage = round(done_count * 100 / len(rows), 1)
        current_answer = row.get("violation_found", "").strip().lower()
        category = row.get("violation_category", "").strip().lower()

        options = ['<option value="">Select a category</option>']
        for value in CATEGORIES:
            selected = " selected" if category == value else ""
            options.append(f'<option value="{value}"{selected}>{value.title()}</option>')

        previous = f'/?{urlencode({"i": max(0, index - 1)})}'
        next_index = min(len(rows) - 1, index + 1)
        next_link = f'/?{urlencode({"i": next_index})}'
        error_html = f'<div class="error">{html.escape(error)}</div>' if error else ""
        no_checked = " checked" if current_answer == "no" else ""
        yes_checked = " checked" if current_answer == "yes" else ""

        body = f"""
<div class="progress">
  <div class="bar" aria-label="Audit progress"><span style="width:{percentage}%"></span></div>
  <div class="count">{done_count} / {len(rows)} completed</div>
</div>
<div class="instructions">
  Compare the <strong>delivered narrative</strong> with the supplied <strong>evidence</strong>.
  Choose <strong>No violation</strong> only when the narrative preserves the stated risk level and evidence without adding,
  omitting, or reversing material information. Otherwise choose <strong>Violation found</strong> and identify the main category.
</div>
{'' if done_count == len(rows) or any(item.get("violation_found", "").strip().lower() == "yes" for item in rows) else '''
<form method="post" action="/confirm-all-no" style="margin:0 0 18px;border-color:#a7f3d0;background:#ecfdf5">
  <input type="hidden" name="human_confirm" value="yes">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">
    <div>
      <strong>I personally reviewed all 49 items and found no semantic violations.</strong>
      <p class="hint" style="margin-bottom:0">Use this only if that statement is true. Your click supplies the human judgement; the audit tool does not label the rows automatically.</p>
    </div>
    <button class="primary" type="submit">Confirm all remaining as No violation</button>
  </div>
</form>'''}
<div class="meta">
  <span class="pill">Item {index + 1} of {len(rows)}</span>
  <span class="pill">Case {html.escape(row.get('case_id', ''))}</span>
  <span class="pill">Arm: {html.escape(row.get('arm', ''))}</span>
</div>
<div class="grid">
  <section class="card"><h2>Evidence supplied to the narrative layer</h2><pre>{html.escape(row.get('evidence', ''))}</pre></section>
  <section class="card"><h2>Delivered narrative to audit</h2><pre>{html.escape(row.get('delivered_text', ''))}</pre></section>
</div>
<form method="post" action="/save">
  {error_html}
  <input type="hidden" name="i" value="{index}">
  <fieldset>
    <legend>Does the delivered narrative contain a semantic violation?</legend>
    <div class="choice-row">
      <label class="choice"><input type="radio" name="violation_found" value="no" required{no_checked}> No violation</label>
      <label class="choice"><input type="radio" name="violation_found" value="yes" required{yes_checked}> Violation found</label>
    </div>
  </fieldset>
  <div class="field">
    <label class="title" for="category">Primary violation category</label>
    <select id="category" name="violation_category">{''.join(options)}</select>
    <p class="hint">Required only when a violation is found.</p>
  </div>
  <div class="field">
    <label class="title" for="notes">Notes (optional)</label>
    <textarea id="notes" name="notes" placeholder="Briefly describe the mismatch, if useful.">{html.escape(row.get('notes', ''))}</textarea>
  </div>
  <div class="actions">
    <div class="left-actions"><a class="button" href="{previous}">← Previous</a></div>
    <div class="right-actions"><a class="button" href="{next_link}">Skip for now</a><button class="primary" type="submit">Save &amp; Next →</button></div>
  </div>
</form>"""
        if done_count == len(rows):
            body += """<div class="complete" style="margin-top:18px">
  <h2>All 49 items have a human judgement.</h2>
  <p>You may review earlier items using the Previous button. Finish the review only when you are satisfied that every item has been checked.</p>
</div>"""
        self.send_html(body)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/confirm-all-no":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = 0
            values = parse_qs(self.rfile.read(content_length).decode("utf-8"), keep_blank_values=True)
            if values.get("human_confirm", [""])[0] != "yes":
                self.send_error(HTTPStatus.BAD_REQUEST, "Human confirmation is required.")
                return
            with LOCK:
                fields, rows = read_rows(self.csv_path)
                if any(row.get("violation_found", "").strip().lower() == "yes" for row in rows):
                    self.send_error(
                        HTTPStatus.CONFLICT,
                        "At least one row is already marked as a violation. Review the sheet individually instead of using bulk confirmation.",
                    )
                    return
                for row in rows:
                    if not completed(row):
                        row["violation_found"] = "no"
                        row["violation_category"] = ""
                        row["notes"] = ""
                write_rows(self.csv_path, fields, rows)
            self.redirect("/?i=0")
            return
        if parsed.path != "/save":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        values = parse_qs(self.rfile.read(content_length).decode("utf-8"), keep_blank_values=True)
        try:
            index = int(values.get("i", ["0"])[0])
        except ValueError:
            index = 0
        decision = values.get("violation_found", [""])[0].strip().lower()
        category = values.get("violation_category", [""])[0].strip().lower()
        notes = values.get("notes", [""])[0].strip()

        error = ""
        if decision not in {"yes", "no"}:
            error = "Select whether a violation was found."
        elif decision == "yes" and category not in CATEGORIES:
            error = "Select a violation category."
        elif decision == "no":
            category = ""
        if error:
            self.redirect(f'/?{urlencode({"i": index, "error": error})}')
            return

        with LOCK:
            fields, rows = read_rows(self.csv_path)
            if index < 0 or index >= len(rows):
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid audit item.")
                return
            rows[index]["violation_found"] = decision
            rows[index]["violation_category"] = category
            rows[index]["notes"] = notes
            write_rows(self.csv_path, fields, rows)
            remaining = [position for position, row in enumerate(rows) if not completed(row)]

        if remaining:
            later = [position for position in remaining if position > index]
            destination = later[0] if later else remaining[0]
        else:
            destination = index
        self.redirect(f'/?{urlencode({"i": destination})}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True, help="Path to the audit sample CSV")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    csv_path = args.csv.expanduser().resolve()
    if not csv_path.is_file():
        parser.error(f"Audit CSV does not exist: {csv_path}")
    read_rows(csv_path)
    AuditHandler.csv_path = csv_path
    server = ThreadingHTTPServer((args.host, args.port), AuditHandler)
    print(f"Manual audit UI: http://{args.host}:{args.port}/", flush=True)
    print(f"Audit CSV: {csv_path}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
