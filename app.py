import os
import secrets
import sqlite3
from datetime import date
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash
from markupsafe import Markup

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"
DATABASE = os.environ.get("DATABASE_PATH", str(Path(__file__).resolve().parent / "mittistay.sqlite3"))
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

def db():
    if "db" not in g:
        path = Path(DATABASE)
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
        g.db.execute("PRAGMA busy_timeout=5000")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS rooms (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
      price INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS bookings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      room_id INTEGER NOT NULL REFERENCES rooms(id),
      guest_name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT,
      checkin TEXT NOT NULL, checkout TEXT NOT NULL,
      guests INTEGER NOT NULL, notes TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    for key, value in [("whatsapp", "919098067313"), ("site_title", "MittiStay")]:
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (key, value))
    for room in [(1, "Orchard Room", "Wake up near mango orchards.", 2200),
                 (2, "Village Comfort Room", "Slow mornings in the countryside.", 2200),
                 (3, "Family Room", "A spacious option for village getaways.", 2800)]:
        c.execute("INSERT OR IGNORE INTO rooms(id,name,description,price) VALUES (?,?,?,?)", room)
    c.commit()

@app.before_request
def prepare():
    init_db()
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)

def check_csrf():
    if not secrets.compare_digest(str(session.get("csrf", "")), str(request.form.get("csrf", ""))):
        abort(400, "Invalid form token. Reload and try again.")

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def setting(name):
    row = db().execute("SELECT value FROM settings WHERE key=?", (name,)).fetchone()
    return row["value"] if row else ""

def page(body, **ctx):
    layout = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="MittiStay rural homestay in Nagla Katilla, Kasganj">
