# SafeKaNiño

Flask web app for barangay incident reporting and mediation.

## Run
```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

## Demo accounts
- **Admin**: `admin` / `admin123`
- **Citizen**: `citizen` / `citizen123`

## Testing flow
1. Log in as **citizen** and submit a report from any of the 4 types.
2. Log in as **admin** — the dashboard notification icon shows a badge and the
   Notifications panel lists the new report (reporter name + incident type).
3. Open **Status Reports**, click **View** to inspect the full submission in
   a modal whose fields match the incident type.
4. Click **Export** to download a CSV of all current reports.
5. Open **Mediation**, click **+ Schedule New Hearing**, pick a pending
   report, set a date/time and save. The report moves to *In Progress*.
6. Use the **Update Status** button on a hearing to move it to *In Progress*
   or *Settled* — Status Reports reflect the change immediately.
7. Status Reports pagination uses continuous numbering (1–10, 11–20, …).
