# -*- coding: utf-8 -*-
import os
import time
import re
import io
import base64
import colorsys
from datetime import datetime
from functools import lru_cache

from flask import Flask, request, render_template_string, make_response, jsonify
from PIL import Image, ImageDraw, ImageFont

try:
    import requests
except ImportError:
    requests = None

app = Flask(__name__)

# ============================ الإعدادات الأساسية ============================
WORKSHOP_NAME = "أبو القيس"
WORKSHOP_PHONE = "05466126354"
IBAN_INFO = "TR00 0000 0000 0000 0000 0000 00"  # ضع الآيبان الخاص بك هنا
PRO_PRICE = "250 TL / شهرياً"
ADMIN_UNLOCK_CODE = "QAIS2026"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# ============================ قاموس اللغات ============================
TR = {
    "ar": {
        "dir": "rtl", "title": "أبو القيس - نظام النجارة المتكامل",
        "sub": "نظام تقطيع الأخشاب والتسعير | هاتف: " + WORKSHOP_PHONE,
        "tab_cut": "📐 التقطيع والطلب", "tab_set": "⚙️ الأسعار والعملات", "tab_acc": "🔩 الإكسسوارات",
        "mat_lbl": "نوع الخشب:", "sw_lbl": "طول اللوح (مم)", "sh_lbl": "عرض اللوح (مم)",
        "kerf_lbl": "سمك المنشار (Kerf)", "rot_lbl": "تدوير القطع", "yes": "مسموح", "no": "ممنوع",
        "pieces_lbl": "المقاسات (الطول العرض العدد الحواف):",
        "pieces_ph": "800 600 4 2\n1200 400 2 LL\n450 300 6",
        "ocr_lbl": "📸 قراءة فورية بالذكاء الاصطناعي (كاميرا أو صورة):",
        "cam_btn": "📷 تصوير بالكاميرا",
        "gal_btn": "🖼️ اختيار صورة",
        "reading": "⏳ جاري قراءة المقاسات من الصورة...",
        "curr_lbl": "العملة:", "rate_usd": "سعر الدولار (TL)", "rate_eur": "سعر اليورو (TL)",
        "p_sheet": "سعر اللوح (TL)", "p_pvc": "سعر متر PVC (TL)", "p_cut": "أجرة قص اللوح (TL)", "margin": "هامش الربح (%)",
        "acc_hinge": "عدد المفصلات (Menteşe)", "acc_hinge_p": "سعر المفصلة (TL)",
        "acc_rail": "عدد سكك الجوارير (Ray)", "acc_rail_p": "سعر السكة (TL)",
        "acc_handle": "عدد المقابض (Kulp)", "acc_handle_p": "سعر المقبض (TL)",
        "btn_calc": "🚀 احسب التقطيع وأصدر الفاتورة",
        "inv_title": "🧾 الفاتورة الجاهزة للزبون:", "dl_btn": "⬇️ تحميل الصورة",
        "sheets_title": "📐 مخططات التقطيع:",
        "pay_title": "🔒 انتهت تجربتك المجانية",
        "pay_desc": "للاستمرار في استخدام النظام، يرجى الاشتراك في باقة Pro",
        "pay_btn": "🔓 تفعيل الاشتراك", "pay_ph": "أدخل كود التفعيل..."
    },
    "tr": {
        "dir": "ltr", "title": "Abu Al-Qais - Kesim Optimizasyon",
        "sub": "Ahşap Kesim ve Maliyet Sistemi | Tel: " + WORKSHOP_PHONE,
        "tab_cut": "📐 Kesim & Sipariş", "tab_set": "⚙️ Fiyat & Döviz", "tab_acc": "🔩 Aksesuar",
        "mat_lbl": "Malzeme Türü:", "sw_lbl": "Plaka Boyu (mm)", "sh_lbl": "Plaka Eni (mm)",
        "kerf_lbl": "Testere Payı (Kerf)", "rot_lbl": "Döndürme", "yes": "Serbest", "no": "Yasak",
        "pieces_lbl": "Ölçüler (Boy En Adet Kenar):",
        "pieces_ph": "800 600 4 2\n1200 400 2 LL\n450 300 6",
        "ocr_lbl": "📸 Yapay Zeka ile Anında Okuma (Kamera veya Fotoğraf):",
        "cam_btn": "📷 Kamera ile Çek",
        "gal_btn": "🖼️ Galeriden Seç",
        "reading": "⏳ Ölçüler okunuyor...",
        "curr_lbl": "Para Birimi:", "rate_usd": "Dolar Kuru (TL)", "rate_eur": "Euro Kuru (TL)",
        "p_sheet": "Plaka Fiyatı (TL)", "p_pvc": "PVC Metre (TL)", "p_cut": "Kesim Ücreti (TL)", "margin": "Kar Marjı (%)",
        "acc_hinge": "Menteşe Adedi", "acc_hinge_p": "Menteşe Fiyatı (TL)",
        "acc_rail": "Çekmece Rayı", "acc_rail_p": "Ray Fiyatı (TL)",
        "acc_handle": "Kulp Adedi", "acc_handle_p": "Kulp Fiyatı (TL)",
        "btn_calc": "🚀 Hesapla ve Fatura Oluştur",
        "inv_title": "🧾 Müşteri Faturası:", "dl_btn": "⬇️ Resmi İndir",
        "sheets_title": "📐 Kesim Planları:",
        "pay_title": "🔒 Ücretsiz Deneme Bitti",
        "pay_desc": "Devam etmek için Pro pakete geçin",
        "pay_btn": "🔓 Aktifleştir", "pay_ph": "Aktivasyon kodu..."
    },
    "en": {
        "dir": "ltr", "title": "Abu Al-Qais - Woodwork Pro",
        "sub": "Cutting & Costing System | Tel: " + WORKSHOP_PHONE,
        "tab_cut": "📐 Cutting", "tab_set": "⚙️ Prices & Currency", "tab_acc": "🔩 Hardware",
        "mat_lbl": "Material:", "sw_lbl": "Sheet Length (mm)", "sh_lbl": "Sheet Width (mm)",
        "kerf_lbl": "Saw Kerf (mm)", "rot_lbl": "Rotation", "yes": "Allowed", "no": "Forbidden",
        "pieces_lbl": "Dimensions (L W Qty Edges):",
        "pieces_ph": "800 600 4 2\n1200 400 2 LL\n450 300 6",
        "ocr_lbl": "📸 Instant AI Reading (Camera or Photo):",
        "cam_btn": "📷 Take Photo",
        "gal_btn": "🖼️ Choose Image",
        "reading": "⏳ Reading dimensions...",
        "curr_lbl": "Currency:", "rate_usd": "USD Rate (TL)", "rate_eur": "EUR Rate (TL)",
        "p_sheet": "Sheet Price (TL)", "p_pvc": "PVC / m (TL)", "p_cut": "Cutting Fee (TL)", "margin": "Profit (%)",
        "acc_hinge": "Hinges Qty", "acc_hinge_p": "Hinge Price (TL)",
        "acc_rail": "Drawer Rails Qty", "acc_rail_p": "Rail Price (TL)",
        "acc_handle": "Handles Qty", "acc_handle_p": "Handle Price (TL)",
        "btn_calc": "🚀 Calculate & Generate Invoice",
        "inv_title": "🧾 Customer Invoice:", "dl_btn": "⬇️ Download Image",
        "sheets_title": "📐 Cutting Layouts:",
        "pay_title": "🔒 Free Trial Ended",
        "pay_desc": "Please upgrade to Pro to continue",
        "pay_btn": "🔓 Activate", "pay_ph": "Activation code..."
    }
}

