import requests
import csv
import io
import re
import json
import hashlib

# =============================================
# 🔗 روابط Google Sheets
# =============================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNymcwLC-PZdkS07k46Yg3dIYhtUoWIsXypczOI0UcV3woXR7xXZkKFh60jJMn0-xH-q6j60P0aXWt/pub?gid=0&single=true&output=csv"
OFFERS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNymcwLC-PZdkS07k46Yg3dIYhtUoWIsXypczOI0UcV3woXR7xXZkKFh60jJMn0-xH-q6j60P0aXWt/pub?gid=1081349164&single=true&output=csv"

def fetch_csv(url):
    r = requests.get(url)
    r.encoding = 'utf-8'
    return list(csv.DictReader(io.StringIO(r.text)))

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
        price_m = row.get('price_m', '').strip()
        price_l = row.get('price_l', '').strip()
        if price_m and price_l:
            entry['pm'] = int(price_m)
            entry['pl'] = int(price_l)
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
            s = re.sub(r'"pm":', 'pm:', s)
            s = re.sub(r'"pl":', 'pl:', s)
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

def mk_id(text):
    return 'off_' + hashlib.md5(text.encode()).hexdigest()[:6]

def build_offers_html(offers):
    html = ''
    for o in offers:
        name_ar = o.get('name_ar', '').strip()
        name_en = o.get('name_en', '').strip()
        price   = o.get('price', '').strip()
        save_ar = o.get('save_ar', '').strip()
        icon    = o.get('icon', '').strip()
        if not name_ar or not price:
            continue
        oid = mk_id(name_ar)
        display_ar = f"{icon} {name_ar}" if icon else name_ar
        html += f'''      <div class="offer-card">
        <div class="offer-ar">{display_ar}</div>
        <div class="offer-en">{name_en}</div>
        <div class="offer-bottom">
          <div class="offer-price">{price} <span>ج</span></div>
          <span class="offer-save">{save_ar}</span>
        </div>
        <div class="qty-row" style="justify-content:center;margin-top:14px">
          <button class="qty-btn" onclick="chg('{oid}','{display_ar}',{price},-1,'العروض')">−</button>
          <span class="qty-num" id="q_{oid}">0</span>
          <button class="qty-btn" onclick="chg('{oid}','{display_ar}',{price},1,'العروض')">+</button>
        </div>
      </div>\n'''
    return html

def main():
    # 1. قرا الملف الحالي
    with open("menu.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 2. حدّث المنتجات
    print("📥 تحميل المنتجات...")
    rows = fetch_csv(SHEET_URL)
    cats, cat_order = parse_data(rows)
    print(f"✅ {len(cats)} كاتيجوري")

    # استبدل const cats
    new_cats_js = build_cats_js(cats, cat_order)
    html = re.sub(r'const cats = \{.*?\n\};', new_cats_js, html, flags=re.DOTALL)

    # استبدل الـ grid
    new_grid = build_grid_html(cats, cat_order)
    html = re.sub(
        r'(<div class="grid">)\s*.*?(\s*</div>\s*\n\s*<footer)',
        lambda m: m.group(1) + '\n' + new_grid + '    ' + m.group(2),
        html, flags=re.DOTALL
    )

    # 3. حدّث العروض
    print("📥 تحميل العروض...")
    offers = fetch_csv(OFFERS_URL)
    print(f"✅ {len(offers)} عرض")

    new_offers_html = build_offers_html(offers)
    html = re.sub(
        r'(<div class="offers-grid">)\s*.*?(\s*</div>\s*\n\s*<footer)',
        lambda m: m.group(1) + '\n' + new_offers_html + '    ' + m.group(2),
        html, flags=re.DOTALL
    )

    # 4. احفظ
    with open("menu.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ تم تحديث menu.html بنجاح!")

if __name__ == "__main__":
    main()
