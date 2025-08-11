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
- `arye_site/` הגדרות הפרויקט.
- `main/` האפליקציה הראשית עם התבנית `home.html`.

## שינוי הטקסט
עריכת הקובץ `main/templates/home.html`.

בהצלחה!