# ============================ خوارزمية التعشيش ============================
SORT_KEYS = [
    lambda p: (-p["l"] * p["w"], -max(p["l"], p["w"])),
    lambda p: (-max(p["l"], p["w"]), -p["l"] * p["w"]),
    lambda p: (-p["l"] * p["w"], -min(p["l"], p["w"])),
    lambda p: (-max(p["l"], p["w"]), -min(p["l"], p["w"])),
]

class MaxRectsBin:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.free = [(0, 0, w, h)]
        self.items = []

    def find(self, pw, ph, strat, rotate):
        best = None
        for fx, fy, fw, fh in self.free:
            opts = [(pw, ph, False)]
            if rotate and pw != ph:
                opts.append((ph, pw, True))
            for w, h, rot in opts:
                if w <= fw and h <= fh:
                    dw, dh = fw - w, fh - h
                    if strat == 0: sc = (min(dw, dh), max(dw, dh))
                    elif strat == 1: sc = (max(dw, dh), min(dw, dh))
                    elif strat == 2: sc = (fw * fh - w * h, min(dw, dh))
                    else: sc = (fy + h, fx)
                    if best is None or sc < best[0]:
                        best = (sc, fx, fy, w, h, rot)
        return best

    def place(self, piece, x, y, w, h, rot):
        nf = []
        for fx, fy, fw, fh in self.free:
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy:
                nf.append((fx, fy, fw, fh))
                continue
            if x > fx: nf.append((fx, fy, x - fx, fh))
            if x + w < fx + fw: nf.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy: nf.append((fx, fy, fw, y - fy))
            if y + h < fy + fh: nf.append((fx, y + h, fw, fy + fh - y - h))
        pruned = [a for i, a in enumerate(nf) if not any(j != i and a[0] >= b[0] and a[1] >= b[1] and a[0]+a[2] <= b[0]+b[2] and a[1]+a[3] <= b[1]+b[3] for j, b in enumerate(nf))]
        self.free = pruned
        self.items.append((piece, x, y, w, h, rot))

def best_layout(pieces, sw, sh, kerf, rotate):
    results = []
    for s in range(4):
        try:
            order = sorted(pieces, key=SORT_KEYS[s])
            bins = []
            for p in order:
                pw, ph = p["l"] + kerf, p["w"] + kerf
                best = None
                for b in bins:
                    r = b.find(pw, ph, s, rotate)
                    if r and (best is None or r[0] < best[1][0]): best = (b, r)
                if best is None:
                    b = MaxRectsBin(sw + kerf, sh + kerf)
                    r = b.find(pw, ph, s, rotate)
                    if not r: raise ValueError("القطعة أكبر من اللوح")
                    bins.append(b)
                    best = (b, r)
                b, r = best
                _, x, y, w, h, rot = r
                b.place(p, x, y, w, h, rot)
            max_free = max((fw * fh for b in bins for _, _, fw, fh in b.free), default=0)
            results.append(((len(bins), -max_free), s, bins))
        except Exception:
            continue
    if not results: raise ValueError("تأكد أن جميع المقاسات أصغر من مقاس اللوح")
    results.sort(key=lambda r: r[0])
    return results[0][1], results[0][2]

