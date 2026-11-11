# -*- coding: utf-8 -*-
import os
import time
import threading
import json
import random
import string
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
TIERS = {
    "pro": {"name": "Pro (برو)", "price": "250 TL / شهرياً", "desc": "{{ t['tier_pro_d'] }}"},
    "promax": {"name": "Pro Max (برو ماكس)", "price": "450 TL / شهرياً", "desc": "{{ t['tier_max_d'] }}"},
    "ultra": {"name": "Ultra (أولترا)", "price": "750 TL / شهرياً", "desc": "{{ t['tier_ult_d'] }}"}
}
ADMIN_UNLOCK_CODE = "QAIS2026"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# ============================ كتالوج أنواع الخشب والألواح ============================
WOOD_CATALOG = [
    ("MDF 18mm (ألواح مضغوطة قياسية)", "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=600&q=80"),
    ("Suntalam / Chipboard (خشب حبيبي ملبس)", "https://images.unsplash.com/photo-1610505466122-b1d9482901ef?w=600&q=80"),
    ("Kontraplak / Plywood (خشب معاكس)", "https://images.unsplash.com/photo-1541123437800-1bb1317badc2?w=600&q=80"),
    ("OSB (ألواح رقائق الخشب الموجهة)", "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&q=80"),
    ("Masif / Solid Wood (خشب طبيعي صلب)", "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=600&q=80"),
]


# ============================ إدارة الأكواد والاشتراكات (GitHub) ============================
_STORE_CACHE = None

def normalize_digits(text):
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    return text.translate(trans)

def load_store(force=False):
    global _STORE_CACHE
    if _STORE_CACHE is not None and not force:
        return _STORE_CACHE
    default_store = {"codes": {}, "tg_users": {}, "banned": [], "offcuts": [], "ledger": []}
    if not (GITHUB_TOKEN and GITHUB_REPO and requests):
        _STORE_CACHE = default_store
        return _STORE_CACHE
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/codes.json"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            content = base64.b64decode(res.json()["content"]).decode("utf-8")
            data = json.loads(content)
            if "codes" in data and "tg_users" in data:
                data.setdefault("banned", [])
                data.setdefault("offcuts", [])
                data.setdefault("ledger", [])
                _STORE_CACHE = data
                return _STORE_CACHE
    except Exception:
        pass
    _STORE_CACHE = default_store
    return _STORE_CACHE

def save_store(store):
    global _STORE_CACHE
    _STORE_CACHE = store
    if not (GITHUB_TOKEN and GITHUB_REPO and requests):
        return False
    try:
        raw = json.dumps(store, ensure_ascii=False, indent=2).encode("utf-8")
        github_upload_file("codes.json", raw, "Update codes.json")
        return True
    except Exception:
        return False

def generate_single_code(tier="pro"):
    tier = tier.lower().strip()
    if tier not in TIERS:
        tier = "pro"
    store = load_store(force=True)
    part1 = "".join(random.choices(string.digits, k=4))
    part2 = "".join(random.choices(string.ascii_uppercase, k=2))
    prefix = {"pro": "PRO", "promax": "MAX", "ultra": "ULT"}[tier]
    new_code = f"QAIS-{prefix}-{part1}-{part2}"
    store["codes"][new_code] = {"used": False, "tier": tier, "created_at": int(time.time()), "used_at": None, "used_by": None}
    save_store(store)
    return new_code

def redeem_single_code(code_str, user_id="web"):
    code_str = code_str.strip().upper()
    if code_str == ADMIN_UNLOCK_CODE:
        return True, "تم التفعيل (كود الإدارة - Ultra)!", "ultra"
    store = load_store(force=True)
    c_info = store["codes"].get(code_str)
    if not c_info:
        return False, "كود التفعيل غير صحيح!", "pro"
    if c_info.get("used"):
        return False, "هذا الكود تم استخدامه مسبقاً!", "pro"
    tier = c_info.get("tier", "pro")
    c_info["used"] = True
    c_info["used_at"] = int(time.time())
    c_info["used_by"] = str(user_id)
    if str(user_id) != "web":
        u = store["tg_users"].setdefault(str(user_id), {"trial_used": True, "pro_until": 0, "tier": tier})
        u["pro_until"] = int(time.time()) + 30 * 86400
        u["tier"] = tier
    save_store(store)
    t_name = TIERS.get(tier, TIERS["pro"])["name"]
    return True, f"تم تفعيل باقة {t_name} بنجاح لمدة 30 يوماً!", tier

def build_cut_summary(groups):
    lines = ["📋 ملخص القص لعامل المنشار:"]
    for g in groups:
        edge_txt = f"طول:{g['le']} عرض:{g['we']}" if (g["le"] or g["we"]) else "بدون شريط"
        lines.append(f"#{g['gi']} | {g['l']} × {g['w']} مم | العدد: {g['qty']} | {edge_txt}")
    return "\n".join(lines)


