from flask import Flask, request, jsonify, g
from flask_cors import CORS
import re
import datetime
import requests
import os
import hmac
import secrets
import copy
from functools import wraps
from collections import Counter

app = Flask(__name__)

# Configure CORS to allow Authorization header and credentials
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])  # allow frontend JS to call backend

LOGIN_EMAIL = os.getenv("MAILGUARD_LOGIN_EMAIL", "admin@mailguard.local").strip().lower()
LOGIN_PASSWORD = os.getenv("MAILGUARD_LOGIN_PASSWORD", "MailGuard@123")
TOKEN_TTL_HOURS = 8
ACTIVE_TOKENS = {}
ACTION_LOGS = []
MAX_ACTIVITY_LOGS = 200

# ---------------- Mock Emails ---------------- #
emails = [
    {
        "id": "e1",
        "from": "hr@company.com",
        "senderDomain": "company.com",
        "subject": "Weekly Team Training Schedule",
        "date": "2026-03-07",
        "body": "Hello team, next week training agenda is available on the internal portal https://company.com/training.",
        "attachments": [],
        "category": "work",
        "headers": {}
    },
    {
        "id": "e2",
        "from": "alerts@secure-billing.xyz",
        "senderDomain": "secure-billing.xyz",
        "subject": "Urgent: Verify your account now",
        "date": "2026-03-07",
        "body": "Urgent notice. Click here to verify your account: http://secure-billing.xyz/verify",
        "attachments": [],
        "category": "finance",
        "headers": {}
    },
    {
        "id": "e3",
        "from": "it-helpdesk@corp-update.tk",
        "senderDomain": "corp-update.tk",
        "subject": "Password reset utility attached",
        "date": "2026-03-06",
        "body": "Please reset your password before policy lockout.",
        "attachments": [{"name": "PasswordResetTool.exe", "size": 382010}],
        "category": "it",
        "headers": {}
    },
    {
        "id": "e4",
        "from": "support@delivery-track.xyz",
        "senderDomain": "delivery-track.xyz",
        "subject": "Shipment status update",
        "date": "2026-03-06",
        "body": "Track your package at http://delivery-track.xyz/status/AB12345",
        "attachments": [],
        "category": "updates",
        "headers": {}
    },
    {
        "id": "e5",
        "from": "newsletter@devdigest.com",
        "senderDomain": "devdigest.com",
        "subject": "Developer Digest March Edition",
        "date": "2026-03-05",
        "body": "New engineering articles are available at https://devdigest.com/march.",
        "attachments": [],
        "category": "newsletter",
        "headers": {}
    },
    {
        "id": "e6",
        "from": "operations@partner-logistics.com",
        "senderDomain": "partner-logistics.com",
        "subject": "Urgent update on transport manifest",
        "date": "2026-03-05",
        "body": "Urgent: review the attached manifest before dispatch closes.",
        "attachments": [{"name": "manifest.scr", "size": 109221}],
        "category": "operations",
        "headers": {}
    },
    {
        "id": "e7",
        "from": "service@identity-check.net",
        "senderDomain": "identity-check.net",
        "subject": "Login warning detected",
        "date": "2026-03-04",
        "body": "We detected login irregularities. Click here: http://identity-check.xyz/auth",
        "attachments": [{"name": "security_patch.bat", "size": 44102}],
        "category": "security",
        "headers": {}
    },
    {
        "id": "e8",
        "from": "admin@school.edu",
        "senderDomain": "school.edu",
        "subject": "Campus event invitation",
        "date": "2026-03-04",
        "body": "You are invited to the annual alumni event. RSVP at https://school.edu/events.",
        "attachments": [],
        "category": "events",
        "headers": {}
    },
    {
        "id": "e9",
        "from": "accounts@vendor-pay.ga",
        "senderDomain": "vendor-pay.ga",
        "subject": "Claim prize for early payment",
        "date": "2026-03-03",
        "body": "Claim prize credits after invoice settlement confirmation.",
        "attachments": [],
        "category": "finance",
        "headers": {}
    },
    {
        "id": "e10",
        "from": "manager@company.com",
        "senderDomain": "company.com",
        "subject": "Quarterly planning session",
        "date": "2026-03-03",
        "body": "Please join the planning session at 3 PM in meeting room 2.",
        "attachments": [],
        "category": "work",
        "headers": {}
    },
    {
        "id": "e11",
        "from": "notice@central-auth.cf",
        "senderDomain": "central-auth.cf",
        "subject": "Urgent bank login revalidation",
        "date": "2026-03-02",
        "body": "Urgent bank notice. Click here http://central-auth.cf/login and backup link http://safe-validate.xyz/check.",
        "attachments": [],
        "category": "finance",
        "headers": {}
    },
    {
        "id": "e12",
        "from": "courier@post-notify.pw",
        "senderDomain": "post-notify.pw",
        "subject": "Customs declaration attached",
        "date": "2026-03-02",
        "body": "A declaration file is attached for your review.",
        "attachments": [{"name": "declaration.exe", "size": 284111}],
        "category": "shipping",
        "headers": {}
    },
    {
        "id": "e13",
        "from": "support@wallet-service.net",
        "senderDomain": "wallet-service.net",
        "subject": "Verify wallet access",
        "date": "2026-03-01",
        "body": "Verify your wallet access immediately: http://wallet-check.xyz/verify",
        "attachments": [],
        "category": "finance",
        "headers": {}
    },
    {
        "id": "e14",
        "from": "care@healthclinic.org",
        "senderDomain": "healthclinic.org",
        "subject": "Appointment reminder",
        "date": "2026-03-01",
        "body": "Reminder: your appointment is scheduled for Monday at 10 AM.",
        "attachments": [{"name": "appointment.pdf", "size": 90511}],
        "category": "personal",
        "headers": {}
    },
    {
        "id": "e15",
        "from": "team@projecthub.com",
        "senderDomain": "projecthub.com",
        "subject": "Repository migration checklist",
        "date": "2026-02-28",
        "body": "The repository migration checklist is attached for the release team.",
        "attachments": [{"name": "migration-checklist.pdf", "size": 121111}],
        "category": "work",
        "headers": {}
    }
]
SEED_EMAILS = copy.deepcopy(emails)

