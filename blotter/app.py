from nlp_classifier import detect_priority
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, flash, Response, abort)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import csv, io, uuid, json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "safekanino-secret-key-change-me"

# ---------------- Database config ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql://postgres:Marvin121002@localhost:5432/safekanino_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Admin account only ----------------
USERS = {
    "admin": {"password": "admin123", "role": "admin", "name": "Barangay Admin"},
}

TYPE_LABELS = {
    "criminal": "Criminal Offense",
    "traffic":  "Traffic & Road Incident",
    "nuisance": "Public Nuisance",
    "dispute":  "Civil / Barangay Dispute",
}

HOTSPOTS = [
    {"sitio": "Libjo",   "percentage": 27},
    {"sitio": "Wawa",    "percentage": 13},
    {"sitio": "Ilaya",   "percentage": 35},
    {"sitio": "Kaingin", "percentage": 25},
]

# ---------------- Models ----------------

class Report(db.Model):
    __tablename__ = 'reports'

    seq         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id   = db.Column(db.String(20), unique=True, nullable=False)
    rtype       = db.Column(db.String(20), nullable=False)
    type_label  = db.Column(db.String(50), nullable=False)
    incident    = db.Column(db.String(100), nullable=False)
    citizen     = db.Column(db.String(100), nullable=False)
    priority    = db.Column(db.String(20), nullable=False)
    date_filed  = db.Column(db.String(20), nullable=False)
    status      = db.Column(db.String(20), nullable=False, default='Pending')
    fields_json = db.Column(db.Text, nullable=False, default='{}')

    def to_dict(self):
        return {
            "id":         self.ticket_id,
            "type":       self.rtype,
            "type_label": self.type_label,
            "incident":   self.incident,
            "citizen":    self.citizen,
            "priority":   self.priority,
            "date":       self.date_filed,
            "status":     self.status,
            "fields":     json.loads(self.fields_json),
        }


class Hearing(db.Model):
    __tablename__ = 'hearings'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date        = db.Column(db.String(20), nullable=False)
    time        = db.Column(db.String(20), nullable=False)
    case_id     = db.Column(db.String(20), nullable=False)
    complainant = db.Column(db.String(100), nullable=False)
    incident    = db.Column(db.String(100), nullable=False)
    mediator    = db.Column(db.String(100), nullable=False, default='Barangay Captain')
    status      = db.Column(db.String(20), nullable=False, default='In Progress')

    def to_dict(self):
        return {
            "id":          self.id,
            "date":        self.date,
            "time":        self.time,
            "case_id":     self.case_id,
            "complainant": self.complainant,
            "incident":    self.incident,
            "mediator":    self.mediator,
            "status":      self.status,
        }


class Notification(db.Model):
    __tablename__ = 'notifications'

    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title         = db.Column(db.String(50), nullable=False, default='NEW REPORT')
    reporter      = db.Column(db.String(100), nullable=False)
    incident_type = db.Column(db.String(100), nullable=False)
    report_id     = db.Column(db.String(20), nullable=False)
    body          = db.Column(db.Text, nullable=False)
    created       = db.Column(db.String(30), nullable=False)
    seen          = db.Column(db.Boolean, nullable=False, default=False)


# ---------------- Helpers ----------------

def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if "user" not in session or session["user"]["role"] != "admin":
            return redirect(url_for("admin_login"))
        return fn(*a, **kw)
    return wrapper


def generate_ticket_id(seq):
    year = datetime.now().strftime("%y")
    return f"BLT-{year}-{str(seq).zfill(3)}"


def add_notification(report_dict):
    notif = Notification(
        id=str(uuid.uuid4()),
        title="NEW REPORT",
        reporter=report_dict["citizen"],
        incident_type=report_dict["incident"],
        report_id=report_dict["id"],
        body=f'{report_dict["citizen"]} filed a new {report_dict["incident"]} report.',
        created=datetime.now().strftime("%b %d, %Y %I:%M %p"),
        seen=False,
    )
    db.session.add(notif)
    db.session.commit()


