from pathlib import Path

from weasyprint import HTML

from workers.celery_app import celery_app
from workers.storage import get_s3_client, upload_file

REPORT_TEMPLATE = """
<html>
<head>
<style>
  body {{ font-family: sans-serif; padding: 40px; color: #1a1a1a; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 8px; }}
  .meta {{ color: #555; margin-bottom: 24px; }}
  .section {{ margin-bottom: 20px; }}
  .section h2 {{ font-size: 16px; margin-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td, th {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
</style>
</head>
<body>
  <h1>DiagnoZ Inspection Report</h1>
  <div class="meta">
    Session ID: {session_id}<br/>
    Dispatch ID: {dispatch_id}<br/>
    Customer: {customer_name}<br/>
    Technician: {technician_name}
  </div>

  <div class="section">
    <h2>Diagnosis</h2>
    <p>{diagnosis_summary}</p>
  </div>

  <div class="section">
    <h2>Voice Transcript</h2>
    <p>{voice_transcript}</p>
  </div>

  <div class="section">
    <h2>Parts Replaced</h2>
    <table>
      <tr><th>Part</th><th>Quantity</th><th>Cost</th></tr>
      {parts_rows}
    </table>
  </div>

  <div class="section">
    <h2>Billing</h2>
    <table>
      <tr><td>Total Service Fee</td><td>{total_service_fee}</td></tr>
      <tr><td>Platform Commission</td><td>{platform_commission_fee}</td></tr>
      <tr><td>Technician Earnings</td><td>{technician_earnings}</td></tr>
    </table>
  </div>
</body>
</html>
"""


def _render_parts_rows(parts_replaced: list[dict]) -> str:
    if not parts_replaced:
        return "<tr><td colspan='3'>None</td></tr>"
    rows = []
    for part in parts_replaced:
        rows.append(
            f"<tr><td>{part.get('name', '')}</td>"
            f"<td>{part.get('quantity', 1)}</td>"
            f"<td>{part.get('cost', 0)}</td></tr>"
        )
    return "".join(rows)


@celery_app.task(name="tasks.generate_report", bind=True, max_retries=3)
def generate_inspection_report(self, dispatch_id: str, report_data: dict, output_dir: str):
    html_content = REPORT_TEMPLATE.format(
        session_id=report_data.get("session_id", "N/A"),
        dispatch_id=dispatch_id,
        customer_name=report_data.get("customer_name", "N/A"),
        technician_name=report_data.get("technician_name", "N/A"),
        diagnosis_summary=report_data.get("diagnosis_summary", "N/A"),
        voice_transcript=report_data.get("voice_transcript", "N/A"),
        parts_rows=_render_parts_rows(report_data.get("parts_replaced", [])),
        total_service_fee=report_data.get("total_service_fee", 0),
        platform_commission_fee=report_data.get("platform_commission_fee", 0),
        technician_earnings=report_data.get("technician_earnings", 0),
    )

    out_path = Path(output_dir) / f"{dispatch_id}.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        HTML(string=html_content).write_pdf(str(out_path))
    except Exception as err:
        raise self.retry(exc=err, countdown=10)

    s3_client = get_s3_client()
    s3_key = f"reports/{dispatch_id}.pdf"
    upload_file(s3_client, out_path, s3_key)

    return {"status": "SUCCESS", "invoice_pdf_url": s3_key}