# ============================ تحليل الحواف والصور ============================
def parse_edges(tok):
    tok = tok.strip().lower()
    if tok.isdigit():
        return {0: (0, 0), 1: (1, 0), 2: (2, 0), 3: (2, 1), 4: (2, 2)}.get(int(tok), (0, 0))
    le = we = 0
    for letter, num in re.findall(r"([lwطع])(\d?)", tok):
        c = int(num) if num else 1
        if letter in ("l", "ط"): le += c
        else: we += c
    return min(le, 2), min(we, 2)

def ocr_image_ai(img_bytes):
    if not OPENROUTER_API_KEY:
        raise ValueError("مفتاح OPENROUTER_API_KEY غير موجود في إعدادات السيرفر")
    if not requests:
        raise ValueError("مكتبة requests غير مثبتة")

    try:
        im = Image.open(io.BytesIO(img_bytes))
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((1600, 1600))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=88)
        jpeg_bytes = buf.getvalue()
    except Exception as e:
        raise ValueError(f"تعذر قراءة ملف الصورة: {e}")

    b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://abu-alqais.onrender.com",
        "X-Title": "Abu Al-Qais Woodwork"
    }

    # قائمة نماذج مجانية تدعم قراءة الصور مع التبديل التلقائي عند الضغط
    free_models = [
        "google/gemma-3-27b-it:free",
        "qwen/qwen2.5-vl-32b-instruct:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "openrouter/free"
    ]

    last_err = ""
    for model in free_models:
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Read this handwritten or printed wood cutting list carefully. Extract dimensions as: Length Width Qty Edges (e.g., 800 600 4 2). If edges are not specified, use 0. Output ONLY the numeric lines, nothing else."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    }
                ]
            }]
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=35)
            if res.status_code == 200:
                data = res.json()
                text = data["choices"][0]["message"]["content"].strip()
                if text:
                    return text
            last_err = f"({res.status_code}): {res.text[:150]}"
        except Exception as e:
            last_err = str(e)

    raise ValueError(f"تعذر القراءة من OpenRouter {last_err}")

# ============================ الرسم والفواتير ============================
@lru_cache(maxsize=16)
def get_font(size):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf"):
        try: return ImageFont.truetype(name, size)
        except Exception: continue
    return ImageFont.load_default()

def to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def render_sheet_b64(b, idx, total, sw, sh, kerf):
    scale = min(1000.0 / sw, 750.0 / sh)
    margin, header = 30, 55
    sheet_w, sheet_h = int(sw * scale), int(sh * scale)
    img = Image.new("RGB", (sheet_w + margin * 2, sheet_h + header + 30), (255, 255, 255))
    d = ImageDraw.Draw(img)
    used = sum(p["l"] * p["w"] for p, *_ in b.items)
    waste = (1 - used / float(sw * sh)) * 100
    d.text((margin, 15), f"Sheet {idx}/{total} | {sw}x{sh} mm | Waste {waste:.1f}%", font=get_font(18), fill=(20, 20, 20))
    ox, oy = margin, header
    d.rectangle([ox, oy, ox + sheet_w, oy + sheet_h], fill=(235, 235, 235), outline=(0, 0, 0), width=2)
    for p, x, y, w, h, rot in b.items:
        aw, ah = w - kerf, h - kerf
        x0, y0 = ox + x * scale, oy + y * scale
        x1, y1 = x0 + aw * scale, y0 + ah * scale
        r, g, bl = colorsys.hsv_to_rgb((p["gi"] * 0.618033) % 1.0, 0.35, 0.96)
        d.rectangle([x0, y0, x1, y1], fill=(int(r*255), int(g*255), int(bl*255)), outline=(40, 40, 40), width=1)
        nh, nv = (p["we"], p["le"]) if rot else (p["le"], p["we"])
        if nh >= 1: d.rectangle([x0, y0, x1, y0 + 3], fill=(220, 20, 60))
        if nh >= 2: d.rectangle([x0, y1 - 3, x1, y1], fill=(220, 20, 60))
        if nv >= 1: d.rectangle([x0, y0, x0 + 3, y1], fill=(220, 20, 60))
        if nv >= 2: d.rectangle([x1 - 3, y0, x1, y1], fill=(220, 20, 60))
        if (x1 - x0) > 45 and (y1 - y0) > 25:
            d.text((x0 + 5, y0 + 5), f"#{p['gi']} ({aw}x{ah})", font=get_font(11), fill=(0, 0, 0))
    return to_b64(img), waste