def save_report(rtype, form, files):
    rtype_label = TYPE_LABELS.get(rtype, "Report")

    citizen = form.get("full_name") or "Anonymous"

    incident = (
        form.get("crime_type")
        or form.get("nuisance_type")
        or form.get("category")
        or form.get("reporter_type")
        or rtype_label
    )

    fields = build_fields(rtype, form, files)

    narrative = ""
    for section in fields.values():
        if isinstance(section, dict):
            for value in section.values():
                narrative += f" {value}"

    priority = detect_priority(narrative)
    today    = datetime.now().strftime("%b %d, %Y")

    report = Report(
        ticket_id="TEMP",
        rtype=rtype,
        type_label=rtype_label,
        incident=incident,
        citizen=citizen,
        priority=priority,
        date_filed=today,
        status="Pending",
        fields_json=json.dumps(fields),
    )
    db.session.add(report)
    db.session.flush()

    report.ticket_id = generate_ticket_id(report.seq)
    db.session.commit()

    add_notification(report.to_dict())
    return report.to_dict()


def build_fields(rtype, f, files):
    g = lambda k, d="": (f.get(k) or d).strip() if isinstance(f.get(k), str) else (f.get(k) or d)

    def save_f(file_key):
        file_obj = files.get(file_key)
        if file_obj and file_obj.filename:
            fname = secure_filename(file_obj.filename)
            unique_name = f"{uuid.uuid4().hex[:8]}_{fname}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file_obj.save(filepath)
            return f"/static/uploads/{unique_name}"
        return "—"

    if rtype == "criminal":
        return {
            "1. Complainant (Victim/Reporter) Information": {
                "Full Name": g("full_name"),
                "Contact Number": g("contact"),
                "Complete Address": g("address"),
                "Valid ID": save_f("valid_id_file"),
            },
            "2. Incident Specifics": {
                "Specific Crime Type": g("crime_type"),
                "Date of Incident": g("incident_date"),
                "Time of Incident": g("incident_time"),
                "Location of Incident": g("incident_location"),
            },
            "3. Respondent (Suspect) Information": {
                "Is the suspect known?": g("known", "no").title(),
                "Full Name": g("suspect_name"),
                "Alias": g("alias"),
                "Address": g("suspect_address"),
                "Suspect Description": g("suspect_desc"),
            },
            "4. Narrative": {
                "Detailed Narrative of the Incident": g("narrative"),
            },
            "5. Evidence & Witnesses": {
                "Witness Names": g("witness_names"),
                "Contacts": g("witness_contacts"),
                "Evidence": save_f("evidence_file"),
            },
        }

    if rtype == "traffic":
        return {
            "1. Reporting Party Information": {
                "Reporter Type": g("reporter_type"),
                "Full Name": g("full_name"),
                "Contact Number": g("contact"),
                "Address": g("address"),
                "Valid ID": save_f("valid_id_file"),
            },
            "2. Incident Core Details": {
                "Date and Time of Incident": g("incident_dt"),
                "Exact Location": g("location"),
                "Road / Weather Condition": g("condition"),
            },
            "3. Vehicle & Driver Information": {
                "Vehicle Type": g("vehicle_type"),
                "Make, Model, and Color": g("vehicle_make"),
                "Plate Number": g("plate"),
                "Driver Details": g("driver"),
            },
            "4. Casualties & Damages": {
                "Injuries Sustained": g("injuries"),
                "Injury Details": g("injury_details"),
                "Property Damage Description": g("property_damage"),
            },
        }

    if rtype == "nuisance":
        return {
            "1. Basics (What & Where)": {
                "Type of Nuisance": g("nuisance_type"),
                "Location": g("location"),
                "Time of Nuisance": g("time"),
            },
            "2. Offender Information": {
                "Who/What is causing it?": g("offender"),
            },
            "3. Evidence": {
                "Photo Upload": save_f("evidence_file"),
            },
            "4. Reporter Information": {
                "File Anonymously": g("anon", "no").title(),
                "Full Name": g("full_name"),
                "Contact Number": g("contact"),
            },
        }

    # dispute
    return {
        "1. Complainant Information": {
            "Full Name": g("full_name"),
            "Contact Number": g("contact"),
            "Complete Address": g("address"),
        },
        "2. Respondent Information": {
            "Full Name of Respondent": g("resp_name"),
            "Complete Address": g("resp_address"),
        },
        "3. Nature of the Dispute": {
            "Dispute Category": g("category"),
        },
        "4. The Narrative": {
            "Statement of the Problem": g("problem"),
        },
        "5. Relief Sought": {
            "Desired Outcome": g("relief"),
        },
        "6. Supporting Documents": {
            "Attachments": save_f("evidence_file"),
        },
    }