PHISH_KEYWORDS = ["verify", "password", "login", "bank", "urgent", "click here", "claim prize"]
SUSPICIOUS_TLDS = [".pw", ".xyz", ".tk", ".cf", ".ga"]
SUSPICIOUS_EXTS = [".exe", ".scr", ".bat"]

# ---------------- Spam Detection ---------------- #
def compute_spam(email):
    score = 0
    reasons = []

    body = email.get("body", "").lower()

    # keyword check
    if any(k in body for k in PHISH_KEYWORDS):
        score += 30
        reasons.append("Suspicious keyword detected")

    # suspicious links
    links = re.findall(r"http[s]?://\S+", body)
    for link in links:
        if any(tld in link for tld in SUSPICIOUS_TLDS):
            score += 25
            reasons.append("Suspicious link detected")

    # suspicious domain
    if any(email["senderDomain"].endswith(tld) for tld in SUSPICIOUS_TLDS):
        score += 20
        reasons.append(f"Suspicious sender domain {email['senderDomain']}")

    # attachments
    for att in email.get("attachments", []):
        if any(att["name"].endswith(ext) for ext in SUSPICIOUS_EXTS):
            score += 25
            reasons.append("Dangerous attachment type detected")

    return {
        "score": min(score, 100),
        "reasons": reasons or ["No issues detected"]
    }
    # scan attachments
def scan_attachment(file_url):
    url = "https://www.virustotal.com/api/v3/urls"
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}
    response = requests.post(url, headers=headers, data={"url": file_url})
    return response.json()

def issue_token(email):
    cleanup_expired_tokens()
    token = secrets.token_urlsafe(24)
    issued_at = datetime.datetime.now(datetime.timezone.utc)
    expires_at = issued_at + datetime.timedelta(hours=TOKEN_TTL_HOURS)
    ACTIVE_TOKENS[token] = {"email": email, "issued_at": issued_at, "expires_at": expires_at}
    return token, expires_at.isoformat()

def cleanup_expired_tokens():
    now = datetime.datetime.now(datetime.timezone.utc)
    expired = [token for token, data in ACTIVE_TOKENS.items() if data["expires_at"] <= now]
    for token in expired:
        ACTIVE_TOKENS.pop(token, None)

def append_activity(event_type, message, actor="system", email_id=None, metadata=None):
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "eventType": event_type,
        "actor": actor,
        "message": message,
        "emailId": email_id,
        "metadata": metadata or {}
    }
    ACTION_LOGS.insert(0, entry)
    if len(ACTION_LOGS) > MAX_ACTIVITY_LOGS:
        ACTION_LOGS.pop()

