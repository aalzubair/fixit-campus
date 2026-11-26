Here's the whole process, step by step. Commands are for a terminal opened in your project folder.

## 1. Put the changes into your project
1. Download `fixit_f3_f4.patch` from my last message and save it in the **root** of your `fixit-campus` folder (the one containing `CLAUDE.md`).
2. Switch to your feature branch and apply it:
```
git checkout "feature/F3-Submit-Complaint,F4-Track/Reopen/Browse"
git apply fixit_f3_f4.patch
```
If `git apply` complains, tell me the error message. Alternatively, unzip `fixit_f3_f4_files.zip` into the project root and let it overwrite the files.

## 2. Set up and start the app
```
python -m venv venv
venv\Scripts\activate          (Windows)   |   source venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
cd src
python manage.py migrate
python manage.py runserver
```
`migrate` creates the new Complaint and Follow tables. Leave the terminal running, then open **http://127.0.0.1:8000/register/** in your browser.

## 3. Create a user and try it
1. Register with a test ID from `src/campus/data/iub_records.json`, for example **2310001** (student), and pick a password.
2. The OTP isn't emailed. It's **printed in the terminal** where `runserver` is running. Copy it into the verify page.
3. Log in. On the home page you'll see three buttons: **Submit Complaint**, **Existing Complaints**, **My Complaints**.

To test following, you need a second person. Open a private/incognito window and register **2310002** (faculty), then:
- As 2310001, submit a complaint.
- As 2310002, submit a complaint with the same category and location. The "Already reported?" panel on the right should show the first one with a **Follow** button.
- Check **Existing Complaints**, **My Complaints → Following**, and try the filters.

## 4. Test the reopen feature
There's no staff screen yet to mark a complaint Resolved, so do it by hand. Stop nothing; open a **second terminal** in `src` with the venv active:
```
python manage.py shell
```
```python
from django.utils import timezone
from campus.models import Complaint
c = Complaint.objects.get(complaint_id="CMP-2026-00001")
c.status = "resolved"
c.resolved_at = timezone.now()
c.save()
```
Reload **My Complaints → View**: a **Reopen complaint** button appears. For the "over 7 days" message, use this instead of `timezone.now()`:
```python
from datetime import timedelta
c.resolved_at = timezone.now() - timedelta(days=8)
```

## 5. Run the automated tests
```
python manage.py test
```
You should see `Ran 352 tests ... OK`.

Which step are you on, and did anything show an error? Paste the message and I'll help you fix it.