def find_report(rid):
    r = Report.query.filter_by(ticket_id=rid).first()
    return r.to_dict() if r else None


def get_unread_count():
    return Notification.query.filter_by(seen=False).count()


# ---------------- Seed ----------------

def seed_sample():
    if Report.query.count() == 0:
        sample_fields = {
            "1. Complainant (Victim/Reporter) Information": {
                "Full Name": "Alvarez, Jerwin L.",
                "Contact Number": "+63 912 345 6789",
                "Complete Address": "123 Sitio Libjo, Barangay San Roque",
                "Valid ID": "valid_id.jpg (attachment)",
            },
            "2. Incident Specifics": {
                "Specific Crime Type": "Physical Assault",
                "Date of Incident": "Jan 25, 2026",
                "Time of Incident": "08:30 PM",
                "Location of Incident": "Corner of Mabini St. & Rizal Ave., Sitio Libjo",
            },
            "3. Respondent (Suspect) Information": {
                "Is the suspect known?": "Yes",
                "Full Name": "Cruz, Mark Anthony",
                "Alias": "Tonying",
                "Address": "45 Sitio Libjo, Barangay San Roque",
            },
            "4. Narrative": {
                "Detailed Narrative of the Incident": (
                    "At around 8:30 PM, while walking home, the complainant was "
                    "approached and physically assaulted by the suspect after a "
                    "heated argument regarding an unpaid debt."
                ),
            },
            "5. Evidence & Witnesses": {
                "Witness Names": "Reyes, Ana M.",
                "Contacts": "+63 917 222 3344",
                "Evidence": "incident_photo.jpg (attachment)",
            },
        }
        report = Report(
            ticket_id="TEMP",
            rtype="criminal",
            type_label="Criminal Offense",
            incident="Physical Assault",
            citizen="Alvarez, Jerwin L.",
            priority="Critical",
            date_filed="Jan 25, 2026",
            status="Pending",
            fields_json=json.dumps(sample_fields),
        )
        db.session.add(report)
        db.session.flush()
        report.ticket_id = generate_ticket_id(report.seq)
        db.session.commit()


# ---------------- Routes ----------------

@app.route("/")
def index():
    return render_template(
        "citizen_hub.html",
        hotspots=HOTSPOTS
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if "user" in session and session["user"]["role"] == "admin":
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        user = USERS.get(u)
        if user and user["password"] == p and user["role"] == "admin":
            session["user"] = {"username": u, "role": user["role"], "name": user["name"]}
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "error")
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ---------------- ADMIN ----------------

@app.route("/admin/dashboard")
@admin_required
def dashboard():
    all_reports = Report.query.order_by(Report.seq.desc()).limit(11).all()
    reports = [r.to_dict() for r in all_reports]
    stats = {
        "pending":   Report.query.filter(Report.status != "Settled").count(),
        "completed": Report.query.filter_by(status="Settled").count(),
        "total":     Report.query.count(),
        "high":      Report.query.filter(Report.priority.in_(["Critical", "High"])).count(),
    }
    notifications = Notification.query.order_by(Notification.created.desc()).limit(5).all()
    notif_list = [{
        "title": n.title, "reporter": n.reporter,
        "incident_type": n.incident_type, "body": n.body, "created": n.created,
    } for n in notifications]
    return render_template(
        "dashboard.html",
        reports=reports, stats=stats, hotspots=HOTSPOTS,
        notifications=notif_list,
        unread=get_unread_count(),
        active="dashboard",
    )


@app.route("/admin/status-reports")
@admin_required
def status_reports():
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 10
    total    = Report.query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    pagination = Report.query.order_by(Report.seq).paginate(page=page, per_page=per_page, error_out=False)
    items = [r.to_dict() for r in pagination.items]
    start = (page - 1) * per_page
    end   = min(start + per_page, total)
    return render_template(
        "status_reports.html",
        reports=items, page=page, total_pages=total_pages,
        total=total, start=start + 1 if total else 0, end=end,
        start_index=start,
        unread=get_unread_count(),
        active="status",
    )