def get_bearer_token():
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()

def require_auth(route_fn):
    @wraps(route_fn)
    def wrapped(*args, **kwargs):
        cleanup_expired_tokens()
        token = get_bearer_token()
        if not token:
            return jsonify({"error": "Missing bearer token"}), 401
        session = ACTIVE_TOKENS.get(token)
        if not session:
            return jsonify({"error": "Invalid or expired token"}), 401
        g.auth_email = session["email"]
        g.auth_token = token
        return route_fn(*args, **kwargs)
    return wrapped

def get_band(score):
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"

def build_metrics(analyzed_emails):
    risk_bands = Counter()
    category_counts = Counter()
    suspicious_domain_count = 0
    daily = {}

    for item in analyzed_emails:
        score = int(item.get("score", 0))
        risk_bands[get_band(score)] += 1
        category_counts[item.get("category", "uncategorized")] += 1
        domain = item.get("senderDomain", "")
        if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
            suspicious_domain_count += 1

        date_key = item.get("date", "unknown")
        bucket = daily.setdefault(date_key, {"total": 0, "high": 0, "medium": 0, "low": 0})
        bucket["total"] += 1
        bucket[get_band(score)] += 1

    total = len(analyzed_emails)
    avg_score = round(sum(item.get("score", 0) for item in analyzed_emails) / total, 2) if total else 0
    trend = [
        {"date": date_key, **daily[date_key]}
        for date_key in sorted(daily.keys())
    ]

    top_risky = sorted(
        analyzed_emails,
        key=lambda email_item: int(email_item.get("score", 0)),
        reverse=True
    )[:5]
    top_risky_payload = [
        {
            "id": item.get("id"),
            "subject": item.get("subject"),
            "from": item.get("from"),
            "score": int(item.get("score", 0))
        }
        for item in top_risky
    ]

    return {
        "totalEmails": total,
        "averageScore": avg_score,
        "riskBands": {
            "high": risk_bands.get("high", 0),
            "medium": risk_bands.get("medium", 0),
            "low": risk_bands.get("low", 0)
        },
        "categoryCounts": dict(category_counts),
        "suspiciousDomainCount": suspicious_domain_count,
        "trendByDate": trend,
        "topRiskyEmails": top_risky_payload,
        "activityCount": len(ACTION_LOGS)
    }

def purge_all_emails(actor):
    deleted_count = len(emails)
    emails.clear()
    append_activity(
        "bulk_delete",
        f"Removed all emails ({deleted_count})",
        actor=actor,
        metadata={"deletedCount": deleted_count}
    )
    return deleted_count

def restore_demo_emails(actor):
    emails.clear()
    emails.extend(copy.deepcopy(SEED_EMAILS))
    restored_count = len(emails)
    append_activity(
        "restore_demo",
        f"Restored demo emails ({restored_count})",
        actor=actor,
        metadata={"restoredCount": restored_count}
    )
    return restored_count

# ---------------- Routes ---------------- #
VIRUSTOTAL_API_KEY = "YOUR_API_KEY"

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    valid_email = hmac.compare_digest(email, LOGIN_EMAIL)
    valid_password = hmac.compare_digest(password, LOGIN_PASSWORD)
    if not (valid_email and valid_password):
        append_activity("login_failed", "Failed login attempt", actor=email or "unknown")
        return jsonify({"error": "Invalid email or password"}), 401

    token, expires_at = issue_token(email)
    append_activity("login_success", "User signed in", actor=email, metadata={"expiresAt": expires_at})
    return jsonify({
        "ok": True,
        "email": email,
        "token": token,
        "expiresAt": expires_at
    })

@app.route("/api/logout", methods=["POST"])
@require_auth
def logout():
    token = g.auth_token
    email = g.auth_email
    ACTIVE_TOKENS.pop(token, None)
    append_activity("logout", "User signed out", actor=email)
    return jsonify({"ok": True})

@app.route("/api/emails", methods=["GET"])
@require_auth
def get_emails():
    """Return all emails with spam analysis"""
    analyzed = []
    for e in emails:
        res = compute_spam(e)
        analyzed.append({**e, **res})
    return jsonify(analyzed)

@app.route("/api/analyze", methods=["POST"])
@require_auth
def analyze_email():
    """Analyze a single email"""
    data = request.json
    res = compute_spam(data)
    return jsonify(res)

