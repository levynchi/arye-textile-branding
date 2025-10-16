# הגדרת CDN לאופטימיזציה של ביצועים

## סיכום השינויים

האתר עודכן להשתמש ב-CDN של DigitalOcean Spaces לטעינה מהירה של תמונות.

## משתני סביבה נדרשים ב-DigitalOcean App Platform

וודא שהמשתנים הבאים מוגדרים ב-Environment Variables:

```
AWS_STORAGE_BUCKET_NAME=arye-textil-media
AWS_S3_REGION_NAME=fra1
AWS_S3_ENDPOINT_URL=https://fra1.digitaloceanspaces.com
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
CDN_DOMAIN=arye-textil-media.fra1.cdn.digitaloceanspaces.com
```

### ⚠️ חשוב מאוד!

- `AWS_S3_ENDPOINT_URL` נשאר ה-direct endpoint (לכתיבה)
- `CDN_DOMAIN` הוא ה-CDN endpoint (לקריאה/הצגה)
- שים לב ל-`.cdn.` בתוך הכתובת של CDN_DOMAIN

## מה השתנה בקוד?

### 1. `arye_site/settings/base.py`

- **שורה 120**: שינוי default region מ-`nyc3` ל-`fra1`
- **שורות 126-129**: הוספת Cache-Control headers (24 שעות)
- **שורות 131-137**: שימוש ב-CDN domain דרך `AWS_S3_CUSTOM_DOMAIN`
- **שורה 69**: העלאת `conn_max_age` מ-600 ל-1800 שניות (30 דקות)

### 2. כל התבניות HTML

הוספנו בכל תבנית (10 קבצים) את השורות הבאות ב-`<head>`:

```html
<link rel="dns-prefetch" href="https://arye-textil-media.fra1.cdn.digitaloceanspaces.com">
<link rel="preconnect" href="https://arye-textil-media.fra1.cdn.digitaloceanspaces.com" crossorigin>
```

זה מאפשר לדפדפן להתחיל את החיבור ל-CDN כבר לפני שהוא מגלה את התמונות בעמוד.

## תוצאות צפויות

✅ טעינת תמונות מהירה פי 3-5 (תלוי במיקום המשתמש)  
✅ התמונות נשמרות ב-cache ב-edge locations קרוב יותר למשתמשים  
✅ הדפדפן שומר תמונות ב-cache מקומי ל-24 שעות  
✅ פחות עומס על ה-Spaces origin  
✅ חיבור מהיר יותר לדאטה-בייס (connection pooling משופר)

## איך לבדוק שזה עובד?

אחרי deploy:

1. פתח את האתר
2. לחץ F12 (Developer Tools)
3. לך ל-Network tab
4. רענן את העמוד
5. לחץ על אחת התמונות
6. בדוק ש-URL מתחיל ב-`https://arye-textil-media.fra1.cdn.digitaloceanspaces.com`
7. בדוק את ה-Response Headers - צריך לראות `cache-control: max-age=86400`

## פתרון בעיות

### התמונות עדיין מגיעות מה-direct endpoint

- וודא ש-`CDN_DOMAIN` מוגדר נכון ב-Environment Variables
- עשה redeploy של האפליקציה
- בדוק את הלוגים שאין שגיאות

### התמונות לא נטענות בכלל

- וודא שה-Spaces bucket מוגדר כ-public
- וודא שה-CORS מוגדר נכון ב-Spaces settings
- בדוק שה-CDN endpoint אכן זמין: נסה לפתוח תמונה ישירות בדפדפן

### שגיאת CORS

הוסף ב-Spaces Settings → CORS Configuration:

```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

## עדכונים עתידיים מומלצים

1. **Image Optimization**: שקול לכווץ תמונות גדולות (> 1MB) לפני העלאה
2. **WebP Format**: המר תמונות ל-WebP לגודל קטן יותר
3. **Responsive Images**: השתמש ב-srcset לגדלים שונים
4. **Lazy Loading**: כבר מוגדר ב-HTML (`loading="lazy"`)
5. **Image CDN**: שקול שימוש ב-service כמו Cloudinary או ImageKit לאופטימיזציה אוטומטית

---

**תאריך עדכון**: אוקטובר 2025  
**גרסה**: 1.0