@app.route("/admin/report/<rid>")
@admin_required
def report_detail(rid):
    r = find_report(rid)
    if not r:
        return jsonify({"error": "not found"}), 404
    return jsonify(r)


@app.route("/admin/mediation")
@admin_required
def mediation():
    all_hearings = Hearing.query.all()
    by_date = {}
    for h in all_hearings:
        by_date.setdefault(h.date, []).append(h.to_dict())
    pending = [r.to_dict() for r in Report.query.filter_by(status="Pending").all()]
    return render_template(
        "mediation.html",
        hearings=by_date,
        all_hearings=[h.to_dict() for h in all_hearings],
        pending_reports=pending,
        unread=get_unread_count(),
        active="mediation",
    )


@app.route("/admin/hearings/schedule", methods=["POST"])
@admin_required
def schedule_hearing():
    rid      = request.form.get("report_id")
    date     = request.form.get("date")
    time     = request.form.get("time")
    mediator = request.form.get("mediator") or "Barangay Captain"
    r        = Report.query.filter_by(ticket_id=rid).first()
    if not r or not date or not time:
        flash("Please select a pending report, date and time.", "error")
        return redirect(url_for("mediation"))
    hearing = Hearing(
        id=str(uuid.uuid4()),
        date=date, time=time,
        case_id=r.ticket_id, complainant=r.citizen,
        incident=r.incident, mediator=mediator,
        status="In Progress",
    )
    db.session.add(hearing)
    r.status = "In Progress"
    db.session.commit()
    flash("Hearing scheduled successfully.", "success")
    return redirect(url_for("mediation"))


@app.route("/admin/hearings/update", methods=["POST"])
@admin_required
def update_hearing_status():
    hid        = request.form.get("hearing_id")
    new_status = request.form.get("status")
    if new_status not in ("Pending", "In Progress", "Settled"):
        return jsonify({"error": "invalid status"}), 400
    h = Hearing.query.get(hid)
    if not h:
        return jsonify({"error": "not found"}), 404
    h.status = new_status
    r = Report.query.filter_by(ticket_id=h.case_id).first()
    if r:
        if new_status == "Settled":
            r.status = "Settled"
        elif new_status == "In Progress":
            r.status = "In Progress"
        elif new_status == "Pending":
            r.status = "Pending"
    db.session.commit()
    return jsonify({"ok": True, "hearing": h.to_dict()})


@app.route("/admin/notifications")
@admin_required
def notifications_api():
    items = Notification.query.order_by(Notification.created.desc()).limit(10).all()
    return jsonify({
        "items":  [{"id": n.id, "title": n.title, "reporter": n.reporter,
                    "incident_type": n.incident_type, "body": n.body,
                    "created": n.created} for n in items],
        "unread": get_unread_count(),
        "total":  Notification.query.count(),
    })


@app.route("/admin/notifications/seen", methods=["POST"])
@admin_required
def notifications_seen():
    Notification.query.filter_by(seen=False).update({"seen": True})
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/admin/export.csv")
@admin_required
def export_csv():
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["#", "ID", "Citizen", "Incident Type", "Priority", "Date Filed", "Status"])
    for i, r in enumerate(Report.query.order_by(Report.seq).all(), 1):
        w.writerow([i, r.ticket_id, r.citizen, r.incident,
                    r.priority, r.date_filed, r.status])
    return Response(
        buf.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=status_reports.csv"},
    )


# ---------------- CITIZEN ----------------

@app.route("/report")
def report_type():
    return render_template("report_type.html")


@app.route("/report/<rtype>", methods=["GET", "POST"])
def report_form(rtype):
    if rtype not in TYPE_LABELS:
        abort(404)
    if request.method == "POST":
        save_report(rtype, request.form, request.files)
        flash("Report submitted successfully!", "success")
        return redirect(url_for("report_type"))
    return render_template(f"form_{rtype}.html")


# ---------------- Init ----------------

with app.app_context():
    db.create_all()
    seed_sample()


if __name__ == "__main__":
    app.run(debug=True, port=5000)