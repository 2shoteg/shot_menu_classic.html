import requests
import csv
import io
import re
import json

# =============================================
# 🔗 رابط Google Sheets (CSV)
# =============================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNymcwLC-PZdkS07k46Yg3dIYhtUoWIsXypczOI0UcV3woXR7xXZkKFh60jJMn0-xH-q6j60P0aXWt/pub?gid=0&single=true&output=csv"

def fetch_sheet():
    print("📥 جاري تحميل البيانات من Google Sheets...")
    r = requests.get(SHEET_URL)
    r.encoding = 'utf-8'
    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)

def parse_data(rows):
    cats = {}
    cat_order = []
    for row in rows:
        cid = row.get('category_id', '').strip()
        if not cid:
            continue
        if cid not in cats:
            cats[cid] = {
                'icon': row.get('category_icon', '').strip(),
                'ar': row.get('category_ar', '').strip(),
                'en': row.get('category_en', '').strip(),
                'items': [],
                'addons': []
            }
            cat_order.append(cid)
        rtype = row.get('type', '').strip().lower()
        name_ar = row.get('name_ar', '').strip()
        name_en = row.get('name_en', '').strip()
        price = row.get('price', '').strip()
        seasonal = row.get('seasonal', '').strip()
        if not name_ar or not price:
            continue
        entry = {'ar': name_ar, 'en': name_en, 'p': int(price)}
        if seasonal == '1':
            entry['b'] = 1
        if rtype == 'addon':
            cats[cid]['addons'].append(entry)
        else:
            cats[cid]['items'].append(entry)
    return cats, cat_order

def build_cats_js(cats, cat_order):
    lines = []
    for cid in cat_order:
        c = cats[cid]
        items_js = json.dumps(c['items'], ensure_ascii=False)
        addons_js = json.dumps(c['addons'], ensure_ascii=False)
        def to_js_obj(s):
            s = re.sub(r'"ar":', 'ar:', s)
            s = re.sub(r'"en":', 'en:', s)
            s = re.sub(r'"p":', 'p:', s)
            s = re.sub(r'"b":', 'b:', s)
            return s
        lines.append(
            f'  {cid}:{{icon:"{c["icon"]}",ar:"{c["ar"]}",en:"{c["en"]}",\n'
            f'    items:{to_js_obj(items_js)},\n'
            f'    addons:{to_js_obj(addons_js)}}}'
        )
    return 'const cats = {\n' + ',\n'.join(lines) + '\n};'

def build_grid_html(cats, cat_order):
    html = ''
    for cid in cat_order:
        c = cats[cid]
        html += f'      <div class="cat-card" onclick="showCat(\'{cid}\')"><span class="ci">{c["icon"]}</span><span class="ca">{c["ar"]}</span><span class="ce">{c["en"]}</span></div>\n'
    return html

def main():
    # 1. قرا الملف الحالي كما هو
    with open("menu.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 2. حمّل البيانات من الشيت
    rows = fetch_sheet()
    print(f"✅ تم تحميل {len(rows)} صف")
    cats, cat_order = parse_data(rows)
    print(f"✅ تم تحليل {len(cats)} كاتيجوري: {', '.join(cat_order)}")

    # 3. استبدل const cats فقط - مش أي حاجة تانية
    new_cats_js = build_cats_js(cats, cat_order)
    html = re.sub(
        r'const cats = \{.*?\n\};',
        new_cats_js,
        html,
        flags=re.DOTALL
    )

    # 4. استبدل الـ grid بتاع الكاتيجوريز في الـ HTML
    new_grid = build_grid_html(cats, cat_order)
    html = re.sub(
        r'(<div class="grid">)\s*.*?(\s*</div>\s*\n\s*<footer)',
        lambda m: m.group(1) + '\n' + new_grid + '    ' + m.group(2),
        html,
        flags=re.DOTALL
    )

    # 5. احفظ الملف
    with open("menu.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ تم تحديث menu.html بنجاح! (بدون تغيير أي حاجة تانية)")

if __name__ == "__main__":
    main()