def render_invoice_b64(mat, sw, sh, pieces_cnt, sheets_cnt, waste_pct, pvc_m, acc_cost, final_price, curr):
    W, H = 750, 560
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 100], fill=(30, 58, 138))
    d.text((25, 20), "ABU AL-QAIS WOODWORK", font=get_font(26), fill=(255, 255, 255))
    d.text((25, 58), f"Tel: {WORKSHOP_PHONE}", font=get_font(16), fill=(219, 234, 254))
    d.text((W - 180, 35), datetime.now().strftime("%Y-%m-%d"), font=get_font(18), fill=(255, 255, 255))
    y = 125
    rows = [
        ("Material:", mat),
        ("Sheet Size:", f"{sw} x {sh} mm"),
        ("Total Pieces:", f"{pieces_cnt}"),
        ("Sheets Needed:", f"{sheets_cnt} (Waste: {waste_pct:.1f}%)"),
        ("PVC Edge Banding:", f"{pvc_m:.1f} m"),
        ("Hardware / Aksesuar:", f"{acc_cost:.1f} {curr}"),
    ]
    for label, val in rows:
        d.text((35, y), label, font=get_font(18), fill=(55, 65, 81))
        d.text((430, y), str(val), font=get_font(18), fill=(17, 24, 39))
        d.line([35, y + 30, W - 35, y + 30], fill=(229, 231, 235), width=1)
        y += 46
    d.rectangle([35, y + 12, W - 35, y + 76], fill=(243, 244, 246), outline=(30, 58, 138), width=2)
    d.text((55, y + 32), "TOTAL PRICE:", font=get_font(22), fill=(30, 58, 138))
    d.text((430, y + 30), f"{final_price:.1f} {curr}", font=get_font(26), fill=(220, 38, 38))
    return to_b64(img)

