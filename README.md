# MittiStay — Village Homestay Demo

MittiStay is a village homestay prototype for **Nagla Katilla, Amapur, Kasganj, Uttar Pradesh, India**, initially featuring three rooms.

## Preview locally

Open `index.html` in your browser or run:

```bash
python3 -m http.server 8000
```

Visit `http://localhost:8000/` for the guest site or `http://localhost:8000/admin.html` for the demo settings page.

## Features

- Responsive homepage with Hindi/English toggle.
- Three indicative room options and village experiences.
- WhatsApp booking enquiries to **+91 9098067313** via `wa.me/919098067313`.
- Browser-only demo dashboard for room descriptions, prices, visibility, and WhatsApp settings.

## Important limitations

**This is not a production booking platform.** The booking enquiry opens a WhatsApp message that the visitor must send. No online payments, availability checks, reservation confirmation, shared database, live guest sync, or authenticated admin login exist. Demo settings are stored only in the current browser's localStorage. Do not use the public admin demo for guest personal information.

For production, add a backend, secure authentication, booking database, overlap checks, payment provider, privacy controls and notifications before allowing real reservations. All room descriptions, amenities and indicative prices must be confirmed.
