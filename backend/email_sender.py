"""
Email sender for WAIO Audit Tool.
Sends branded audit report emails with PDF attachment via Resend.
"""
import os
import logging
import resend

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")


def send_report_email(to_email: str, report: dict, pdf_bytes: bytes) -> dict:
    """
    Send the audit report PDF to the given email address.
    Returns a dict with 'success' and 'message' keys.
    """
    if not RESEND_API_KEY:
        return {"success": False, "message": "Email sending is not configured (RESEND_API_KEY not set)."}

    resend.api_key = RESEND_API_KEY

    url = report.get("url", "Unknown")
    overall_score = report.get("overall_score", 0)
    overall_label = report.get("overall_label", "N/A")
    summary = report.get("summary", {})

    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;color:#1a1a2e;">
        <div style="background:#1a1a2e;padding:24px 32px;border-radius:12px 12px 0 0;">
            <div style="font-size:20px;font-weight:800;color:white;">WAIO <span style="color:#8b8b9e;font-weight:400;">Audit Engine</span></div>
            <div style="font-size:10px;color:#8b8b9e;margin-top:2px;">BY VEZA DIGITAL</div>
        </div>
        <div style="background:#f8f9fa;padding:32px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;">
            <h2 style="font-size:18px;margin:0 0 8px;">Your Audit Report is Ready</h2>
            <p style="font-size:14px;color:#6b7280;margin:0 0 20px;">
                We've completed the analysis for <strong>{url}</strong>
            </p>

            <div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:20px;text-align:center;margin-bottom:20px;">
                <div style="font-size:42px;font-weight:900;color:#2820FF;">{overall_score}</div>
                <div style="font-size:11px;font-weight:700;color:#2820FF;text-transform:uppercase;letter-spacing:1.5px;">{overall_label}</div>
                <div style="font-size:10px;color:#9ca3af;margin-top:4px;">Overall Health Score</div>
            </div>

            <div style="display:flex;gap:12px;margin-bottom:20px;">
                <div style="flex:1;text-align:center;background:{('#FEF2F2' if summary.get('critical', 0) > 0 else 'white')};border-radius:8px;padding:12px;">
                    <div style="font-size:22px;font-weight:900;color:#DC2626;">{summary.get('critical', 0)}</div>
                    <div style="font-size:9px;font-weight:700;color:#6b7280;text-transform:uppercase;">Critical</div>
                </div>
                <div style="flex:1;text-align:center;background:{('#FFF7ED' if summary.get('high', 0) > 0 else 'white')};border-radius:8px;padding:12px;">
                    <div style="font-size:22px;font-weight:900;color:#EA580C;">{summary.get('high', 0)}</div>
                    <div style="font-size:9px;font-weight:700;color:#6b7280;text-transform:uppercase;">High</div>
                </div>
                <div style="flex:1;text-align:center;background:{('#FEFCE8' if summary.get('medium', 0) > 0 else 'white')};border-radius:8px;padding:12px;">
                    <div style="font-size:22px;font-weight:900;color:#A16207;">{summary.get('medium', 0)}</div>
                    <div style="font-size:9px;font-weight:700;color:#6b7280;text-transform:uppercase;">Medium</div>
                </div>
            </div>

            <p style="font-size:13px;color:#6b7280;">
                The full detailed report is attached as a PDF. It includes all 6 pillar scores,
                detailed findings with recommendations, and credibility anchors.
            </p>

            <div style="text-align:center;margin-top:24px;">
                <a href="https://www.vezadigital.com" style="display:inline-block;background:#2820FF;color:white;font-size:13px;font-weight:700;padding:12px 28px;border-radius:8px;text-decoration:none;">
                    Learn More About Veza Digital →
                </a>
            </div>
        </div>
        <div style="text-align:center;padding:16px;font-size:10px;color:#9ca3af;">
            Sent by WAIO Audit Engine · <a href="https://www.vezadigital.com" style="color:#2820FF;">vezadigital.com</a>
        </div>
    </div>
    """

    try:
        # Build safe filename from URL
        safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_").strip("_")
        filename = f"WAIO_Audit_{safe_url}.pdf"

        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"Your WAIO Audit Report for {url}",
            "html": html_body,
            "attachments": [
                {
                    "filename": filename,
                    "content": list(pdf_bytes),
                }
            ],
        }

        response = resend.Emails.send(params)
        logger.info(f"Email sent to {to_email}: {response}")
        return {"success": True, "message": f"Report sent to {to_email}"}

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return {"success": False, "message": f"Failed to send email: {str(e)}"}
