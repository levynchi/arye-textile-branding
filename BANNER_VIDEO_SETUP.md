# הוספת תמיכה בוידיאו לבאנרים

## סיכום השינויים

הוספנו אפשרות להעלות וידיאו לבאנרים במקום תמונה, עם תמונה כגיבוי.

## מה השתנה?

### 1. **`main/models.py`** - מודל Banner

✅ **שורה 47**: עדכון help_text של שדה `image` - "גיבוי לוידיאו"  
✅ **שורה 48**: הוספת שדה `video` חדש:
```python
video = models.FileField(upload_to="banner/videos/", blank=True, null=True, help_text="וידיאו באנר (אופציונלי) - יתעדף על פני תמונה")
```

### 2. **`main/admin.py`** - ממשק Admin

✅ **שורות 112-124**: עדכון BannerAdmin:
- הוספת `video` ל-fields
- הוספת `has_video` ו-`has_image` ל-list_display (מציג ✓/✗)
- סדר השדות: `page`, `video`, `image`, `height_variant`, `updated`

### 3. **`static/main.css`** - עיצוב וידיאו

✅ **שורות 59-60**: הוספת CSS לוידיאו:
```css
.hero-video{
    position:absolute;
    top:0;
    left:0;
    width:100%;
    height:100%;
    object-fit:cover;
    z-index:0;
}
```

### 4. **Migration** - `0027_add_video_field_to_banner.py`

✅ הוספת השדה לדאטה-בייס

## איך זה עובד?

### לוגיקה בתבנית (`partials/hero.html`)

התבנית כבר מוכנה ומטפלת בוידיאו:

```html
{# Video banner - takes priority over image #}
{% if banner and banner.video %}
    <video class="hero-video" autoplay muted loop playsinline>
        <source src="{{ banner.video.url }}" type="video/mp4">
        <source src="{{ banner.video.url }}" type="video/webm">
        <source src="{{ banner.video.url }}" type="video/ogg">
    </video>
{% elif banner and banner.image %}
    {# Fallback to image #}
{% endif %}
```

### סדר עדיפויות:
1. **וידיאו** - אם קיים, יוצג וידיאו
2. **תמונה** - אם אין וידיאו, יוצג תמונה
3. **רקע ברירת מחדל** - אם אין אף אחד

## איך להשתמש?

### 1. כנס לאדמין
```
https://arye-textil.co.il/admin/main/banner/
```

### 2. בחר באנר לעריכה
למשל: Banner #3 לתדמיתנות

### 3. העלה וידיאו
- **וידיאו**: בחר קובץ וידיאו (MP4 מומלץ)
- **תמונה**: השאר כגיבוי למקרה שהוידיאו לא עובד

### 4. שמור

## המלצות לוידיאו

### פורמטים נתמכים:
- **MP4** (מומלץ ביותר)
- **WebM** (לקבצים קטנים יותר)
- **OGV** (תמיכה נוספת)

### אופטימיזציה:
- **גודל**: עד 10MB מומלץ
- **אורך**: 10-30 שניות
- **רזולוציה**: 1920x1080 או 1280x720
- **Bitrate**: 2-5 Mbps
- **לולאה**: הוידיאו יותחל אוטומטית בלולאה

### תכונות הוידיאו:
- ✅ **autoplay** - מתחיל אוטומטית
- ✅ **muted** - שקט (נדרש לautoplay)
- ✅ **loop** - חוזר על עצמו
- ✅ **playsinline** - עובד על מובייל

## CSS נוסף

הוידיאו מעוצב כך ש:
- **ממלא את כל הבאנר** (`width:100%; height:100%`)
- **שומר על פרופורציות** (`object-fit:cover`)
- **נמצא מאחורי הטקסט** (`z-index:0`)
- **מכסה את כל הבאנר** (`position:absolute`)

## פתרון בעיות

### הוידיאו לא נטען
1. בדוק שהקובץ בפורמט נתמך (MP4)
2. וודא שהקובץ לא גדול מדי (>20MB)
3. בדוק שהוידיאו לא פגום

### הוידיאו לא מתחיל אוטומטית
- זה נורמלי בדפדפנים מסוימים (Chrome/Safari)
- הוידיאו יתחיל כשהמשתמש יקליק עליו

### הוידיאו לא מתאים לגודל הבאנר
- ה-CSS כבר מטפל בזה עם `object-fit:cover`
- הוידיאו ייחתך בצורה חכמה כדי למלא את הבאנר

### בעיות ביצועים
- השתמש בקבצים קטנים יותר
- דחוס את הוידיאו לפני העלאה
- שקול להשתמש ב-WebM לקבצים קטנים יותר

---

**תאריך עדכון**: אוקטובר 2025  
**גרסה**: 1.0

## עדכונים עתידיים אפשריים

1. **Video Optimization**: דחיסה אוטומטית של וידיאו
2. **Multiple Formats**: המרה אוטומטית למספר פורמטים
3. **Thumbnail Generation**: יצירת תמונת תצוגה אוטומטית
4. **Video Controls**: אפשרות להציג controls למשתמש
5. **Lazy Loading**: טעינת וידיאו רק כשהבאנר נראה