# ============================ قاموس اللغات ============================
TR = {
    "ar": {
        "dir": "rtl", "title": "أبو القيس - نظام النجارة المتكامل",
        "sub": "نظام تقطيع الأخشاب والتسعير | هاتف: " + WORKSHOP_PHONE,
        "tab_cut": "📐 التقطيع والطلب", "tab_set": "⚙️ الأسعار والعملات", "tab_acc": "🔩 الإكسسوارات", "tab_tpl": "🧊 قوالب 3D", "tab_led": "📒 الدفتر والمخزون", "tab_kar": "🎨 قارتيلا 75+75",
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
        "pay_btn": "🔓 تفعيل الاشتراك", "pay_ph": "أدخل كود التفعيل...",
        "tip_grain": "{{ t['tip_grain']|safe }}",
        "use_offcuts": "{{ t['use_offcuts'] }}",
        "cust_lbl": "{{ t['cust_lbl'] }}",
        "cust_ph": "مثال: أحمد محمد",
        "dep_lbl": "{{ t['dep_lbl'] }}",
        "wa_btn": "{{ t['wa_btn'] }}",
        "print_btn": "{{ t['print_btn'] }}",
        "saw_btn": "{{ t['saw_btn'] }}",
        "csv_btn": "{{ t['csv_btn'] }}",
        "pdf_btn": "{{ t['pdf_btn'] }}",
        "etiket_btn": "{{ t['etiket_btn'] }}",
        "tier_pro": "{{ t['tier_pro'] }}",
        "tier_pro_d": "تقطيع الألواح + الفاتورة + قراءة الصور AI + القوالب الجاهزة",
        "tier_max": "{{ t['tier_max'] }}",
        "tier_max_d": "كل ميزات Pro + اسم الورشة + دفتر الورشة والمخزون + رابط عامل المنشار + واتساب",
        "tier_ult": "{{ t['tier_ult'] }}",
        "tier_ult_d": "كل ميزات Pro Max + تصدير CNC CSV + قارتيلا 75+75 + PDF + ملصقات Etiket"
    },
    "tr": {
        "dir": "ltr", "title": "Abu Al-Qais - Kesim Optimizasyon",
        "sub": "Ahşap Kesim ve Maliyet Sistemi | Tel: " + WORKSHOP_PHONE,
        "tab_cut": "📐 Kesim & Sipariş", "tab_set": "⚙️ Fiyat & Döviz", "tab_acc": "🔩 Aksesuar", "tab_tpl": "🧊 3D Şablonlar", "tab_led": "📒 Defter & Fire", "tab_kar": "🎨 Kartela 75+75",
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
        "pay_btn": "🔓 Aktifleştir", "pay_ph": "Aktivasyon kodu...",
        "tip_grain": "💡 İpucu: Döndürmeyi engellemek (desen yönü) için satır sonuna <b>G</b>, kalın bant için <b>2mm</b> ekleyin (Örn: <code>800 600 2 4 2mm G</code>)",
        "use_offcuts": "♻️ Yeni plaka açmadan önce kayıtlı fireleri (parçaları) otomatik kullan",
        "cust_lbl": "👤 Müşteri Adı (İsteğe bağlı):",
        "cust_ph": "Örn: Ahmet Yılmaz",
        "dep_lbl": "💵 Alınan Kapora:",
        "wa_btn": "📲 WhatsApp ile Gönder",
        "print_btn": "🏷️ Kesim Etiketlerini Yazdır",
        "saw_btn": "🪚 Kesimci Bağlantısı (Fiyatsız)",
        "csv_btn": "📊 CNC Kesim Makinesi için CSV İndir",
        "pdf_btn": "📄 Faturayı PDF İndir",
        "etiket_btn": "🏷️ Etiket Sayfası (Etiket)",
        "tier_pro": "🔹 Pro Paket — 250 TL / Aylık",
        "tier_pro_d": "Plaka Kesim + Fatura + Yapay Zeka Fotoğraf Okuma + Hazır Şablonlar",
        "tier_max": "🔸 Pro Max Paket — 450 TL / Aylık",
        "tier_max_d": "Tüm Pro özellikleri + Atölye Adı + Defter & Fire + Kesimci Linki + WhatsApp",
        "tier_ult": "👑 Ultra Paket — 750 TL / Aylık",
        "tier_ult_d": "Tüm Pro Max özellikleri + CNC CSV + 75+75 Kartela + PDF + Etiket"
    },
    "en": {
        "dir": "ltr", "title": "Abu Al-Qais - Woodwork Pro",
        "sub": "Cutting & Costing System | Tel: " + WORKSHOP_PHONE,
        "tab_cut": "📐 Cutting", "tab_set": "⚙️ Prices & Currency", "tab_acc": "🔩 Hardware", "tab_tpl": "🧊 3D Templates", "tab_led": "📒 Ledger & Offcuts", "tab_kar": "🎨 Kartela 75+75",
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
        "pay_btn": "🔓 Activate", "pay_ph": "Activation code...",
        "tip_grain": "💡 Tip: Add <b>G</b> at the end of a line to lock grain direction, and <b>2mm</b> for thick edge banding (e.g. <code>800 600 2 4 2mm G</code>)",
        "use_offcuts": "♻️ Automatically use saved offcuts before opening a new sheet",
        "cust_lbl": "👤 Customer Name (Optional):",
        "cust_ph": "e.g. John Doe",
        "dep_lbl": "💵 Deposit Paid:",
        "wa_btn": "📲 Send via WhatsApp",
        "print_btn": "🏷️ Print Cutting Labels (Etiket)",
        "saw_btn": "🪚 Saw Operator Link (No Prices)",
        "csv_btn": "📊 Export CSV for CNC Machine",
        "pdf_btn": "📄 Download Invoice PDF",
        "etiket_btn": "🏷️ Labels Page (Etiket)",
        "tier_pro": "🔹 Pro Plan — 250 TL / Month",
        "tier_pro_d": "Sheet Cutting + Invoice + AI Photo Reading + 3D Templates",
        "tier_max": "🔸 Pro Max Plan — 450 TL / Month",
        "tier_max_d": "All Pro features + Workshop Name + Ledger & Offcuts + Saw Link + WhatsApp",
        "tier_ult": "👑 Ultra Plan — 750 TL / Month",
        "tier_ult_d": "All Pro Max features + CNC CSV + 75+75 Kartela + PDF + Etiket Labels"
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
                    r = b.find(pw, ph, s, rotate and not p.get('no_rot', False))
                    if r and (best is None or r[0] < best[1][0]): best = (b, r)
                if best is None:
                    b = MaxRectsBin(sw + kerf, sh + kerf)
                    r = b.find(pw, ph, s, rotate and not p.get('no_rot', False))
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

    # جلب أحدث النماذج المجانية التي تدعم الصور تلقائياً من OpenRouter لتجنب خطأ 404
    free_models = []
    try:
        m_res = requests.get("https://openrouter.ai/api/v1/models", timeout=15)
        if m_res.status_code == 200:
            for m in m_res.json().get("data", []):
                mid = m.get("id", "")
                arch = m.get("architecture") or {}
                mods = arch.get("input_modalities") or []
                if mid.endswith(":free") and ("image" in mods or "image" in str(arch.get("modality", "")).lower()):
                    free_models.append(mid)
    except Exception:
        pass

    if not free_models:
        free_models = [
            "google/gemma-3-27b-it:free",
            "qwen/qwen2.5-vl-32b-instruct:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
            "nvidia/nemotron-nano-12b-v2-vl:free",
        ]

    last_err = ""
    for model in free_models[:6]:
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
            last_err = f"({res.status_code}) [{model}]: {res.text[:120]}"
        except Exception as e:
            last_err = f"[{model}]: {e}"

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

def render_invoice_b64(mat, sw, sh, pieces_cnt, sheets_cnt, waste_pct, pvc_m, acc_cost, final_price, curr, ws_name="ABU AL-QAIS WOODWORK", ws_phone=WORKSHOP_PHONE, inv_mode="workshop", cust_name="", deposit=0.0):
    W, H = 750, 610
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 100], fill=(30, 58, 138))
    d.text((25, 20), str(ws_name)[:28], font=get_font(26), fill=(255, 255, 255))
    d.text((25, 58), f"Tel: {ws_phone}", font=get_font(16), fill=(219, 234, 254))
    d.text((W - 180, 35), datetime.now().strftime("%Y-%m-%d"), font=get_font(18), fill=(255, 255, 255))
    y = 125
    rows = [
        ("Customer:", cust_name if cust_name else "-"),
        ("Material:", mat),
        ("Sheet Size:", f"{sw} x {sh} mm"),
        ("Total Pieces:", f"{pieces_cnt}"),
        ("Sheets Needed:", f"{sheets_cnt}" if inv_mode == "customer" else f"{sheets_cnt} (Waste: {waste_pct:.1f}%)"),
        ("PVC Edge Banding:", f"{pvc_m:.1f} m"),
        ("Hardware / Aksesuar:", f"{acc_cost:.1f} {curr}"),
    ]
    for label, val in rows:
        d.text((35, y), label, font=get_font(18), fill=(55, 65, 81))
        d.text((430, y), str(val), font=get_font(18), fill=(17, 24, 39))
        d.line([35, y + 30, W - 35, y + 30], fill=(229, 231, 235), width=1)
        y += 46
    d.rectangle([35, y + 10, W - 35, y + 72], fill=(243, 244, 246), outline=(30, 58, 138), width=2)
    d.text((55, y + 26), "TOTAL:", font=get_font(20), fill=(30, 58, 138))
    rem = max(0.0, final_price - deposit)
    if deposit > 0:
        d.text((220, y + 26), f"{final_price:.1f} | Paid: {deposit:.1f} | Rem: {rem:.1f} {curr}", font=get_font(18), fill=(220, 38, 38))
    else:
        d.text((430, y + 24), f"{final_price:.1f} {curr}", font=get_font(24), fill=(220, 38, 38))
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
        :root {
            --bg-body: #eef2f6;
            --bg-card: #ffffff;
            --text-main: #1f2937;
            --text-lbl: #374151;
            --hdr-bg: linear-gradient(135deg, #1e3a8a, #2563eb);
            --hdr-sub: #dbeafe;
            --inp-bg: #f9fafb;
            --inp-brd: #d1d5db;
            --tab-bg: #f3f4f6;
            --tab-txt: #4b5563;
            --tab-act: #1e3a8a;
            --btn-main: #10b981;
            --ocr-bg: #f1f5f9;
            --ocr-txt: #1e293b;
        }
        body.theme-wood {
            --bg-body: #f5efe6;
            --bg-card: #fffdf9;
            --text-main: #3e2723;
            --text-lbl: #5d4037;
            --hdr-bg: linear-gradient(135deg, #5d4037, #8d6e63);
            --hdr-sub: #efebe9;
            --inp-bg: #faf6f0;
            --inp-brd: #d7ccc8;
            --tab-bg: #efebe9;
            --tab-txt: #5d4037;
            --tab-act: #6d4c41;
            --btn-main: #b45309;
            --ocr-bg: #f5ebe0;
            --ocr-txt: #4e342e;
        }
        body.theme-dark {
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --text-main: #f1f5f9;
            --text-lbl: #cbd5e1;
            --hdr-bg: linear-gradient(135deg, #0f172a, #334155);
            --hdr-sub: #94a3b8;
            --inp-bg: #0f172a;
            --inp-brd: #334155;
            --tab-bg: #334155;
            --tab-txt: #cbd5e1;
            --tab-act: #3b82f6;
            --btn-main: #059669;
            --ocr-bg: #0f172a;
            --ocr-txt: #e2e8f0;
        }
        body { font-family: Tahoma, Arial, sans-serif; background: var(--bg-body); margin: 0; padding: 12px; color: var(--text-main); transition: 0.25s; }
        .container { max-width: 650px; margin: auto; background: var(--bg-card); padding: 18px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
        .lang-bar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 6px; margin-bottom: 10px; }
        .lang-bar a { text-decoration: none; padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; background: #e5e7eb; color: #374151; }
        .lang-bar a.active { background: #1e3a8a; color: #fff; }
        .header { background: var(--hdr-bg); color: #fff; padding: 16px; border-radius: 12px; text-align: center; margin-bottom: 16px; }
        .header h2 { margin: 0; font-size: 20px; }
        .header p { margin: 5px 0 0; font-size: 13px; color: var(--hdr-sub); }
        .tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 15px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }
        .tab-btn { flex: 1 1 30%; min-width: 95px; padding: 9px 6px; border: none; border-radius: 8px; background: var(--tab-bg); font-weight: bold; font-size: 12px; cursor: pointer; color: var(--tab-txt); text-align: center; }
        .tab-btn.active { background: var(--tab-act); color: #fff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        label { display: block; font-weight: bold; margin: 10px 0 4px; font-size: 13px; color: var(--text-lbl); }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid var(--inp-brd); border-radius: 8px; box-sizing: border-box; font-size: 14px; background: var(--inp-bg); color: var(--text-main); }
        .row { display: flex; gap: 10px; }
        .row div { flex: 1; }
        .ocr-btns { display: flex; gap: 10px; margin-top: 6px; }
        .ocr-btn { flex: 1; padding: 12px 8px; background: var(--ocr-bg); border: 2px dashed #94a3b8; border-radius: 8px; text-align: center; cursor: pointer; font-weight: bold; color: var(--ocr-txt); font-size: 13px; margin: 0; }
        .ocr-status { margin-top: 8px; font-size: 13px; font-weight: bold; color: #2563eb; display: none; }
        .submit-btn { width: 100%; padding: 14px; background: var(--btn-main); color: #fff; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; margin-top: 16px; cursor: pointer; }
        .dl-btn { display: inline-block; padding: 8px 14px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: bold; margin-top: 6px; }
        .paywall { background: #fef2f2; border: 2px solid #ef4444; padding: 15px; border-radius: 10px; text-align: center; }
        .iban { background: #fff; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 14px; border: 1px dashed #ef4444; margin: 10px 0; direction: ltr; }
        .result-box { margin-top: 20px; border-top: 2px solid #e5e7eb; padding-top: 15px; }
        img { width: 100%; border-radius: 8px; margin-top: 8px; border: 1px solid #d1d5db; }
        .error { background: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 14px; }
    </style>
    <script>
        
        let angle3D = 35;
        function rot3D(deg) { angle3D += deg; draw3D(); }

        const TPL_PHOTOS = {
            wardrobe2: "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=500&q=80",
            wardrobe3: "https://images.unsplash.com/photo-1558997519-83ea9252edf8?w=500&q=80",
            wardrobe_slide: "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=500&q=80",
            shoe_cab: "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=500&q=80",
            bookcase: "https://images.unsplash.com/photo-1594620302200-9a762244a156?w=500&q=80",
            kit_base: "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=500&q=80",
            kit_wall: "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=500&q=80",
            kit_drawers: "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=500&q=80",
            kit_tall: "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=500&q=80",
            nightstand: "https://images.unsplash.com/photo-1532372320572-cda25653a26d?w=500&q=80",
            chiffonier: "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=500&q=80",
            dresser: "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=500&q=80",
            bed_single: "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=500&q=80",
            bed_double: "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=500&q=80",
            table_dining: "https://images.unsplash.com/photo-1577140917170-285929fb55b7?w=500&q=80",
            table_coffee: "https://images.unsplash.com/photo-1533090481720-856c6e3c1fdc?w=500&q=80",
            desk_office: "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=500&q=80",
            tv_unit: "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=500&q=80",
            chair_simple: "https://images.unsplash.com/photo-1503602642458-232111445657?w=500&q=80",
            bench_storage: "https://images.unsplash.com/photo-1503602642458-232111445657?w=500&q=80",
            storage_box: "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=500&q=80"
        };
        const TPL_DEFAULTS = {
            wardrobe2: [2000, 1000, 600], wardrobe3: [2100, 1500, 600], wardrobe_slide: [2200, 1800, 650],
            shoe_cab: [1100, 800, 350], bookcase: [1800, 800, 320],
            kit_base: [720, 800, 560], kit_wall: [720, 800, 320], kit_drawers: [720, 600, 560], kit_tall: [2100, 600, 580],
            nightstand: [500, 450, 400], chiffonier: [900, 800, 450], dresser: [780, 1100, 450],
            bed_single: [400, 950, 1950], bed_double: [400, 1650, 2050],
            table_dining: [750, 1400, 800], table_coffee: [450, 1000, 600], desk_office: [750, 1200, 600],
            tv_unit: [500, 1600, 400], chair_simple: [850, 450, 450], bench_storage: [450, 1000, 400], storage_box: [450, 800, 400]
        };

        function onTplChange() {
            const k = document.getElementById('tpl_select').value;
            const d = TPL_DEFAULTS[k] || [1000, 800, 500];
            document.getElementById('tpl_h').value = d[0];
            document.getElementById('tpl_w').value = d[1];
            document.getElementById('tpl_d').value = d[2];
            const imgEl = document.getElementById('tpl_preview_img');
            if (imgEl && TPL_PHOTOS[k]) imgEl.src = TPL_PHOTOS[k];
            draw3D();
        }

        function proj3D(x, y, z, rad, cx, cy, sc) {
            const rx = x * Math.cos(rad) - z * Math.sin(rad);
            const rz = x * Math.sin(rad) + z * Math.cos(rad);
            const px = cx + rx * sc;
            const py = cy - y * sc + rz * 0.38 * sc;
            return [px, py];
        }

        function draw3D() {
            const c = document.getElementById('canvas3d');
            if (!c) return;
            const ctx = c.getContext('2d');
            ctx.clearRect(0, 0, c.width, c.height);
            const H = parseFloat(document.getElementById('tpl_h').value) || 1000;
            const W = parseFloat(document.getElementById('tpl_w').value) || 800;
            const D = parseFloat(document.getElementById('tpl_d').value) || 500;
            const maxDim = Math.max(H, W, D, 1);
            const sc = 135 / maxDim;
            const rad = angle3D * Math.PI / 180;
            const cx = c.width / 2, cy = c.height / 2 + (H * sc) * 0.35;

            const pts = [
                [-W/2, 0, -D/2], [W/2, 0, -D/2], [W/2, H, -D/2], [-W/2, H, -D/2],
                [-W/2, 0,  D/2], [W/2, 0,  D/2], [W/2, H,  D/2], [-W/2, H,  D/2]
            ].map(p => proj3D(p[0], p[1], p[2], rad, cx, cy, sc));

            ctx.strokeStyle = '#2563eb';
            ctx.lineWidth = 2;
            const edges = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
            edges.forEach(e => {
                ctx.beginPath();
                ctx.moveTo(pts[e[0]][0], pts[e[0]][1]);
                ctx.lineTo(pts[e[1]][0], pts[e[1]][1]);
                ctx.stroke();
            });

            // Draw front detail (doors/shelves)
            const k = document.getElementById('tpl_select').value;
            ctx.strokeStyle = '#f59e0b';
            ctx.lineWidth = 1.5;
            if (k.includes('wardrobe') || k.includes('kit_base') || k.includes('kit_wall') || k === 'shoe_cab') {
                const m1 = proj3D(0, 0, D/2, rad, cx, cy, sc);
                const m2 = proj3D(0, H, D/2, rad, cx, cy, sc);
                ctx.beginPath(); ctx.moveTo(m1[0], m1[1]); ctx.lineTo(m2[0], m2[1]); ctx.stroke();
            } else if (k.includes('drawer') || k === 'chiffonier' || k === 'nightstand') {
                const rows = k === 'nightstand' ? 2 : 3;
                for (let i = 1; i < rows; i++) {
                    const y = (H / rows) * i;
                    const p1 = proj3D(-W/2, y, D/2, rad, cx, cy, sc);
                    const p2 = proj3D(W/2, y, D/2, rad, cx, cy, sc);
                    ctx.beginPath(); ctx.moveTo(p1[0], p1[1]); ctx.lineTo(p2[0], p2[1]); ctx.stroke();
                }
            }
            ctx.fillStyle = '#64748b';
            ctx.font = 'bold 12px Tahoma';
            ctx.fillText(`${W} × ${H} × ${D} mm`, 10, 18);
        }

        function applyTemplate() {
            const k = document.getElementById('tpl_select').value;
            const H = parseInt(document.getElementById('tpl_h').value) || 1000;
            const W = parseInt(document.getElementById('tpl_w').value) || 800;
            const D = parseInt(document.getElementById('tpl_d').value) || 500;
            const T = 18;
            const iw = W - 2 * T;
            let lines = [];

            if (k === 'wardrobe2' || k === 'kit_base' || k === 'kit_wall' || k === 'shoe_cab') {
                lines = [
                    `${H} ${D} 2 1`,
                    `${iw} ${D} 2 1`,
                    `${iw} ${D-20} 2 1`,
                    `${H-4} ${Math.floor(W/2)-3} 2 4`
                ];
            } else if (k === 'wardrobe3' || k === 'wardrobe_slide') {
                lines = [
                    `${H} ${D} 2 1`,
                    `${iw} ${D} 2 1`,
                    `${H-2*T} ${D-20} 1 1`,
                    `${Math.floor(iw/2)} ${D-20} 4 1`,
                    `${H-4} ${Math.floor(W/3)-3} 3 4`
                ];
            } else if (k === 'bookcase') {
                lines = [`${H} ${D} 2 1`, `${iw} ${D} 5 1`];
            } else if (k === 'nightstand' || k === 'chiffonier' || k === 'kit_drawers') {
                const dc = k === 'nightstand' ? 2 : (k === 'kit_drawers' ? 3 : 4);
                const dh = Math.floor((H - 2*T) / dc) - 4;
                lines = [
                    `${H} ${D} 2 1`,
                    `${iw} ${D} 2 1`,
                    `${dh} ${W-4} ${dc} 4`,
                    `${D-50} 140 ${dc*2} 1`,
                    `${iw-60} 140 ${dc*2} 1`
                ];
            } else if (k.includes('table') || k === 'desk_office') {
                lines = [
                    `${W} ${D} 1 4`,
                    `${H-T} ${D-40} 2 2`,
                    `${W-100} 120 2 1`
                ];
            } else if (k === 'storage_box' || k === 'bench_storage') {
                lines = [
                    `${W} ${D} 2 4`,
                    `${H-2*T} ${W} 2 2`,
                    `${H-2*T} ${D-2*T} 2 2`
                ];
            } else {
                lines = [
                    `${H} ${D} 2 1`,
                    `${iw} ${D} 2 1`,
                    `${iw} ${H-2*T} 1 0`
                ];
            }
            const box = document.getElementById('pieces_box');
            box.value = (box.value.trim() ? box.value.trim() + String.fromCharCode(10) : '') + lines.join(String.fromCharCode(10));
            openTab('tab1', document.querySelector('.tab-btn'));
        }
        window.addEventListener('DOMContentLoaded', () => { setTimeout(draw3D, 200); });

        
        function showKartela(type) {
            document.getElementById('kar_colors_grid').style.display = type === 'colors' ? 'grid' : 'none';
            document.getElementById('kar_cnc_grid').style.display = type === 'cnc' ? 'grid' : 'none';
        }

        function initKartela() {
            const cGrid = document.getElementById('kar_colors_grid');
            const cncGrid = document.getElementById('kar_cnc_grid');
            if (!cGrid || !cncGrid || cGrid.children.length > 0) return;

            const boardTypes = ['MDF 18mm', 'Suntalam 18mm', 'High Gloss', 'Akrilik', 'Lak MDF'];
            const colorNames = [
                'أبيض ثلجي', 'كريمي', 'بيج رملي', 'رمادي فاتح', 'أنثراسيت', 'أسود مطفي', 'جوز تركي', 'بلوط طبيعي', 'صنوبر', 'سنديان',
                'ماهوجني', 'تييك', 'أزرق بترولي', 'أخضر زيتوني', 'تراكوتا'
            ];
            let cHtml = '';
            for (let i = 0; i < 75; i++) {
                const hue = (i * 29) % 360;
                const sat = (i % 5 === 0) ? 8 : (35 + (i % 4) * 15);
                const lig = 22 + ((i * 7) % 65);
                const bg = `hsl(${hue}, ${sat}%, ${lig}%)`;
                const bType = boardTypes[i % boardTypes.length];
                const cName = colorNames[i % colorNames.length] + ' #' + (i + 1);
                cHtml += `<div onclick="alert('تم اختيار: ${cName} (${bType})')" style="cursor:pointer; background:var(--inp-bg); border:1px solid var(--inp-brd); border-radius:8px; padding:6px; text-align:center; box-shadow:0 2px 5px rgba(0,0,0,0.06);">
                    <div style="width:12px; height:12px; border-radius:50%; background:var(--bg-card); border:2px solid #94a3b8; margin:0 auto 5px;"></div>
                    <div style="height:46px; border-radius:6px; background:${bg}; border:1px solid rgba(0,0,0,0.15);"></div>
                    <div style="font-size:10px; font-weight:bold; margin-top:5px; line-height:1.2;">${cName}</div>
                    <div style="font-size:9px; color:#64748b;">${bType}</div>
                </div>`;
            }
            cGrid.innerHTML = cHtml;

            let cncHtml = '';
            for (let i = 1; i <= 75; i++) {
                const mode = i % 6;
                let inner = '';
                if (mode === 0) inner = `<rect x="12" y="12" width="56" height="86" fill="none" stroke="#8d6e63" stroke-width="2"/><rect x="20" y="20" width="40" height="70" fill="none" stroke="#8d6e63" stroke-width="1.5"/>`;
                else if (mode === 1) inner = `<path d="M14,98 L14,35 Q40,10 66,35 L66,98 Z" fill="none" stroke="#8d6e63" stroke-width="2"/>`;
                else if (mode === 2) inner = `<line x1="15" y1="20" x2="65" y2="20" stroke="#8d6e63" stroke-width="2"/><line x1="15" y1="35" x2="65" y2="35" stroke="#8d6e63" stroke-width="2"/><line x1="15" y1="50" x2="65" y2="50" stroke="#8d6e63" stroke-width="2"/><line x1="15" y1="65" x2="65" y2="65" stroke="#8d6e63" stroke-width="2"/><line x1="15" y1="80" x2="65" y2="80" stroke="#8d6e63" stroke-width="2"/>`;
                else if (mode === 3) inner = `<polygon points="40,15 65,55 40,95 15,55" fill="none" stroke="#8d6e63" stroke-width="2"/><rect x="12" y="12" width="56" height="86" fill="none" stroke="#8d6e63" stroke-width="1"/>`;
                else if (mode === 4) inner = `<path d="M12,30 Q40,15 68,30 M12,55 Q40,40 68,55 M12,80 Q40,65 68,80" fill="none" stroke="#8d6e63" stroke-width="2"/>`;
                else inner = `<rect x="14" y="14" width="22" height="36" fill="none" stroke="#8d6e63" stroke-width="1.8"/><rect x="44" y="14" width="22" height="36" fill="none" stroke="#8d6e63" stroke-width="1.8"/><rect x="14" y="58" width="52" height="36" fill="none" stroke="#8d6e63" stroke-width="1.8"/>`;

                cncHtml += `<div onclick="alert('تصميم كاباك CNC-${i} جاهز للتنفيذ')" style="cursor:pointer; background:var(--inp-bg); border:1px solid var(--inp-brd); border-radius:8px; padding:6px; text-align:center;">
                    <svg viewBox="0 0 80 110" style="width:100%; height:75px; background:#faf6f0; border-radius:4px; border:1px solid #d7ccc8;">
                        <rect x="4" y="4" width="72" height="102" fill="none" stroke="#5d4037" stroke-width="2"/>
                        ${inner}
                    </svg>
                    <div style="font-size:10px; font-weight:bold; margin-top:4px;">CNC-${i}</div>
                </div>`;
            }
            cncGrid.innerHTML = cncHtml;
        }
        window.addEventListener('DOMContentLoaded', () => { setTimeout(initKartela, 300); });

        function setTheme(t) {
            document.body.className = t ? ('theme-' + t) : '';
            localStorage.setItem('aq_theme', t);
        }
        window.addEventListener('DOMContentLoaded', () => {
            const saved = localStorage.getItem('aq_theme') || '';
            if (saved) document.body.className = 'theme-' + saved;
        });

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
    <div class="lang-bar" style="justify-content: space-between; align-items: center;">
        <div style="display:flex; gap:5px;">
            <button type="button" onclick="setTheme('')" style="padding:5px 9px; border:none; border-radius:6px; cursor:pointer; font-size:12px; background:#2563eb; color:#fff;">🔵 أزرق</button>
            <button type="button" onclick="setTheme('wood')" style="padding:5px 9px; border:none; border-radius:6px; cursor:pointer; font-size:12px; background:#8d6e63; color:#fff;">🪵 خشبي</button>
            <button type="button" onclick="setTheme('dark')" style="padding:5px 9px; border:none; border-radius:6px; cursor:pointer; font-size:12px; background:#1e293b; color:#fff;">🌙 ليلي</button>
        </div>
        <div style="display:flex; gap:5px;">
            <a href="/?lang=ar" class="{{ 'active' if lang=='ar' else '' }}">🇸🇦 العربية</a>
            <a href="/?lang=tr" class="{{ 'active' if lang=='tr' else '' }}">🇹🇷 Türkçe</a>
            <a href="/?lang=en" class="{{ 'active' if lang=='en' else '' }}">🇬🇧 English</a>
        </div>
    </div>
    <div class="header">
        <h2>🪵 {{ t['title'] }}</h2>
        <p>{{ t['sub'] }}</p>
    </div>

    {% if paywall %}
    <div class="paywall">
        <h3>{{ t['pay_title'] }}</h3>
        <p>{{ t['pay_desc'] }}</p>
        <div style="display:flex; flex-direction:column; gap:8px; margin:12px 0; text-align:right;">
            <div style="background:#fff; padding:10px; border-radius:8px; border:1px solid #cbd5e1;">
                <b>🔹 باقة Pro — 250 TL / شهرياً</b><br>
                <span style="font-size:12px; color:#475569;">تقطيع الألواح + الفاتورة + قراءة الصور AI + القوالب الجاهزة</span>
            </div>
            <div style="background:#fff; padding:10px; border-radius:8px; border:2px solid #2563eb;">
                <b>🔸 باقة Pro Max — 450 TL / شهرياً</b><br>
                <span style="font-size:12px; color:#475569;">كل ميزات Pro + اسم الورشة + دفتر الورشة والمخزون + رابط عامل المنشار + واتساب</span>
            </div>
            <div style="background:#fff; padding:10px; border-radius:8px; border:2px solid #b45309;">
                <b>👑 باقة Ultra — 750 TL / شهرياً</b><br>
                <span style="font-size:12px; color:#475569;">كل ميزات Pro Max + تصدير CNC CSV + قارتيلا 75+75 + PDF + ملصقات Etiket</span>
            </div>
        </div>
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
        <button type="button" class="tab-btn" onclick="openTab('tab4', this)">{{ t['tab_tpl'] }}</button>
        <button type="button" class="tab-btn" onclick="openTab('tab5', this)">{{ t['tab_led'] }}</button>
        <button type="button" class="tab-btn" onclick="openTab('tab6', this)">{{ t['tab_kar'] }}</button>
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
            <div style="margin:6px 0; font-size:12px; color:#64748b;">💡 نصيحة: أضف <b>G</b> بنهاية السطر لمنع التدوير (اتجاه العرق)، وأضف <b>2mm</b> للشريط السميك (مثال: <code>800 600 2 4 2mm G</code>)</div>
            <label style="display:flex; align-items:center; gap:8px; font-weight:normal; cursor:pointer;">
                <input type="checkbox" name="use_offcuts" value="1" checked style="width:auto;"> ♻️ استخدام البقايا المحفوظة تلقائياً قبل فتح لوح جديد
            </label>

            <div class="row">
                <div><label>👤 اسم الزبون (اختياري):</label><input type="text" name="cust_name" value="{{ cust_name }}" placeholder="{{ t['cust_ph'] }}"></div>
                <div><label>💵 العربون المدفوع:</label><input type="text" inputmode="decimal" dir="ltr" name="deposit" value="{{ deposit }}"></div>
            </div>
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
                <div><label>شريط PVC 0.4mm (TL)</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="p_pvc" value="12"></div>
                <div><label>شريط PVC 2mm (TL)</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="p_pvc2" value="25"></div>
            </div>
            <label>{{ t['p_cut'] }}</label><input type="text" inputmode="numeric" dir="ltr" lang="en" name="p_cut" value="100">
            <hr style="margin:14px 0; border:0; border-top:1px solid var(--inp-brd);">
            <div class="row">
                <div><label>🏷️ اسم الورشة (للفاتورة):</label><input type="text" name="ws_name" value="{{ ws_name }}"></div>
                <div><label>📞 هاتف الورشة:</label><input type="text" dir="ltr" name="ws_phone" value="{{ ws_phone }}"></div>
            </div>
            <label>📄 نوع الفاتورة:</label>
            <select name="inv_mode">
                <option value="workshop" {{ 'selected' if inv_mode=='workshop' else '' }}>🔧 نسخة الورشة (تظهر الهدر والتفاصيل)</option>
                <option value="customer" {{ 'selected' if inv_mode=='customer' else '' }}>🤝 عرض سعر للزبون (يخفي الهدر)</option>
            </select>
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

        
        <div id="tab4" class="tab-content">
            <label>🧊 اختر قالباً جاهزاً (22+ نموذج):</label>
            <select id="tpl_select" onchange="onTplChange()">
                <optgroup label="🚪 خزائن وملابس">
                    <option value="wardrobe2">خزانة ملابس ببابين</option>
                    <option value="wardrobe3">خزانة ملابس 3 أبواب</option>
                    <option value="wardrobe_slide">خزانة سحاب (جرار)</option>
                    <option value="shoe_cab">خزانة أحذية</option>
                    <option value="bookcase">مكتبة / رفوف مفتوحة (4 رفوف)</option>
                </optgroup>
                <optgroup label="🍳 مطابخ">
                    <option value="kit_base">خزانة مطبخ سفلية (بابين)</option>
                    <option value="kit_wall">خزانة مطبخ علوية (بابين)</option>
                    <option value="kit_drawers">وحدة أدراج مطبخ (3 دروج)</option>
                    <option value="kit_tall">خزانة مطبخ عالية (ثلاجة/فرن)</option>
                </optgroup>
                <optgroup label="🛏️ غرف نوم وأدراج">
                    <option value="nightstand">كومودينو (طاولة سرير 2 درج)</option>
                    <option value="chiffonier">شفونير (4 دروج)</option>
                    <option value="dresser">تسريحة مع أدراج</option>
                    <option value="bed_single">هيكل سرير مفرد</option>
                    <option value="bed_double">هيكل سرير مزدوج</option>
                </optgroup>
                <optgroup label="🪑 طاولات ومكاتب وكراسي">
                    <option value="table_dining">طاولة طعام مستطيلة</option>
                    <option value="table_coffee">طاولة قهوة / وسط</option>
                    <option value="desk_office">مكتب دراسة / عمل</option>
                    <option value="tv_unit">طاولة تلفزيون (TV Ünitesi)</option>
                    <option value="chair_simple">كرسي خشبي بسيط</option>
                    <option value="bench_storage">بنش / مقعد مع تخزين</option>
                    <option value="storage_box">صندوق تخزين (مطمورة)</option>
                </optgroup>
            </select>
            <div class="row">
                <div><label>الارتفاع H (مم)</label><input type="number" id="tpl_h" value="2000" oninput="draw3D()"></div>
                <div><label>العرض W (مم)</label><input type="number" id="tpl_w" value="1000" oninput="draw3D()"></div>
                <div><label>العمق D (مم)</label><input type="number" id="tpl_d" value="600" oninput="draw3D()"></div>
            </div>
            <div style="text-align:center; margin:10px 0;">
                <img id="tpl_preview_img" src="https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=500&q=80" style="max-height:170px; width:auto; max-width:100%; object-fit:cover; border-radius:10px; border:1px solid var(--inp-brd);" alt="شكل القطعة جاهزة">
            </div>
            <div style="text-align:center; margin:12px 0; background:var(--inp-bg); border:1px solid var(--inp-brd); border-radius:10px; padding:10px;">
                <canvas id="canvas3d" width="320" height="220" style="max-width:100%;"></canvas>
                <div style="display:flex; justify-content:center; gap:10px; margin-top:8px;">
                    <button type="button" onclick="rot3D(-15)" style="padding:6px 14px; border:none; border-radius:6px; background:#2563eb; color:#fff; cursor:pointer; font-weight:bold;">⬅️ يمين</button>
                    <button type="button" onclick="rot3D(15)" style="padding:6px 14px; border:none; border-radius:6px; background:#2563eb; color:#fff; cursor:pointer; font-weight:bold;">يسار ➡️</button>
                </div>
            </div>
            <button type="button" onclick="applyTemplate()" style="width:100%; padding:12px; background:#f59e0b; color:#fff; border:none; border-radius:8px; font-weight:bold; font-size:15px; cursor:pointer;">📥 توليد المقاسات وإضافتها للتقطيع</button>
        </div>

        
        <div id="tab5" class="tab-content">
            <h4 style="margin:6px 0;">♻️ بقايا الألواح الكبيرة (المخزون / Fire):</h4>
            {% if offcuts %}
                <div style="max-height:160px; overflow-y:auto; border:1px solid var(--inp-brd); border-radius:8px; padding:8px; background:var(--inp-bg); font-size:13px;">
                {% for o in offcuts %}
                    <div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px dashed var(--inp-brd);">
                        <span>🪵 {{ o.mat }} | <b>{{ o.w }} × {{ o.h }} مم</b></span>
                        <span style="color:#64748b;">{{ o.date }}</span>
                    </div>
                {% endfor %}
                </div>
            {% else %}
                <p style="font-size:13px; color:#64748b;">لا توجد بقايا محفوظة حالياً. تُحفظ البقايا أكبر من 500×500 مم تلقائياً بعد كل تقطيع.</p>
            {% endif %}

            <h4 style="margin:14px 0 6px;">📒 دفتر الورشة (أرشيف الزبائن):</h4>
            {% if ledger %}
                <div style="max-height:220px; overflow-y:auto; border:1px solid var(--inp-brd); border-radius:8px; padding:8px; background:var(--inp-bg); font-size:13px;">
                {% for l in ledger %}
                    <div style="padding:6px 0; border-bottom:1px dashed var(--inp-brd);">
                        <div><b>👤 {{ l.cust }}</b> ({{ l.date }}) - {{ l.mat }}</div>
                        <div style="color:#059669;">الإجمالي: {{ l.total }} {{ l.curr }} | العربون: {{ l.dep }} | <b>المتبقي: {{ l.rem }} {{ l.curr }}</b></div>
                    </div>
                {% endfor %}
                </div>
            {% else %}
                <p style="font-size:13px; color:#64748b;">لا توجد طلبيات مسجلة في الدفتر بعد.</p>
            {% endif %}
        </div>

        
        <div id="tab6" class="tab-content">
            <div style="display:flex; gap:8px; margin-bottom:12px;">
                <button type="button" onclick="showKartela('colors')" style="flex:1; padding:10px; border:none; border-radius:8px; background:#2563eb; color:#fff; font-weight:bold; cursor:pointer;">🎨 قارتيلا الألوان (75 لون)</button>
                <button type="button" onclick="showKartela('cnc')" style="flex:1; padding:10px; border:none; border-radius:8px; background:#b45309; color:#fff; font-weight:bold; cursor:pointer;">🚪 قارتيلا كاباك CNC (75 تصميم)</button>
            </div>
            <div id="kar_colors_grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(90px, 1fr)); gap:10px; max-height:420px; overflow-y:auto; padding:6px;"></div>
            <div id="kar_cnc_grid" style="display:none; grid-template-columns:repeat(auto-fill, minmax(95px, 1fr)); gap:10px; max-height:420px; overflow-y:auto; padding:6px;"></div>
        </div>

        <button type="submit" class="submit-btn">{{ t['btn_calc'] }}</button>
    </form>
    {% endif %}

    {% if error %}<div class="error">❌ {{ error }}</div>{% endif %}

    {% if invoice %}
    <div class="result-box">
        <h3>{{ t['inv_title'] }}</h3>
        <img src="data:image/png;base64,{{ invoice }}">
        <a href="/download/{{ invoice_id }}" class="dl-btn">{{ t['dl_btn'] }}</a>
        <a href="https://wa.me/?text={{ wa_text }}" target="_blank" class="dl-btn" style="background:#25D366;">📲 إرسال عبر واتساب</a>
        <button type="button" onclick="window.print()" class="dl-btn" style="background:#64748b; border:none; cursor:pointer;">🏷️ طباعة ملصقات القص (Etiket)</button>
        <a href="/saw/{{ order_id }}" target="_blank" class="dl-btn" style="background:#f59e0b;">🪚 رابط عامل المنشار (بدون أسعار)</a>
        <a href="/export_csv/{{ order_id }}" class="dl-btn" style="background:#0f766e;">📊 تصدير CSV لماكينة القص (CNC)</a>
        <a href="/invoice_pdf/{{ order_id }}" class="dl-btn" style="background:#dc2626;">📄 تحميل الفاتورة PDF</a>
        <a href="/etiket/{{ order_id }}" target="_blank" class="dl-btn" style="background:#7c3aed;">🏷️ صفحة ملصقات (Etiket)</a>

        <h3>{{ t['sheets_title'] }} ({{ sheets_cnt }})</h3>
        {% for s in sheets %}
        <img src="data:image/png;base64,{{ s.b64 }}">
        <a href="/download/{{ s.id }}" class="dl-btn">{{ t['dl_btn'] }} #{{ loop.index }}</a>
        {% endfor %}
    </div>
    {% endif %}
</div>
</body>
</html>
"""


def _tmp_set(prefix, key, val):
    try:
        with open(f"/tmp/aq_{prefix}_{key}.json", "w", encoding="utf-8") as f:
            json.dump(val, f, ensure_ascii=False)
    except Exception:
        pass

def _tmp_get(prefix, key):
    try:
        with open(f"/tmp/aq_{prefix}_{key}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

class _TmpDict:
    def __init__(self, prefix):
        self.prefix = prefix
    def __setitem__(self, k, v):
        _tmp_set(self.prefix, k, v)
    def get(self, k, default=None):
        v = _tmp_get(self.prefix, k)
        return v if v is not None else default

IMG_CACHE = _TmpDict("img")

def cache_img(b64_str, fname):
    img_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    IMG_CACHE[img_id] = [b64_str, fname]
    return img_id

SAW_CACHE = _TmpDict("saw")
CSV_CACHE = _TmpDict("csv")

@app.route("/saw/<oid>", methods=["GET"])
def saw_view(oid):
    data = SAW_CACHE.get(oid)
    if not data:
        return "انتهت صلاحية رابط عامل المنشار.", 404
    imgs_html = "".join(f'<img src="/download/{sid}" style="width:100%; margin-top:12px; border:1px solid #ccc; border-radius:8px;">' for sid in data["sheet_ids"])
    return f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>أمر قص - عامل المنشار</title></head>
    <body style="font-family:Tahoma,Arial; padding:14px; background:#f8fafc; max-width:650px; margin:auto;">
    <h2 style="color:#1e3a8a;">🪚 أمر قص لعامل المنشار ({data['mat']})</h2>
    <pre style="background:#fff; padding:12px; border-radius:8px; border:1px solid #cbd5e1; white-space:pre-wrap; font-size:14px; direction:rtl;">{data['summary']}</pre>
    {imgs_html}
    </body></html>"""

@app.route("/export_csv/<oid>", methods=["GET"])
def export_csv(oid):
    csv_txt = CSV_CACHE.get(oid)
    if not csv_txt:
        return "انتهت صلاحية ملف CSV.", 404
    resp = make_response(csv_txt.encode("utf-8-sig"))
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f"attachment; filename=cut_list_{oid}.csv"
    return resp


ETIKET_CACHE = _TmpDict("etiket")

@app.route("/invoice_pdf/<oid>", methods=["GET"])
def invoice_pdf(oid):
    data = SAW_CACHE.get(oid)
    if not data or not data.get("inv_id"):
        return "انتهت صلاحية الفاتورة.", 404
    item = IMG_CACHE.get(data["inv_id"])
    if not item:
        return "انتهت صلاحية الفاتورة.", 404
    im = Image.open(io.BytesIO(base64.b64decode(item[0]))).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="PDF", resolution=100.0)
    resp = make_response(buf.getvalue())
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f"attachment; filename=invoice_{oid}.pdf"
    return resp

@app.route("/etiket/<oid>", methods=["GET"])
def etiket_view(oid):
    cards = ETIKET_CACHE.get(oid)
    if not cards:
        return "انتهت صلاحية الملصقات.", 404
    cards_html = ""
    for c in cards:
        cards_html += f"""<div style="border:2px solid #1e293b; border-radius:8px; padding:10px; width:210px; display:inline-block; margin:6px; font-family:Tahoma,Arial; background:#fff; page-break-inside:avoid;">
            <div style="font-weight:bold; font-size:15px; border-bottom:1px solid #cbd5e1; padding-bottom:4px;">#{c['gi']} | {c['l']} × {c['w']} مم</div>
            <div style="font-size:12px; margin-top:4px;">الكمية: <b>{c['qty']}</b> | {c['mat']}</div>
            <div style="font-size:12px;">شريط: طول({c['le']}) عرض({c['we']}) [{c['thick']}mm]</div>
            <div style="font-size:11px; color:#475569; margin-top:3px;">الزبون: {c['cust']}</div>
        </div>"""
    return f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>ملصقات القص - Etiket</title></head>
    <body style="background:#f1f5f9; padding:12px;">
    <button onclick="window.print()" style="padding:10px 20px; background:#2563eb; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer; margin-bottom:12px;">🖨️ طباعة الملصقات</button>
    <div>{cards_html}</div></body></html>"""

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/download/<img_id>", methods=["GET"])
def download_img(img_id):
    item = IMG_CACHE.get(img_id)
    if not item:
        return "انتهت صلاحية الصورة، يرجى الضغط على احسب التقطيع مرة أخرى.", 404
    b64_str, fname = item
    resp = make_response(base64.b64decode(b64_str))
    resp.headers["Content-Type"] = "image/png"
    resp.headers["Content-Disposition"] = f"attachment; filename={fname}"
    return resp

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
    client_ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
    trial_used = (request.cookies.get("trial_used") == "1") or bool(client_ip and _tmp_get("trial_ip", client_ip.replace(".", "_").replace(":", "_")))

    st_view = load_store()
    ctx = {
        "lang": lang, "t": TR[lang], "iban": IBAN_INFO, "price": PRO_PRICE,
        "ws_name": WORKSHOP_NAME, "ws_phone": WORKSHOP_PHONE, "inv_mode": "workshop",
        "cust_name": "", "deposit": "0", "order_id": "",
        "offcuts": list(reversed(st_view.get("offcuts", [])))[:20],
        "ledger": list(reversed(st_view.get("ledger", [])))[:25],
        "sw": 2800, "sh": 2100, "kerf": 4, "pieces_text": "", "wa_text": "",
        "paywall": False, "error": None, "invoice": None, "sheets": []
    }

    if request.method == "POST":
        code = request.form.get("unlock_code", "").strip()
        if code:
            ok, msg_txt, tier = redeem_single_code(code, "web")
            if ok:
                resp = make_response(render_template_string(HTML_TEMPLATE, **ctx))
                resp.set_cookie("is_pro", "1", max_age=30*86400)
                resp.set_cookie("sub_tier", tier, max_age=30*86400)
                return resp
            ctx["paywall"], ctx["error"] = True, msg_txt
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
            pieces_text = normalize_digits(request.form.get("pieces", "").strip())

            ctx.update({"sw": sw, "sh": sh, "kerf": kerf, "pieces_text": pieces_text})

            groups = []
            for line in normalize_digits(pieces_text).splitlines():
                tokens = [t for t in re.split(r"[\s,;*×x:=]+", line.strip()) if t]
                if len(tokens) >= 2:
                    l, w = int(float(tokens[0])), int(float(tokens[1]))
                    qty = int(tokens[2]) if len(tokens) > 2 and tokens[2].isdigit() else 1
                    le, we = parse_edges(tokens[3]) if len(tokens) > 3 else (0, 0)
                    up_line = line.upper()
                    no_rot = (" G" in up_line or up_line.endswith("G") or "عرق" in line)
                    thick = "2" if "2MM" in up_line else "0.4"
                    groups.append({"l": l, "w": w, "qty": qty, "le": le, "we": we, "gi": len(groups) + 1, "no_rot": no_rot, "thick": thick})

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

            ws_name = request.form.get("ws_name", WORKSHOP_NAME).strip() or WORKSHOP_NAME
            ws_phone = request.form.get("ws_phone", WORKSHOP_PHONE).strip() or WORKSHOP_PHONE
            inv_mode = request.form.get("inv_mode", "workshop")
            ctx.update({"ws_name": ws_name, "ws_phone": ws_phone, "inv_mode": inv_mode})
            from urllib.parse import quote
            wa_msg = f"🪵 {ws_name}\nالمادة: {mat}\nالألواح: {total_sheets}\nالسعر الإجمالي: {final_price:.1f} {curr}\nللتواصل: {ws_phone}"
            ctx["wa_text"] = quote(wa_msg)
            cust_name = request.form.get("cust_name", "").strip()
            deposit = float(normalize_digits(request.form.get("deposit", "0") or "0"))
            ctx.update({"cust_name": cust_name, "deposit": str(deposit)})
            inv_b64 = render_invoice_b64(mat, sw, sh, len(pieces), total_sheets, waste_pct, pvc_m, acc_disp, final_price, curr, ws_name, ws_phone, inv_mode, cust_name, deposit)
            ctx["invoice"] = inv_b64
            ctx["invoice_id"] = cache_img(inv_b64, "invoice.png")
            ctx["sheets_cnt"] = total_sheets
            sheets_list = []
            for i, b in enumerate(bins):
                sb64 = render_sheet_b64(b, i + 1, total_sheets, sw, sh, kerf)[0]
                sheets_list.append({"b64": sb64, "id": cache_img(sb64, f"sheet_{i+1}.png")})
            ctx["sheets"] = sheets_list
            oid = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
            ctx["order_id"] = oid
            SAW_CACHE[oid] = {"mat": mat, "summary": build_cut_summary(groups), "sheet_ids": [x["id"] for x in sheets_list], "inv_id": ctx["invoice_id"]}
            ETIKET_CACHE[oid] = [{"gi": g["gi"], "l": g["l"], "w": g["w"], "qty": g["qty"], "le": g["le"], "we": g["we"], "thick": g["thick"], "mat": mat, "cust": cust_name or "-"} for g in groups]
            csv_lines = ["Group,Length_mm,Width_mm,Qty,Edge_Length,Edge_Width"]
            for g in groups:
                csv_lines.append(f"{g['gi']},{g['l']},{g['w']},{g['qty']},{g['le']},{g['we']}")
            CSV_CACHE[oid] = "\n".join(csv_lines)

            # حفظ البقايا الكبيرة (> 500x500) ودفتر الورشة
            st_save = load_store()
            today_str = datetime.now().strftime("%Y-%m-%d")
            for _, _, fw, fh in bins[-1].free:
                aw_f, ah_f = fw - kerf, fh - kerf
                if aw_f >= 500 and ah_f >= 500:
                    st_save.setdefault("offcuts", []).append({"mat": mat, "w": aw_f, "h": ah_f, "date": today_str})
            st_save["offcuts"] = st_save.get("offcuts", [])[-30:]
            if cust_name or deposit > 0:
                rem_val = max(0.0, final_price - deposit)
                st_save.setdefault("ledger", []).append({
                    "cust": cust_name or "زبون نقدي", "mat": mat, "date": today_str,
                    "total": f"{final_price:.1f}", "dep": f"{deposit:.1f}", "rem": f"{rem_val:.1f}", "curr": curr
                })
                st_save["ledger"] = st_save.get("ledger", [])[-50:]
            save_store(st_save)
            ctx["offcuts"] = list(reversed(st_save.get("offcuts", [])))[:20]
            ctx["ledger"] = list(reversed(st_save.get("ledger", [])))[:25]

            resp = make_response(render_template_string(HTML_TEMPLATE, **ctx))
            if client_ip:
                _tmp_set("trial_ip", client_ip.replace(".", "_").replace(":", "_"), 1)
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

TG_TEMPLATES = {
    "wardrobe2": ("خزانة ملابس ببابين (2000×1000×600)", "2000 600 2 1\n964 600 2 1\n964 580 2 1\n1996 497 2 4", "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=600&q=80"),
    "wardrobe3": ("خزانة ملابس 3 أبواب (2100×1500×600)", "2100 600 2 1\n1464 600 2 1\n2064 580 1 1\n732 580 4 1\n2096 497 3 4", "https://images.unsplash.com/photo-1558997519-83ea9252edf8?w=600&q=80"),
    "kit_base": ("مطبخ سفلي بابين (720×800×560)", "720 560 2 1\n764 560 2 1\n764 540 1 1\n716 397 2 4", "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=600&q=80"),
    "kit_wall": ("مطبخ علوي بابين (720×800×320)", "720 320 2 1\n764 320 2 1\n764 300 1 1\n716 397 2 4", "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=600&q=80"),
    "nightstand": ("كومودينو 2 درج (500×450×400)", "500 400 2 1\n414 400 2 1\n228 446 2 4\n350 140 4 1\n354 140 4 1", "https://images.unsplash.com/photo-1532372320572-cda25653a26d?w=600&q=80"),
    "chiffonier": ("شفونير 4 دروج (900×800×450)", "900 450 2 1\n764 450 2 1\n212 796 4 4\n400 140 8 1\n704 140 8 1", "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=600&q=80"),
    "table_dining": ("طاولة طعام (750×1400×800)", "1400 800 1 4\n732 760 2 2\n1300 120 2 1", "https://images.unsplash.com/photo-1577140917170-285929fb55b7?w=600&q=80"),
    "desk_office": ("مكتب عمل (750×1200×600)", "1200 600 1 4\n732 560 2 2\n1100 120 2 1", "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=600&q=80"),
    "storage_box": ("صندوق تخزين (450×800×400)", "800 400 2 4\n414 800 2 2\n414 364 2 2", "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=600&q=80"),
}

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
        [{"text": f"🪚 المنشار: {s['kerf']} مم", "callback_data": "toggle_kerf"},
         {"text": "🖼️ أنواع الخشب", "callback_data": "wood_catalog"}],
        [{"text": "🧊 قوالب جاهزة (خزائن/طاولات)", "callback_data": "menu_tpl"}],
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
        elif data == "toggle_kerf":
            k_order = [3, 4, 5]
            s["kerf"] = k_order[(k_order.index(s["kerf"]) + 1) % len(k_order)] if s["kerf"] in k_order else 4
            tg_edit_msg(chat_id, msg_id, "⚙️ إعدادات التقطيع الحالية:", main_menu_markup(s, host_url))
        elif data == "menu_tpl":
            kb = {"inline_keyboard": [
                [{"text": "🚪 خزانة بابين", "callback_data": "run_tpl_wardrobe2"},
                 {"text": "🚪 خزانة 3 أبواب", "callback_data": "run_tpl_wardrobe3"}],
                [{"text": "🍳 مطبخ سفلي", "callback_data": "run_tpl_kit_base"},
                 {"text": "🍳 مطبخ علوي", "callback_data": "run_tpl_kit_wall"}],
                [{"text": "🛏️ كومودينو", "callback_data": "run_tpl_nightstand"},
                 {"text": "🗄️ شفونير 4 دروج", "callback_data": "run_tpl_chiffonier"}],
                [{"text": "🪑 طاولة طعام", "callback_data": "run_tpl_table_dining"},
                 {"text": "💻 مكتب عمل", "callback_data": "run_tpl_desk_office"}],
                [{"text": "📦 صندوق تخزين", "callback_data": "run_tpl_storage_box"},
                 {"text": "🔙 رجوع", "callback_data": "back_main"}]
            ]}
            tg_edit_msg(chat_id, msg_id, "🧊 اختر القالب الجاهز لحساب التقطيع والفاتورة فوراً:", kb)
        elif data.startswith("run_tpl_"):
            tkey = data.replace("run_tpl_", "")
            if tkey in TG_TEMPLATES:
                tname, tpieces, tphoto = TG_TEMPLATES[tkey]
                tg_api("sendPhoto", data={"chat_id": chat_id, "photo": tphoto, "caption": f"🪑 شكل القطعة بعد التركيب: {tname}\n⏳ جاري حساب التقطيع وإصدار الفاتورة..."})
                try:
                    groups = []
                    for line in tpieces.splitlines():
                        tokens = line.split()
                        l, w, qty = int(tokens[0]), int(tokens[1]), int(tokens[2])
                        le, we = parse_edges(tokens[3])
                        groups.append({"l": l, "w": w, "qty": qty, "le": le, "we": we, "gi": len(groups) + 1})
                    sw, sh, kerf = s["sw"], s["sh"], s["kerf"]
                    pieces = [dict(g) for g in groups for _ in range(g["qty"])]
                    _, bins = best_layout(pieces, sw, sh, kerf, s["rot"])
                    total_sheets = len(bins)
                    waste_pct = (1 - sum(p["l"] * p["w"] for p in pieces) / float(total_sheets * sw * sh)) * 100
                    pvc_m = sum(p["le"] * p["l"] + p["we"] * p["w"] for p in pieces) / 1000.0
                    total_tl = ((total_sheets * (s["p_sheet"] + s["p_cut"])) + (pvc_m * s["p_pvc"])) * (1 + s["margin"] / 100.0)
                    curr = s["curr"]
                    final_price = total_tl / 35.0 if curr == "USD" else (total_tl / 38.0 if curr == "EUR" else total_tl)
                    tg_send_msg(chat_id, build_cut_summary(groups))
                    inv_b64 = render_invoice_b64(s["mat"], sw, sh, len(pieces), total_sheets, waste_pct, pvc_m, 0, final_price, curr)
                    tg_send_b64_photo(chat_id, inv_b64, caption=f"🧾 الفاتورة ({tname}) | الألواح: {total_sheets} | الهدر: {waste_pct:.1f}%")
                    for i, b in enumerate(bins):
                        s_b64, w_pct = render_sheet_b64(b, i + 1, total_sheets, sw, sh, kerf)
                        tg_send_b64_photo(chat_id, s_b64, caption=f"📐 لوح {i + 1}/{total_sheets} (هدر {w_pct:.1f}%)")
                except Exception as ex:
                    tg_send_msg(chat_id, f"❌ خطأ: {ex}")
        elif data == "wood_catalog":
            for w_name, w_url in WOOD_CATALOG:
                tg_api("sendPhoto", data={"chat_id": chat_id, "photo": w_url, "caption": f"🪵 {w_name}"})
            tg_send_msg(chat_id, "اختر من القائمة:", main_menu_markup(s, host_url))
        elif data == "back_main":
            tg_edit_msg(chat_id, msg_id, "⚙️ إعدادات التقطيع الحالية:", main_menu_markup(s, host_url))
        return "OK", 200

    msg = update.get("message")
    if not msg:
        return "OK", 200

    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    s = get_session(chat_id)

    is_admin = bool(ADMIN_CHAT_ID and str(chat_id) == str(ADMIN_CHAT_ID).strip())
    st_global = load_store()
    if not is_admin and str(chat_id) in st_global.get("banned", []):
        tg_send_msg(chat_id, "⛔ تم حظرك من استخدام البوت.")
        return "OK", 200

    # تسجيل المستخدم وإرسال نسخة من رسالته للإدارة
    if not is_admin:
        if str(chat_id) not in st_global["tg_users"]:
            st_global["tg_users"][str(chat_id)] = {"trial_used": False, "pro_until": 0}
            save_store(st_global)
        if ADMIN_CHAT_ID:
            u_obj = msg.get("from", {})
            u_name = u_obj.get("first_name", "") + (" @" + u_obj["username"] if u_obj.get("username") else "")
            fwd_txt = text if text else ("[صورة]" if "photo" in msg else "[ملف/رسالة]")
            tg_send_msg(ADMIN_CHAT_ID, f"📩 رسالة من: {u_name} (`{chat_id}`)\n{fwd_txt}")

    if text in ("/start", "/menu"):
        welcome = (
            "أهلاً بك في بوت أبو القيس لتقطيع الأخشاب 🪵\n\n"
            "• أرسل **صورة الطلبية** لقراءتها بالذكاء الاصطناعي.\n"
            "• أو اكتب المقاسات مباشرة (مثال: `800 600 4 2`).\n"
            "• لتفعيل اشتراكك أرسل: `/activate الكود`\n"
            "• استخدم الأزرار بالأسفل لتغيير الإعدادات:"
        )
        if is_admin:
            welcome += "\n\n👑 أوامر الإدارة:\n`/newcode pro` | `/newcode promax` | `/newcode ultra` | `/stats` | `/broadcast الرسالة`\n`/ban المعرف` | `/unban المعرف`"
        tg_send_msg(chat_id, welcome, main_menu_markup(s, host_url))
        return "OK", 200


    if text == "/woods":
        for w_name, w_url in WOOD_CATALOG:
            tg_api("sendPhoto", data={"chat_id": chat_id, "photo": w_url, "caption": f"🪵 {w_name}"})
        return "OK", 200

    if text.startswith("/broadcast"):
        if not is_admin:
            tg_send_msg(chat_id, "⛔ هذا الأمر مخصص لصاحب البوت فقط.")
            return "OK", 200
        b_msg = text.replace("/broadcast", "", 1).strip()
        if not b_msg:
            tg_send_msg(chat_id, "⚠️ اكتب الرسالة بعد الأمر، مثال:\n`/broadcast خصم 20% اليوم!`")
            return "OK", 200
        st = load_store(force=True)
        users = list(st["tg_users"].keys())
        sent = 0
        for uid in users:
            if uid not in st.get("banned", []):
                tg_send_msg(uid, f"📢 إعلان من الإدارة:\n\n{b_msg}")
                sent += 1
        tg_send_msg(chat_id, f"✅ تم إرسال الإذاعة إلى {sent} مستخدم.")
        return "OK", 200

    if text.startswith("/ban "):
        if not is_admin:
            return "OK", 200
        target_id = text.split(maxsplit=1)[1].strip()
        st = load_store(force=True)
        if target_id not in st.setdefault("banned", []):
            st["banned"].append(target_id)
            save_store(st)
        tg_send_msg(chat_id, f"🚫 تم حظر المستخدم `{target_id}`.")
        return "OK", 200

    if text.startswith("/unban "):
        if not is_admin:
            return "OK", 200
        target_id = text.split(maxsplit=1)[1].strip()
        st = load_store(force=True)
        if target_id in st.get("banned", []):
            st["banned"].remove(target_id)
            save_store(st)
        tg_send_msg(chat_id, f"✅ تم إلغاء حظر المستخدم `{target_id}`.")
        return "OK", 200

    if text.startswith("/newcode"):
        if not is_admin:
            tg_send_msg(chat_id, "⛔ هذا الأمر مخصص لصاحب البوت فقط.")
            return "OK", 200
        parts = text.split(maxsplit=1)
        tier = parts[1].strip().lower() if len(parts) > 1 else "pro"
        if tier not in TIERS:
            tier = "pro"
        new_c = generate_single_code(tier)
        t_name = TIERS[tier]["name"]
        tg_send_msg(chat_id, f"🎟️ كود تفعيل جديد لباقة **{t_name}** (لمدة 30 يوماً):\n`{new_c}`")
        return "OK", 200

    if text == "/stats":
        if not is_admin:
            tg_send_msg(chat_id, "⛔ هذا الأمر مخصص لصاحب البوت فقط.")
            return "OK", 200
        st = load_store(force=True)
        total_c = len(st["codes"])
        unused_c = sum(1 for v in st["codes"].values() if not v.get("used"))
        now_ts = int(time.time())
        active_u = sum(1 for u in st["tg_users"].values() if u.get("pro_until", 0) > now_ts)
        total_u = len(st["tg_users"])
        banned_u = len(st.get("banned", []))
        tg_send_msg(chat_id, f"📊 إحصائيات النظام:\n• إجمالي المستخدمين: {total_u}\n• المحظورون: {banned_u}\n• مشتركون نشطون: {active_u}\n• إجمالي الأكواد: {total_c} (غير مستخدم: {unused_c})")
        return "OK", 200

    if text.startswith("/activate"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            tg_send_msg(chat_id, "⚠️ أرسل الكود هكذا:\n`/activate QAIS-1234-AB`")
            return "OK", 200
        ok, msg_txt, _ = redeem_single_code(parts[1], chat_id)
        tg_send_msg(chat_id, ("✅ " if ok else "❌ ") + msg_txt)
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
            tg_send_msg(chat_id, f"✅ تم رفع `{fname}` إلى GitHub بنجاح!\n⏳ جاري تحديث السيرفر على Render، سأرسل لك إشعاراً بعد دقيقة عند الجاهزية.")
            
            def notify_ready(cid, fn):
                time.sleep(65)
                tg_send_msg(cid, f"🚀 تم تحديث السيرفر بالملف `{fn}` بنجاح! يمكنك استخدام البوت الآن.")
            
            threading.Thread(target=notify_ready, args=(chat_id, fname), daemon=True).start()
            return "OK", 200

        if not is_admin and ("photo" in msg or text):
            st = load_store()
            u_info = st["tg_users"].get(str(chat_id), {})
            now_ts = int(time.time())
            is_tg_pro = u_info.get("pro_until", 0) > now_ts
            if is_tg_pro:
                rem_sec = u_info.get("pro_until", 0) - now_ts
                if 0 < rem_sec <= 3 * 86400 and not u_info.get("reminded"):
                    days_left = max(1, int(rem_sec // 86400))
                    sc = u_info.get("sheets_calc", 0)
                    ic = u_info.get("invoices_cnt", 0)
                    tg_send_msg(chat_id, f"⏳ تنبيه: اشتراكك ينتهي خلال {days_left} يوم!\n📊 أنجزت هذا الشهر: {sc} لوح و {ic} فاتورة.\nجدد اشتراكك الآن لضمان استمرار عمل ورشتك.")
                    u_info["reminded"] = True
                    save_store(st)
            else:
                if u_info.get("trial_used"):
                    tg_send_msg(chat_id, f"🔒 انتهت تجربتك المجانية!\nللاستمرار يرجى الاشتراك ({PRO_PRICE}) عبر الآيبان:\n{IBAN_INFO}\nثم أرسل كود التفعيل هكذا: `/activate الكود`")
                    return "OK", 200
                st["tg_users"][str(chat_id)] = {"trial_used": True, "pro_until": 0}
                save_store(st)

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
        for line in normalize_digits(pieces_text).splitlines():
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

        tg_send_msg(chat_id, build_cut_summary(groups))
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
