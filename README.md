# Arye Single Page Django Site

אתר דג'נגו קטן עם דף אחד שמציג את המילה "אריה".

## הפעלה מקומית

1. יצירת והפעלת סביבת פייתון (כבר נוצרה `.venv`):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. התקנת חבילות (כבר מותקן Django, להרצה עתידית):
```powershell
pip install django
```
3. הרצת שרת פיתוח:
```powershell
python manage.py runserver
```
4. גלישה לכתובת:
```
http://127.0.0.1:8000/
```

## מבנה

## שינוי הטקסט
עריכת הקובץ `main/templates/home.html`.

## Deployment (DigitalOcean App Platform)
1) Push to GitHub (already configured). Connect the repo in DigitalOcean.
2) App Platform settings:
	- Environment: Python
	- Build & Run commands: pip install -r requirements.txt; python manage.py collectstatic --noinput; python manage.py migrate; (Run) Procfile web command
	- HTTP Port: use $PORT (App Platform injects it)
	- Environment variables:
	  - DJANGO_SECRET_KEY: <secure random>
	  - DJANGO_DEBUG: false
	  - DJANGO_ALLOWED_HOSTS: your-app.onrender.com,your-domain.com (domains separated by comma)
	  - DJANGO_CSRF_TRUSTED_ORIGINS: https://your-app.ondigitalocean.app,https://your-domain.com
	  - DATABASE_URL (if using managed Postgres) and set Django DATABASES accordingly (future)
3) Static files:
	- WhiteNoise is enabled; collectstatic outputs to staticfiles_build
4) Media files:
	- For production, use a bucket (Spaces/S3) or keep local only if ephemeral is acceptable (not recommended).

## Local run
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
בהצלחה!