# ============================ واجهة التطبيق الاحترافية ============================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}" dir="{{ t['dir'] }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t['title'] }}</title>
    <style>
        body { font-family: Tahoma, Arial, sans-serif; background: #eef2f6; margin: 0; padding: 12px; color: #1f2937; }
        .container { max-width: 650px; margin: auto; background: #fff; padding: 18px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
        .lang-bar { display: flex; justify-content: flex-end; gap: 6px; margin-bottom: 10px; }
        .lang-bar a { text-decoration: none; padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; background: #e5e7eb; color: #374151; }
        .lang-bar a.active { background: #1e3a8a; color: #fff; }
        .header { background: linear-gradient(135deg, #1e3a8a, #2563eb); color: #fff; padding: 16px; border-radius: 12px; text-align: center; margin-bottom: 16px; }
        .header h2 { margin: 0; font-size: 20px; }
        .header p { margin: 5px 0 0; font-size: 13px; color: #dbeafe; }
        .tabs { display: flex; gap: 6px; margin-bottom: 15px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }
        .tab-btn { flex: 1; padding: 10px 5px; border: none; border-radius: 8px; background: #f3f4f6; font-weight: bold; font-size: 13px; cursor: pointer; color: #4b5563; }
        .tab-btn.active { background: #1e3a8a; color: #fff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        label { display: block; font-weight: bold; margin: 10px 0 4px; font-size: 13px; color: #374151; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; box-sizing: border-box; font-size: 14px; background: #f9fafb; }
        .row { display: flex; gap: 10px; }
        .row div { flex: 1; }
        .ocr-btns { display: flex; gap: 10px; margin-top: 6px; }
        .ocr-btn { flex: 1; padding: 12px 8px; background: #f1f5f9; border: 2px dashed #94a3b8; border-radius: 8px; text-align: center; cursor: pointer; font-weight: bold; color: #1e293b; font-size: 13px; margin: 0; }
        .ocr-status { margin-top: 8px; font-size: 13px; font-weight: bold; color: #2563eb; display: none; }
        .submit-btn { width: 100%; padding: 14px; background: #10b981; color: #fff; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; margin-top: 16px; cursor: pointer; }
        .dl-btn { display: inline-block; padding: 8px 14px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: bold; margin-top: 6px; }
        .paywall { background: #fef2f2; border: 2px solid #ef4444; padding: 15px; border-radius: 10px; text-align: center; }
        .iban { background: #fff; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 14px; border: 1px dashed #ef4444; margin: 10px 0; direction: ltr; }
        .result-box { margin-top: 20px; border-top: 2px solid #e5e7eb; padding-top: 15px; }
        img { width: 100%; border-radius: 8px; margin-top: 8px; border: 1px solid #d1d5db; }
        .error { background: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 14px; }
    </style>
    <script>
        function openTab(id, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            btn.classList.add('active');
        }

        async function instantOCR(input) {
            if (!input.files || !input.files[0]) return;
            const status = document.getElementById('ocr_status');
            const box = document.getElementById('pieces_box');
            status.style.display = 'block';
            status.style.color = '#2563eb';
            status.innerText = "{{ t['reading'] }}";

            const fd = new FormData();
            fd.append('order_img', input.files[0]);

            try {
                const res = await fetch('/ocr', { method: 'POST', body: fd });
                const data = await res.json();
                if (data.ok) {
                    box.value = data.text;
                    status.style.color = '#059669';
                    status.innerText = "✅ " + input.files[0].name;
                } else {
                    status.style.color = '#dc2626';
                    status.innerText = "❌ " + data.error;
                }
            } catch (e) {
                status.style.color = '#dc2626';
                status.innerText = "❌ خطأ في الاتصال بالسيرفر";
            }
        }
    </script>
</head>
<body>
<div class="container">
    <div class="lang-bar">
        <a href="/?lang=ar" class="{{ 'active' if lang=='ar' else '' }}">🇸🇦 العربية</a>
        <a href="/?lang=tr" class="{{ 'active' if lang=='tr' else '' }}">🇹🇷 Türkçe</a>
        <a href="/?lang=en" class="{{ 'active' if lang=='en' else '' }}">🇬🇧 English</a>
    </div>
    <div class="header">
        <h2>🪵 {{ t['title'] }}</h2>
        <p>{{ t['sub'] }}</p>
    </div>

    {% if paywall %}
    <div class="paywall">
        <h3>{{ t['pay_title'] }}</h3>
        <p>{{ t['pay_desc'] }} ({{ price }})</p>
        <div class="iban">{{ iban }}</div>
        <form method="POST">
            <input type="text" name="unlock_code" placeholder="{{ t['pay_ph'] }}" required>
            <button type="submit" class="submit-btn">{{ t['pay_btn'] }}</button>
        </form>
    </div>
    {% else %}
    <div class="tabs">
        <button type="button" class="tab-btn active" onclick="openTab('tab1', this)">{{ t['tab_cut'] }}</button>
        <button type="button" class="tab-btn" onclick="openTab('tab2', this)">{{ t['tab_set'] }}</button>
        <button type="button" class="tab-btn" onclick="openTab('tab3', this)">{{ t['tab_acc'] }}</button>
    </div>

    <form method="POST" enctype="multipart/form-data">
        <div id="tab1" class="tab-content active">
            <label>{{ t['mat_lbl'] }}</label>
            <select name="material">
                <option value="MDF 18mm">MDF 18mm</option>
                <option value="Suntalam 18mm">Suntalam 18mm</option>
                <option value="MDF 8mm (Arkalik)">MDF 8mm (Arkalık)</option>
                <option value="Kontraplak">Kontraplak</option>
            </select>
            <div class="row">
                <div><label>{{ t['sw_lbl'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="sw" value="{{ sw }}"></div>
                <div><label>{{ t['sh_lbl'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="sh" value="{{ sh }}"></div>
            </div>
            <div class="row">
                <div><label>{{ t['kerf_lbl'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="kerf" value="{{ kerf }}"></div>
                <div>
                    <label>{{ t['rot_lbl'] }}</label>
                    <select name="rotate">
                        <option value="1" selected>{{ t['yes'] }}</option>
                        <option value="0">{{ t['no'] }}</option>
                    </select>
                </div>
            </div>
            <label>{{ t['pieces_lbl'] }}</label>
            <textarea id="pieces_box" name="pieces" rows="5" dir="ltr" lang="en" placeholder="{{ t['pieces_ph'] }}">{{ pieces_text }}</textarea>

            <label>{{ t['ocr_lbl'] }}</label>
            <div class="ocr-btns">
                <label for="cam_upload" class="ocr-btn">{{ t['cam_btn'] }}</label>
                <label for="gal_upload" class="ocr-btn">{{ t['gal_btn'] }}</label>
            </div>
            <input type="file" id="cam_upload" accept="image/*" capture="environment" style="display:none;" onchange="instantOCR(this)">
            <input type="file" id="gal_upload" accept="image/*" style="display:none;" onchange="instantOCR(this)">
            <div id="ocr_status" class="ocr-status"></div>
        </div>

        <div id="tab2" class="tab-content">
            <div class="row">
                <div>
                    <label>{{ t['curr_lbl'] }}</label>
                    <select name="currency">
                        <option value="TL">TL (₺)</option>
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                    </select>
                </div>
                <div><label>{{ t['margin'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="margin" value="20"></div>
            </div>
            <div class="row">
                <div><label>{{ t['rate_usd'] }}</label><input type="text" inputmode="decimal" dir="ltr" lang="en" name="rate_usd" value="35.0"></div>
                <div><label>{{ t['rate_eur'] }}</label><input type="text" inputmode="decimal" dir="ltr" lang="en" name="rate_eur" value="38.0"></div>
            </div>
            <div class="row">
                <div><label>{{ t['p_sheet'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="p_sheet" value="650"></div>
                <div><label>{{ t['p_pvc'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="p_pvc" value="15"></div>
            </div>
            <label>{{ t['p_cut'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="p_cut" value="100">
        </div>

        <div id="tab3" class="tab-content">
            <div class="row">
                <div><label>{{ t['acc_hinge'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="h_qty" value="0"></div>
                <div><label>{{ t['acc_hinge_p'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="h_price" value="25"></div>
            </div>
            <div class="row">
                <div><label>{{ t['acc_rail'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="r_qty" value="0"></div>
                <div><label>{{ t['acc_rail_p'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="r_price" value="120"></div>
            </div>
            <div class="row">
                <div><label>{{ t['acc_handle'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="k_qty" value="0"></div>
                <div><label>{{ t['acc_handle_p'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="k_price" value="40"></div>
            </div>
        </div>

        <button type="submit" class="submit-btn">{{ t['btn_calc'] }}</button>
    </form>
    {% endif %}

    {% if error %}<div class="error">❌ {{ error }}</div>{% endif %}

    {% if invoice %}
    <div class="result-box">
        <h3>{{ t['inv_title'] }}</h3>
        <img src="data:image/png;base64,{{ invoice }}">
        <a href="data:image/png;base64,{{ invoice }}" download="invoice.png" class="dl-btn">{{ t['dl_btn'] }}</a>

        <h3>{{ t['sheets_title'] }} ({{ sheets_cnt }})</h3>
        {% for s in sheets %}
        <img src="data:image/png;base64,{{ s }}">
        <a href="data:image/png;base64,{{ s }}" download="sheet_{{ loop.index }}.png" class="dl-btn">{{ t['dl_btn'] }} #{{ loop.index }}</a>
        {% endfor %}
    </div>
    {% endif %}
</div>
</body>
</html>
"""

@app.route("/ocr", methods=["POST"])
def ocr_endpoint():
    try:
        img_file = request.files.get("order_img")
        if not img_file or not img_file.filename:
            return jsonify({"ok": False, "error": "لم يتم اختيار صورة"})
        text = ocr_image_ai(img_file.read())
        return jsonify({"ok": True, "text": text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/", methods=["GET", "POST"])
def home():
    lang = request.args.get("lang") or request.cookies.get("lang") or "ar"
    if lang not in TR: lang = "ar"
    is_pro = request.cookies.get("is_pro") == "1"
    trial_used = request.cookies.get("trial_used") == "1"

    ctx = {
        "lang": lang, "t": TR[lang], "iban": IBAN_INFO, "price": PRO_PRICE,
        "sw": 2800, "sh": 2100, "kerf": 4, "pieces_text": "",
        "paywall": False, "error": None, "invoice": None, "sheets": []
    }

    if request.method == "POST":
        code = request.form.get("unlock_code", "").strip()
        if code:
            if code == ADMIN_UNLOCK_CODE:
                resp = make_response(render_template_string(HTML_TEMPLATE, **ctx))
                resp.set_cookie("is_pro", "1", max_age=30*86400)
                return resp
            ctx["paywall"], ctx["error"] = True, "كود التفعيل غير صحيح!"
            return render_template_string(HTML_TEMPLATE, **ctx)

        if trial_used and not is_pro:
            ctx["paywall"] = True
            return render_template_string(HTML_TEMPLATE, **ctx)

        try:
            mat = request.form.get("material", "MDF 18mm")
            sw = int(request.form.get("sw", 2800))
            sh = int(request.form.get("sh", 2100))
            kerf = int(request.form.get("kerf", 4))
            rotate = request.form.get("rotate", "1") == "1"
            pieces_text = request.form.get("pieces", "").strip()

            ctx.update({"sw": sw, "sh": sh, "kerf": kerf, "pieces_text": pieces_text})

            groups = []
            for line in pieces_text.splitlines():
                tokens = [t for t in re.split(r"[\s,;*×x:=]+", line.strip()) if t]
                if len(tokens) >= 2:
                    l, w = int(float(tokens[0])), int(float(tokens[1]))
                    qty = int(tokens[2]) if len(tokens) > 2 and tokens[2].isdigit() else 1
                    le, we = parse_edges(tokens[3]) if len(tokens) > 3 else (0, 0)
                    groups.append({"l": l, "w": w, "qty": qty, "le": le, "we": we, "gi": len(groups) + 1})

            if not groups:
                raise ValueError("أدخل مقاساً واحداً على الأقل")

            pieces = [dict(g) for g in groups for _ in range(g["qty"])]
            _, bins = best_layout(pieces, sw, sh, kerf, rotate)
            total_sheets = len(bins)
            waste_pct = (1 - sum(p["l"] * p["w"] for p in pieces) / float(total_sheets * sw * sh)) * 100
            pvc_m = sum(p["le"] * p["l"] + p["we"] * p["w"] for p in pieces) / 1000.0

            p_sheet = float(request.form.get("p_sheet", 650))
            p_pvc = float(request.form.get("p_pvc", 15))
            p_cut = float(request.form.get("p_cut", 100))
            margin = float(request.form.get("margin", 20))
            acc_tl = (
                int(request.form.get("h_qty", 0)) * float(request.form.get("h_price", 0)) +
                int(request.form.get("r_qty", 0)) * float(request.form.get("r_price", 0)) +
                int(request.form.get("k_qty", 0)) * float(request.form.get("k_price", 0))
            )
            total_tl = ((total_sheets * (p_sheet + p_cut)) + (pvc_m * p_pvc) + acc_tl) * (1 + margin / 100.0)

            curr = request.form.get("currency", "TL")
            if curr == "USD":
                rate = float(request.form.get("rate_usd", 35.0))
                final_price, acc_disp = total_tl / rate, acc_tl / rate
            elif curr == "EUR":
                rate = float(request.form.get("rate_eur", 38.0))
                final_price, acc_disp = total_tl / rate, acc_tl / rate
            else:
                final_price, acc_disp = total_tl, acc_tl

            ctx["invoice"] = render_invoice_b64(mat, sw, sh, len(pieces), total_sheets, waste_pct, pvc_m, acc_disp, final_price, curr)
            ctx["sheets_cnt"] = total_sheets
            ctx["sheets"] = [render_sheet_b64(b, i + 1, total_sheets, sw, sh, kerf)[0] for i, b in enumerate(bins)]

            resp = make_response(render_template_string(HTML_TEMPLATE, **ctx))
            resp.set_cookie("trial_used", "1", max_age=365*86400)
            resp.set_cookie("lang", lang, max_age=365*86400)
            return resp
        except Exception as e:
            ctx["error"] = str(e)

    elif trial_used and not is_pro:
        ctx["paywall"] = True

    resp = make_response(render_template_string(HTML_TEMPLATE, **ctx))
    resp.set_cookie("lang", lang, max_age=365*86400)
    return resp


# ============================ بوت تليجرام (Webhook) ============================
BOT_SESSIONS = {}

def get_session(chat_id):
    cid = str(chat_id)
    if cid not in BOT_SESSIONS:
        BOT_SESSIONS[cid] = {
            "sw": 2800,
            "sh": 2100,
            "kerf": 4,
            "mat": "MDF 18mm",
            "curr": "TL",
            "rot": True,
            "p_sheet": 650,
            "p_pvc": 15,
            "p_cut": 100,
            "margin": 20
        }
    return BOT_SESSIONS[cid]

def tg_api(method, data=None, files=None):
    if not (TELEGRAM_BOT_TOKEN and requests):
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        return requests.post(url, data=data, files=files, timeout=30).json()
    except Exception:
        return None

def tg_send_msg(chat_id, text, reply_markup=None):
    import json
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    tg_api("sendMessage", data=payload)

def tg_edit_msg(chat_id, message_id, text, reply_markup=None):
    import json
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    tg_api("editMessageText", data=payload)

def tg_send_b64_photo(chat_id, b64_str, caption=""):
    img_bytes = base64.b64decode(b64_str)
    tg_api("sendPhoto", data={"chat_id": chat_id, "caption": caption}, files={"photo": ("image.png", img_bytes, "image/png")})

def main_menu_markup(s, host_url=""):
    rot_txt = "✅ مسموح" if s["rot"] else "❌ ممنوع"
    kb = [
        [{"text": f"📐 اللوح: {s['sw']}×{s['sh']}", "callback_data": "menu_sheet"},
         {"text": f"🪵 النوع: {s['mat']}", "callback_data": "menu_mat"}],
        [{"text": f"💰 العملة: {s['curr']}", "callback_data": "toggle_curr"},
         {"text": f"🔄 التدوير: {rot_txt}", "callback_data": "toggle_rot"}],
    ]
    if host_url:
        kb.append([{"text": "🌐 فتح الموقع الكامل", "url": host_url}])
    return {"inline_keyboard": kb}

def github_upload_file(filename, content_bytes, commit_msg="Update via Telegram Bot"):
    if not (GITHUB_TOKEN and GITHUB_REPO and requests):
        raise ValueError("يرجى إضافة GITHUB_TOKEN و GITHUB_REPO في إعدادات Render أولاً.")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    sha = None
    get_res = requests.get(url, headers=headers, timeout=20)
    if get_res.status_code == 200:
        sha = get_res.json().get("sha")
    elif get_res.status_code not in (404,):
        raise ValueError(f"خطأ في فحص GitHub ({get_res.status_code}): {get_res.text[:150]}")

    payload = {
        "message": commit_msg,
        "content": base64.b64encode(content_bytes).decode("utf-8")
    }
    if sha:
        payload["sha"] = sha

    put_res = requests.put(url, headers=headers, json=payload, timeout=30)
    if put_res.status_code not in (200, 201):
        raise ValueError(f"فشل الرفع إلى GitHub ({put_res.status_code}): {put_res.text[:150]}")
    return True

def tg_download_file(file_id):
    info = tg_api("getFile", data={"file_id": file_id})
    if not info or not info.get("ok"):
        return None
    file_path = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    res = requests.get(url, timeout=30)
    return res.content if res.status_code == 200 else None

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    if not TELEGRAM_BOT_TOKEN:
        return "❌ يرجى إضافة TELEGRAM_BOT_TOKEN في إعدادات Environment Variables على Render أولاً.", 400
    webhook_url = f"https://{request.host}/telegram_webhook"
    res = tg_api("setWebhook", data={"url": webhook_url})
    return jsonify({"webhook_url": webhook_url, "telegram_response": res})

@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    host_url = f"https://{request.host}"

    # 1. معالجة ضغطات الأزرار التفاعلية
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb["id"]
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        data = cb.get("data", "")
        s = get_session(chat_id)

        tg_api("answerCallbackQuery", data={"callback_query_id": cb_id})

        if data == "menu_sheet":
            kb = {"inline_keyboard": [
                [{"text": "2800 × 2100", "callback_data": "set_sheet_2800_2100"},
                 {"text": "2440 × 1220", "callback_data": "set_sheet_2440_1220"}],
                [{"text": "3660 × 1830", "callback_data": "set_sheet_3660_1830"},
                 {"text": "🔙 رجوع", "callback_data": "back_main"}]
            ]}
            tg_edit_msg(chat_id, msg_id, "📐 اختر مقاس اللوح القياسي:", kb)
        elif data.startswith("set_sheet_"):
            _, _, sw_s, sh_s = data.split("_")
            s["sw"], s["sh"] = int(sw_s), int(sh_s)
            tg_edit_msg(chat_id, msg_id, "⚙️ إعدادات التقطيع الحالية:", main_menu_markup(s, host_url))
        elif data == "menu_mat":
            kb = {"inline_keyboard": [
                [{"text": "MDF 18mm", "callback_data": "set_mat_MDF 18mm"},
                 {"text": "Suntalam 18mm", "callback_data": "set_mat_Suntalam 18mm"}],
                [{"text": "MDF 8mm", "callback_data": "set_mat_MDF 8mm"},
                 {"text": "Kontraplak", "callback_data": "set_mat_Kontraplak"}],
                [{"text": "🔙 رجوع", "callback_data": "back_main"}]
            ]}
            tg_edit_msg(chat_id, msg_id, "🪵 اختر نوع الخشب:", kb)
        elif data.startswith("set_mat_"):
            s["mat"] = data.replace("set_mat_", "")
            tg_edit_msg(chat_id, msg_id, "⚙️ إعدادات التقطيع الحالية:", main_menu_markup(s, host_url))
        elif data == "toggle_curr":
            order = ["TL", "USD", "EUR"]
            s["curr"] = order[(order.index(s["curr"]) + 1) % len(order)]
            tg_edit_msg(chat_id, msg_id, "⚙️ إعدادات التقطيع الحالية:", main_menu_markup(s, host_url))
        elif data == "toggle_rot":
            s["rot"] = not s["rot"]
            tg_edit_msg(chat_id, msg_id, "⚙️ إعدادات التقطيع الحالية:", main_menu_markup(s, host_url))
        elif data == "back_main":
            tg_edit_msg(chat_id, msg_id, "⚙️ إعدادات التقطيع الحالية:", main_menu_markup(s, host_url))
        return "OK", 200

    msg = update.get("message")
    if not msg:
        return "OK", 200

    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    s = get_session(chat_id)

    if text in ("/start", "/menu"):
        welcome = (
            "أهلاً بك في بوت أبو القيس لتقطيع الأخشاب 🪵\n\n"
            "• أرسل **صورة الطلبية** لقراءتها بالذكاء الاصطناعي.\n"
            "• أو اكتب المقاسات مباشرة (مثال: `800 600 4 2`).\n"
            "• استخدم الأزرار بالأسفل لتغيير الإعدادات:"
        )
        tg_send_msg(chat_id, welcome, main_menu_markup(s, host_url))
        return "OK", 200

    try:
        if "document" in msg:
            if ADMIN_CHAT_ID and str(chat_id) != str(ADMIN_CHAT_ID).strip():
                tg_send_msg(chat_id, "⛔ عذراً، ميزة تحديث الملفات مخصصة لصاحب البوت فقط.")
                return "OK", 200
            doc = msg["document"]
            fname = doc.get("file_name", "app.py")
            tg_send_msg(chat_id, f"⏳ جاري تحميل الملف `{fname}` ورفعه إلى GitHub...")
            file_bytes = tg_download_file(doc["file_id"])
            if not file_bytes:
                raise ValueError("تعذر تحميل الملف من تليجرام")
            github_upload_file(fname, file_bytes, f"Update {fname} via Telegram Bot")
            tg_send_msg(chat_id, f"✅ تم رفع `{fname}` إلى GitHub بنجاح!\nسيقوم Render بتحديث السيرفر تلقائياً خلال دقيقة واحدة.")
            return "OK", 200

        pieces_text = ""
        if "photo" in msg:
            tg_send_msg(chat_id, "⏳ جاري قراءة المقاسات من الصورة...")
            file_id = msg["photo"][-1]["file_id"]
            img_bytes = tg_download_file(file_id)
            if not img_bytes:
                raise ValueError("تعذر تحميل الصورة من تليجرام")
            pieces_text = ocr_image_ai(img_bytes)
            tg_send_msg(chat_id, f"📋 المقاسات المستخرجة:\n{pieces_text}")
        elif text:
            pieces_text = text

        if not pieces_text:
            return "OK", 200

        groups = []
        for line in pieces_text.splitlines():
            tokens = [t for t in re.split(r"[\s,;*×x:=]+", line.strip()) if t]
            if len(tokens) >= 2:
                l, w = int(float(tokens[0])), int(float(tokens[1]))
                qty = int(tokens[2]) if len(tokens) > 2 and tokens[2].isdigit() else 1
                le, we = parse_edges(tokens[3]) if len(tokens) > 3 else (0, 0)
                groups.append({"l": l, "w": w, "qty": qty, "le": le, "we": we, "gi": len(groups) + 1})

        if not groups:
            raise ValueError("لم أتمكن من فهم المقاسات. أرسلها بشكل: الطول العرض العدد الحواف")

        sw, sh, kerf = s["sw"], s["sh"], s["kerf"]
        pieces = [dict(g) for g in groups for _ in range(g["qty"])]
        _, bins = best_layout(pieces, sw, sh, kerf, s["rot"])
        total_sheets = len(bins)
        waste_pct = (1 - sum(p["l"] * p["w"] for p in pieces) / float(total_sheets * sw * sh)) * 100
        pvc_m = sum(p["le"] * p["l"] + p["we"] * p["w"] for p in pieces) / 1000.0
        total_tl = ((total_sheets * (s["p_sheet"] + s["p_cut"])) + (pvc_m * s["p_pvc"])) * (1 + s["margin"] / 100.0)

        curr = s["curr"]
        final_price = total_tl / 35.0 if curr == "USD" else (total_tl / 38.0 if curr == "EUR" else total_tl)

        inv_b64 = render_invoice_b64(s["mat"], sw, sh, len(pieces), total_sheets, waste_pct, pvc_m, 0, final_price, curr)
        tg_send_b64_photo(chat_id, inv_b64, caption=f"🧾 الفاتورة ({s['mat']}) | الألواح: {total_sheets} | الهدر: {waste_pct:.1f}%")

        for i, b in enumerate(bins):
            s_b64, w_pct = render_sheet_b64(b, i + 1, total_sheets, sw, sh, kerf)
            tg_send_b64_photo(chat_id, s_b64, caption=f"📐 لوح {i + 1}/{total_sheets} (هدر {w_pct:.1f}%)")

    except Exception as e:
        tg_send_msg(chat_id, f"❌ خطأ: {e}")

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
