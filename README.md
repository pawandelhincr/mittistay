# MittiStay — Dynamic Village Homestay Booking MVP

MittiStay is a rural homestay website for **Nagla Katilla, Amapur, Kasganj, Uttar Pradesh, India**, initially offering three rooms.

## Dynamic app (Flask + SQLite)

The dynamic application lives in **`app.py`**.

- Room listings and prices are read from a SQLite database.
- Guests can submit a booking request; requests are stored in SQLite with **pending** status.
- Password-protected admin screen for room names, descriptions, nightly prices, visibility, WhatsApp number and booking status.
- Admin can mark requests pending, confirmed or cancelled. Confirmed bookings cannot overlap on the same room.
- WhatsApp follow-up number defaults to **+91 9098067313**.
- There is **no payment collection** or automatic booking confirmation.

**Note:** `index.html` and `admin.html` are older browser-only static demos. For the dynamic version, start the Flask server and visit `/` and `/admin`; do not use `python3 -m http.server` for the dynamic app.

## Run locally on MacBook

Clone the repository and install packages:

```bash
git clone https://github.com/pawandelhincr/mittistay.git
cd mittistay
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create credentials **in your own terminal** (do not paste secrets in chat or commit them):

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD='replace-this-with-your-own-strong-password'
python app.py
```

Open:
- Guest website: http://127.0.0.1:8000/
- Admin dashboard: http://127.0.0.1:8000/admin
- Admin login: http://127.0.0.1:8000/admin/login

The SQLite database is created automatically in `mittistay.sqlite3`. It is excluded from Git by `.gitignore`. Keep the database persistent and backed up.

If you have an existing clone, run `git pull origin main` before starting.

## Deploy

GitHub only stores the code. **GitHub Pages cannot run this Python/Flask backend**. Deploy to a service supporting Python server processes and a durable filesystem/database. Install dependencies from `requirements.txt`, use the `Procfile` command (or `gunicorn app:app`), and set your credentials in the hosting provider's environment settings. Set `COOKIE_SECURE=1` when hosted behind HTTPS. Set `DATABASE_PATH` to persistent storage; an ephemeral filesystem will lose bookings.

The supplied Flask app is an **MVP**. Before accepting real guest bookings publicly, add production-grade rate limiting, email/phone verification, notification delivery, multi-worker booking-lock guarantees, monitoring, backups, data privacy controls, password-hash authentication and a proper database (PostgreSQL is recommended). Price and amenity details are placeholders for verification. There is no payment gateway, photo management or domain setup yet.

## Repo files

- `app.py` — dynamic Flask application
- `requirements.txt` — Python dependencies
- `Procfile` — server launch command for compatible hosts
- `.env.example` — environment variable names (not actual secrets)
- `.gitignore` — prevents local secrets and databases from being committed
- `index.html`, `admin.html` — original static demos