@app.route("/api/mark_spam/<email_id>", methods=["POST"])
@require_auth
def mark_spam(email_id):
    for e in emails:
        if e["id"] == email_id:
            e["category"] = "spam"
            append_activity(
                "mark_spam",
                f"Email {email_id} moved to spam",
                actor=g.auth_email,
                email_id=email_id
            )
            return jsonify({"msg": "Email moved to spam"})
    return jsonify({"error": "Email not found"}), 404

@app.route("/api/mark_safe/<email_id>", methods=["POST"])
@require_auth
def mark_safe(email_id):
    for e in emails:
        if e["id"] == email_id:
            e["category"] = "inbox"
            append_activity(
                "mark_safe",
                f"Email {email_id} marked safe",
                actor=g.auth_email,
                email_id=email_id
            )
            return jsonify({"msg": "Email marked as safe"})
    return jsonify({"error": "Email not found"}), 404

@app.route("/api/emails/purge", methods=["POST"])
@require_auth
def purge_emails():
    deleted_count = purge_all_emails(g.auth_email)
    return jsonify({
        "ok": True,
        "deletedCount": deleted_count,
        "remainingCount": len(emails)
    })

@app.route("/api/emails/reset", methods=["POST"])
@require_auth
def reset_emails():
    restored_count = restore_demo_emails(g.auth_email)
    return jsonify({
        "ok": True,
        "restoredCount": restored_count
    })

@app.route("/api/assistant", methods=["POST"])
@require_auth
def assistant():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    message_lc = message.lower()
    append_activity(
        "assistant_query",
        f"Assistant query: {message[:120]}",
        actor=g.auth_email
    )

    if ("delete all" in message_lc or "remove all" in message_lc or "clear all" in message_lc) and "email" in message_lc:
        deleted_count = purge_all_emails(g.auth_email)
        return jsonify({
            "ok": True,
            "action": "delete_all",
            "deletedCount": deleted_count,
            "reply": f"Completed. I removed all emails in one step ({deleted_count})."
        })

    if ("restore" in message_lc or "reset" in message_lc) and ("email" in message_lc or "demo" in message_lc):
        restored_count = restore_demo_emails(g.auth_email)
        return jsonify({
            "ok": True,
            "action": "restore_demo",
            "restoredCount": restored_count,
            "reply": f"Done. I restored {restored_count} demo emails."
        })

    if "help" in message_lc or "what can you do" in message_lc:
        return jsonify({
            "ok": True,
            "action": "help",
            "reply": "Try: 'delete all emails', 'reset demo emails', 'risk summary', or 'count high risk emails'."
        })

    analyzed = []
    for item in emails:
        spam_result = compute_spam(item)
        analyzed.append({**item, **spam_result})
    metrics = build_metrics(analyzed)

    if "risk summary" in message_lc or "summary" in message_lc:
        bands = metrics["riskBands"]
        return jsonify({
            "ok": True,
            "action": "risk_summary",
            "reply": (
                f"Risk summary: total {metrics['totalEmails']}, "
                f"high {bands['high']}, medium {bands['medium']}, low {bands['low']}, "
                f"average score {metrics['averageScore']}."
            ),
            "metrics": metrics
        })

    if ("high risk" in message_lc and ("count" in message_lc or "how many" in message_lc or "show" in message_lc)):
        return jsonify({
            "ok": True,
            "action": "high_risk_count",
            "reply": f"There are {metrics['riskBands']['high']} high risk emails right now.",
            "metrics": metrics
        })

    return jsonify({
        "ok": True,
        "action": "fallback",
        "reply": "I can help with mailbox operations. Ask me: delete all emails, reset demo emails, or risk summary."
    })

@app.route("/api/metrics", methods=["GET"])
@require_auth
def get_metrics():
    analyzed = []
    for e in emails:
        res = compute_spam(e)
        analyzed.append({**e, **res})
    metrics = build_metrics(analyzed)
    return jsonify(metrics)

@app.route("/api/activity", methods=["GET"])
@require_auth
def get_activity():
    try:
        limit = int(request.args.get("limit", 25))
    except ValueError:
        limit = 25
    limit = max(1, min(limit, 100))
    return jsonify(ACTION_LOGS[:limit])

@app.route("/scan_link", methods=["POST"])
@require_auth
def scan_link():
    data = request.json
    result = scan_attachment(data["link"])
    return jsonify(result)

# ---------------- Run ---------------- #
if __name__ == "__main__":
    app.run(debug=True, port=5000)