<title>MittiStay | Village Homestay</title><style>
:root{--forest:#163d30;--sand:#e8bf83;--paper:#fbf8f1}
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;margin:0;color:#263c31;background:#fff}
header{background:var(--forest);color:white;padding:18px max(5%,calc((100% - 1080px)/2));display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;align-items:center}
header b{font-size:25px}header a{color:white;text-decoration:none;margin-left:14px}
main{max-width:1120px;margin:auto;padding:40px 22px 90px}.hero{background:linear-gradient(115deg,#153d31fa,#315b40b9),radial-gradient(ellipse,#cfca89,#52845e);color:white;border-radius:16px;padding:85px 7%}
h1{font:normal clamp(40px,5vw,70px)/1.1 Georgia,serif;margin:8px 0 20px}
h2{font:normal 38px Georgia,serif;color:var(--forest)}.hero h2{color:white}
.kicker{letter-spacing:.13em;font-size:12px;font-weight:800;color:var(--sand)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.room,.panel{background:var(--paper);padding:23px;border:1px solid #e0e4d7;border-radius:12px}
.room .emoji{font-size:55px}.muted{color:#627265;line-height:1.6}
.price{color:var(--forest);font-size:22px;font-weight:800}
input,select,textarea{width:100%;font:inherit;padding:12px;border:1px solid #b9cbb9;border-radius:6px;margin-top:6px;background:white}
label{display:block;font-weight:600;margin:14px 0}button,.btn{border:0;border-radius:7px;display:inline-block;cursor:pointer;background:var(--forest);color:white;text-decoration:none;padding:12px 18px;font:inherit;font-weight:700}
.btn.alt{background:#19865a}.muted-btn{background:#596d62}.columns{display:grid;grid-template-columns:1fr 1fr;gap:30px}.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.notice{padding:14px;margin:15px 0;background:#f5ead0;border-radius:6px}
table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #ddd;padding:12px;text-align:left;vertical-align:top}section{margin-top:50px}.panel form{margin:0}
footer{background:var(--forest);color:white;text-align:center;padding:25px}
@media(max-width:760px){.grid,.columns{grid-template-columns:1fr}.hero{padding:65px 7%}table{display:block;overflow-x:auto}}
</style></head><body><header><b>🌿 MittiStay</b><nav><a href="/">Home</a><a href="/#rooms">Rooms</a><a href="/#book">Booking</a><a href="/admin">Admin</a></nav></header>
<main>{% for message in get_flashed_messages() %}<p class="notice">{{ message }}</p>{% endfor %}
""" + body + """</main><footer>© {{ year }} MittiStay · Nagla Katilla, Amapur, Kasganj, UP · WhatsApp +91 9098067313</footer></body></html>"""
    return render_template_string(layout, year=date.today().year, csrf=session.get("csrf"), **ctx)

@app.route("/")
def home():
    rooms = db().execute("SELECT * FROM rooms WHERE active=1 ORDER BY id").fetchall()
    body = """
<div class="hero"><p class="kicker">NAGLA KATILLA · AMAPUR · KASGANJ</p><h1>Come as a guest.<br>Leave as family.</h1>
<p>Slow mornings, mango orchards and authentic village hospitality in Uttar Pradesh.</p><p><a class="btn" style="background:#e8bf83;color:#163d30" href="#book">Plan your stay</a></p></div>
<section id="rooms"><p class="kicker" style="color:#4a6d4e">OUR STAYS</p><h2>Stay close to nature</h2>
<div class="grid">{% for room in rooms %}<article class="room"><div class="emoji">{{ ['🌳','🛏️','🏡'][(room.id-1)%3] }}</div><h3>{{ room.name }}</h3><p class="muted">{{ room.description }}</p>
<p class="price">₹{{ room.price }} <small>/ night · indicative</small></p><a class="btn" href="#book">Enquire</a></article>{% endfor %}</div></section>
<section><h2>Experience rural India</h2><div class="grid">
<div class="panel"><h3>🌾 Village walks</h3><p>Enjoy local farms and village pathways.</p></div>
<div class="panel"><h3>🥘 Home-style meals</h3><p>Ask your host about seasonal food.</p></div>
<div class="panel"><h3>🥭 Mango orchards</h3><p>Discover the surroundings.</p></div></div></section>
<section class="columns" id="book"><div><p class="kicker" style="color:#4a6d4e">BOOKING REQUEST</p><h2>Plan your village escape</h2>
<p class="muted">Send your preferred dates. We will review the request and confirm availability. No payment is collected here.</p><p class="notice">A request is not a confirmed reservation. We will contact you before confirmation.</p></div>
<div class="panel"><form action="{{ url_for('book') }}" method="post"><input type="hidden" name="csrf" value="{{ csrf }}">
<label>Full name<input name="name" maxlength="100" required></label><label>Phone / WhatsApp<input name="phone" maxlength="25" required></label>
<label>Email (optional)<input name="email" type="email" maxlength="150"></label>
<label>Room<select name="room_id" required>{% for room in rooms %}<option value="{{ room.id }}">{{ room.name }} — ₹{{ room.price }}/night</option>{% endfor %}</select></label>
<div class="columns" style="gap:12px"><label>Check-in<input type="date" name="checkin" min="{{ today }}" required></label><label>Check-out<input type="date" name="checkout" min="{{ today }}" required></label></div>
<label>Guests<input type="number" name="guests" min="1" max="12" value="2" required></label>
<label>Notes<textarea name="notes" maxlength="500" rows="3"></textarea></label>
<button type="submit">Request Booking</button></form></div></section>
"""
    return page(body, rooms=rooms, today=date.today().isoformat())

@app.post("/book")
def book():
    check_csrf()
    try:
        room_id = int(request.form.get("room_id", ""))
        guests = int(request.form.get("guests", ""))
        checkin = date.fromisoformat(request.form.get("checkin", ""))
        checkout = date.fromisoformat(request.form.get("checkout", ""))
    except ValueError:
        abort(400, "Invalid dates, guests or room.")
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    notes = request.form.get("notes", "").strip()
    if not (1 <= len(name) <= 100 and 7 <= len(phone) <= 25 and len(email) <= 150 and len(notes) <= 500 and 1 <= guests <= 12):
        abort(400, "Please check the form fields.")
    if checkin < date.today() or checkout <= checkin or (checkout - checkin).days > 30:
        abort(400, "Select valid dates (up to 30 nights).")
    conn = db()
    room = conn.execute("SELECT * FROM rooms WHERE id=? AND active=1", (room_id,)).fetchone()
    if not room:
        abort(400, "Room unavailable.")
    blocked = conn.execute("""SELECT 1 FROM bookings WHERE room_id=? AND status='confirmed'
    AND checkin < ? AND checkout > ? LIMIT 1""", (room_id, checkout.isoformat(), checkin.isoformat())).fetchone()
    if blocked:
        flash("This room is already booked for those dates. Please choose another date.")
        return redirect(url_for("home") + "#book")
    conn.execute("""INSERT INTO bookings(room_id,guest_name,phone,email,checkin,checkout,guests,notes)
    VALUES(?,?,?,?,?,?,?,?)""", (room_id,name,phone,email,checkin.isoformat(),checkout.isoformat(),guests,notes))
    conn.commit()
    return page("""<section class="panel"><h1>Thank you!</h1><h3>Your booking request has been received.</h3>
<p>Our team will review dates and contact you. This is <b>not yet a confirmed booking</b>.</p>
<a class="btn alt" target="_blank" rel="noopener noreferrer" href="{{ whatsapp_link }}">Follow up on WhatsApp</a> <a class="btn" href="/">Back home</a></section>""",
        whatsapp_link="https://wa.me/" + setting("whatsapp") + "?text=Hello%20MittiStay%2C%20I%20submitted%20a%20booking%20request.")

@app.route("/admin/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        check_csrf()
        supplied = request.form.get("password", "")
        valid = (check_password_hash(ADMIN_PASSWORD_HASH, supplied) if ADMIN_PASSWORD_HASH else
                 bool(ADMIN_PASSWORD) and secrets.compare_digest(ADMIN_PASSWORD, supplied))
        if valid:
            session.clear()
            session["admin"] = True
            session["csrf"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin"))
        flash("Invalid password or admin password not configured.")
    return page("""<section class="panel" style="max-width:450px;margin:auto"><h2>Admin login</h2>
<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}"><label>Password<input name="password" type="password" required></label>
<button>Sign in</button></form><p class="muted">Configure ADMIN_PASSWORD_HASH or ADMIN_PASSWORD in your server environment.</p></section>""")

@app.post("/admin/logout")
@admin_required
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin():
    rooms = db().execute("SELECT * FROM rooms ORDER BY id").fetchall()
    bookings = db().execute("""SELECT b.*,r.name AS room_name FROM bookings b
    JOIN rooms r ON b.room_id=r.id ORDER BY b.created_at DESC,b.id DESC LIMIT 200""").fetchall()
    body = """
<section><div class="row"><h1>Admin Dashboard</h1><form method="post" action="{{ url_for('logout') }}"><input type="hidden" name="csrf" value="{{ csrf }}"><button class="muted-btn">Logout</button></form></div>
<p class="muted">Manage your rooms, WhatsApp number and booking requests. Set prices only after confirming them.</p></section>
<section class="panel"><h2>WhatsApp settings</h2><form method="post" action="{{ url_for('admin_settings') }}"><input type="hidden" name="csrf" value="{{ csrf }}">
<label>WhatsApp with country code<input name="whatsapp" value="{{ whatsapp }}" pattern="[0-9]{10,15}" required></label><button>Save number</button></form></section>
<section><h2>Rooms</h2><div class="grid">{% for room in rooms %}<div class="panel"><form action="{{ url_for('admin_room',room_id=room.id) }}" method="post">
<input type="hidden" name="csrf" value="{{ csrf }}"><label>Room name<input name="name" value="{{ room.name }}" required maxlength="100"></label>
<label>Price ₹ per night<input type="number" name="price" value="{{ room.price }}" min="0" max="1000000" required></label>
<label>Description<textarea name="description" rows="4" maxlength="500">{{ room.description }}</textarea></label>
<label><input type="checkbox" style="width:auto" name="active" value="1" {% if room.active %}checked{% endif %}> Visible to guests</label><button>Save room</button></form></div>{% endfor %}</div></section>
<section><h2>Booking requests</h2><div class="panel"><table><thead><tr><th>Guest</th><th>Room & dates</th><th>Status</th><th>Change status</th></tr></thead><tbody>
{% for b in bookings %}<tr><td><b>{{ b.guest_name }}</b><p>{{ b.phone }}</p><p>{{ b.email }}</p><p class="muted">{{ b.notes }}</p></td>
<td>{{ b.room_name }}<p>{{ b.checkin }} → {{ b.checkout }}</p><small>{{ b.guests }} guest(s)</small></td>
<td>{{ b.status }}</td><td><form method="post" action="{{ url_for('admin_booking',booking_id=b.id) }}">
<input type="hidden" name="csrf" value="{{ csrf }}"><select name="status"><option value="pending" {% if b.status=='pending' %}selected{% endif %}>Pending</option>
<option value="confirmed" {% if b.status=='confirmed' %}selected{% endif %}>Confirmed</option>
<option value="cancelled" {% if b.status=='cancelled' %}selected{% endif %}>Cancelled</option></select><button style="margin-top:8px">Update</button></form></td></tr>
{% else %}<tr><td colspan="4">No booking requests yet.</td></tr>{% endfor %}</tbody></table></div></section>
"""
    return page(body, rooms=rooms, bookings=bookings, whatsapp=setting("whatsapp"))

@app.post("/admin/settings")
@admin_required
def admin_settings():
    check_csrf()
    number = request.form.get("whatsapp", "").strip()
    if not (number.isdigit() and 10 <= len(number) <= 15):
        abort(400, "Use 10–15 digits with country code.")
    db().execute("UPDATE settings SET value=? WHERE key='whatsapp'", (number,))
    db().commit()
    flash("WhatsApp updated.")
    return redirect(url_for("admin"))

@app.post("/admin/rooms/<int:room_id>")
@admin_required
def admin_room(room_id):
    check_csrf()
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    try:
        price = int(request.form.get("price", ""))
    except ValueError:
        abort(400)
    if not (name and len(name) <= 100 and len(description) <= 500 and 0 <= price <= 1000000):
        abort(400)
    d = db()
    r = d.execute("UPDATE rooms SET name=?,description=?,price=?,active=? WHERE id=?",
        (name,description,price,int(request.form.get("active") == "1"),room_id))
    if not r.rowcount:
        abort(404)
    d.commit()
    flash("Room updated.")
    return redirect(url_for("admin"))

@app.post("/admin/bookings/<int:booking_id>")
@admin_required
def admin_booking(booking_id):
    check_csrf()
    status = request.form.get("status", "")
    if status not in {"pending","confirmed","cancelled"}:
        abort(400)
    d = db()
    booking = d.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
    if not booking:
        abort(404)
    if status == "confirmed":
        conflict = d.execute("""SELECT 1 FROM bookings WHERE id<>? AND room_id=? AND status='confirmed'
        AND checkin < ? AND checkout > ? LIMIT 1""",
        (booking_id,booking["room_id"],booking["checkout"],booking["checkin"])).fetchone()
        if conflict:
            flash("Cannot confirm: dates overlap another confirmed booking.")
            return redirect(url_for("admin"))
    d.execute("UPDATE bookings SET status=? WHERE id=?", (status,booking_id))
    d.commit()
    flash("Booking status updated. Contact the guest directly; automatic notifications are not configured.")
    return redirect(url_for("admin"))

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT","8000")), debug=False)
