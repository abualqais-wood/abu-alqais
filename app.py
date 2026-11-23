<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>متر أبو القيس الذكي | Abu Al-Qais Smart Metre</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --accent: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --danger: #ef4444;
            --info: #38bdf8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
        body { background-color: var(--bg-dark); color: var(--text-main); overflow-x: hidden; user-select: none; }
        
        /* Header */
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 16px; background: var(--card-bg); border-bottom: 1px solid #334155;
            position: sticky; top: 0; z-index: 50;
        }
        .brand { font-size: 1.15rem; font-weight: 800; color: var(--accent); display: flex; align-items: center; gap: 8px; }
        .lang-btn {
            background: #334155; color: var(--text-main); border: none; padding: 6px 12px;
            border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem;
        }

        /* Main Layout */
        .container { max-width: 600px; margin: 0 auto; padding: 16px; }
        .card {
            background: var(--card-bg); border: 1px solid #334155; border-radius: 12px; padding: 18px;
            text-align: center; margin-bottom: 16px;
        }
        .btn-primary {
            width: 100%; padding: 15px; background: var(--accent); color: #000;
            border: none; border-radius: 12px; font-size: 1.05rem; font-weight: 900;
            cursor: pointer; margin-top: 12px; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.3);
        }
        .btn-heart {
            width: 100%; padding: 15px; background: linear-gradient(135deg, #e11d48, #0284c7); color: #fff;
            border: none; border-radius: 12px; font-size: 1.05rem; font-weight: 900;
            cursor: pointer; margin-top: 10px; box-shadow: 0 4px 14px rgba(225, 29, 72, 0.3);
        }

        /* ================= AR FULLSCREEN OVERLAY (NO OVERLAP LAYOUT) ================= */
        #ar-overlay {
            position: fixed; inset: 0; display: none; flex-direction: column;
            justify-content: space-between; padding: 12px; z-index: 9000;
            pointer-events: none;
        }
        #ar-overlay.active { display: flex; }

        /* Top Header + Mini Blueprint side-by-side inside a clean Flexbox row */
        .ar-top-container {
            display: flex; gap: 8px; align-items: stretch; width: 100%;
            pointer-events: auto;
        }
        .ar-top-bar {
            flex: 1; background: rgba(15, 23, 42, 0.92); padding: 10px; border-radius: 12px;
            text-align: center; border: 1px solid #475569;
            display: flex; flex-direction: column; justify-content: center;
        }
        .mini-plan-box {
            width: 106px; flex-shrink: 0;
            background: rgba(15, 23, 42, 0.92); border: 1px solid var(--info);
            border-radius: 12px; padding: 4px; display: flex; flex-direction: column;
            align-items: center; justify-content: center;
        }
        #mini-plan-canvas { width: 96px; height: 78px; display: block; }
        .mini-plan-label { font-size: 0.65rem; color: #cbd5e1; font-weight: 700; margin-top: 2px; }

        .status-pill {
            display: inline-block; padding: 3px 8px; border-radius: 16px; font-size: 0.74rem;
            font-weight: 700; margin-bottom: 4px; background: #7f1d1d; color: #fecaca;
        }
        .status-pill.ready { background: #064e3b; color: #a7f3d0; }
        .live-readout { font-size: 1.75rem; font-weight: 900; color: var(--accent); direction: ltr; line-height: 1.15; }
        .sub-readout { font-size: 0.85rem; color: var(--info); font-weight: 700; direction: ltr; margin-top: 2px; }

        /* Center Crosshair */
        .center-crosshair {
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            width: 52px; height: 52px; border: 3px solid var(--accent); border-radius: 50%;
            pointer-events: none; display: flex; align-items: center; justify-content: center;
            z-index: 9001;
        }
        .center-crosshair::before {
            content: ''; position: absolute; width: 64px; height: 2px; background: rgba(245, 158, 11, 0.45);
        }
        .center-crosshair::after {
            content: ''; position: absolute; height: 64px; width: 2px; background: rgba(245, 158, 11, 0.45);
        }
        .center-dot {
            width: 10px; height: 10px; background: #ef4444; border-radius: 50%; z-index: 2;
            border: 2px solid #fff;
        }
        .center-crosshair.locked {
            border-color: var(--success);
            box-shadow: 0 0 16px rgba(16, 185, 129, 0.85);
        }
        .center-crosshair.locked .center-dot { background: var(--success); }

        .ar-controls-wrap { display: flex; flex-direction: column; gap: 8px; pointer-events: auto; }
        .ar-main-btn {
            width: 100%; padding: 16px; border-radius: 12px; border: none;
            background: var(--accent); color: #000; font-size: 1.1rem; font-weight: 900;
            box-shadow: 0 4px 16px rgba(0,0,0,0.5); cursor: pointer;
        }
        .ar-sub-bar { display: flex; gap: 8px; }
        .ar-sub-bar button {
            flex: 1; padding: 13px 6px; border-radius: 10px; border: none;
            font-size: 0.88rem; font-weight: 800; cursor: pointer;
        }
        .btn-save { background: var(--success); color: #fff; }
        .btn-undo { background: #475569; color: #fff; }
        .btn-clear { background: var(--danger); color: #fff; }

        /* ================= HEART RATE & BREATHING OVERLAY ================= */
        #hr-overlay {
            position: fixed; inset: 0; background: #0f172a;
            display: none; flex-direction: column; justify-content: space-between;
            padding: 16px; z-index: 9000; text-align: center; overflow-y: auto;
        }
        #hr-overlay.active { display: flex; }
        .hr-video-box {
            position: relative; width: 104px; height: 104px; margin: 8px auto;
            border-radius: 50%; overflow: hidden; border: 4px solid #e11d48;
            box-shadow: 0 0 20px rgba(225, 29, 72, 0.5);
        }
        #hr-video { width: 100%; height: 100%; object-fit: cover; }

        .vitals-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 8px 0;
        }
        .vital-box {
            background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 10px;
        }
        .vital-box.heart { border-color: #e11d48; }
        .vital-box.breath { border-color: #38bdf8; }
        .bpm-display { font-size: 2.3rem; font-weight: 900; color: #fb7185; line-height: 1.1; }
        .rpm-display { font-size: 2.3rem; font-weight: 900; color: #38bdf8; line-height: 1.1; }
        .vital-unit { font-size: 0.76rem; color: var(--text-muted); font-weight: 700; margin-top: 3px; }

        #ecg-canvas {
            width: 100%; height: 100px; background: #020617; border-radius: 12px;
            border: 1px solid #334155; margin: 6px 0; display: block;
        }
        .progress-bar-bg {
            width: 100%; height: 10px; background: #334155; border-radius: 10px; overflow: hidden; margin: 6px 0;
        }
        .progress-bar-fill {
            height: 100%; width: 0%; background: linear-gradient(90deg, #e11d48, #38bdf8); transition: width 0.2s;
        }

        /* ================= SAVED RECORDS TABLE ================= */
        .list-section { background: var(--card-bg); border-radius: 12px; padding: 14px; border: 1px solid #334155; overflow-x: auto; }
        .list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
        th, td { padding: 10px 6px; text-align: center; border-bottom: 1px solid #334155; }
        th { color: var(--text-muted); font-weight: 600; }
        .badge-mm {
            display: inline-block; background: #334155; padding: 3px 7px; border-radius: 4px;
            font-family: monospace; font-size: 0.85rem; color: #38bdf8; word-break: break-word;
        }
        .copy-btn {
            background: var(--success); color: #fff; border: none; padding: 7px 12px;
            border-radius: 6px; font-weight: 700; font-size: 0.82rem; cursor: pointer; white-space: nowrap;
        }
        .blueprint-preview {
            background: #020617; border: 1px solid #334155; border-radius: 12px;
            padding: 12px; text-align: center; display: none; margin-bottom: 16px;
        }
        #full-plan-canvas { width: 100%; max-width: 340px; height: 220px; margin: 0 auto; display: block; }

        /* Non-overlapping Toast Notification */
        .toast {
            position: fixed; bottom: 135px; left: 50%; transform: translateX(-50%);
            background: rgba(15, 23, 42, 0.96); color: #fff; border: 1px solid var(--accent);
            padding: 9px 16px; border-radius: 8px; font-size: 0.86rem; font-weight: 700;
            z-index: 10000; display: none; text-align: center; width: 85%; max-width: 340px;
            pointer-events: none; box-shadow: 0 4px 12px rgba(0,0,0,0.6);
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>

<div id="toast" class="toast"></div>

<header>
    <div class="brand">📐 <span data-i18n="title">متر أبو القيس الذكي</span></div>
    <button class="lang-btn" onclick="toggleLang()" id="langBtn">Türkçe</button>
</header>

<div class="container">
    <div class="card">
        <h3 data-i18n="arTitle">قياس شامل ورسم مخطط فوري (3D AR)</h3>
        <p style="font-size:0.86rem; color:var(--text-muted); margin-top:6px; line-height:1.5;" data-i18n="arDesc">
            يقيس كل شيء (ارتفاع شجرة أو إنسان، عرض طريق، غرف، ألواح) مع تثبيت النقاط ضد الاهتزاز ورسم مخطط هندسي حي.
        </p>
        <button class="btn-primary" onclick="startAR()" data-i18n="btnAr">📷 ابدأ القياس ورسم المخطط</button>
        <button class="btn-heart" onclick="startHeartRate()" data-i18n="btnHr">❤️🫁 قياس نبضات القلب ومعدل التنفس</button>
    </div>

    <!-- Full Blueprint Preview Card -->
    <div class="blueprint-preview" id="blueprint-card">
        <h4 style="color:var(--info); margin-bottom:8px;" data-i18n="lastBlueprint">آخر مخطط هندسي تم رسمه</h4>
        <canvas id="full-plan-canvas" width="340" height="220"></canvas>
    </div>

    <div class="list-section">
        <div class="list-header">
            <h4 data-i18n="savedList">سجل القياسات والنبض والتنفس</h4>
            <button class="copy-btn" onclick="copyAllMeasurements()" data-i18n="copyOpt">📋 نسخ الكل</button>
        </div>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th data-i18n="colType">النوع</th>
                    <th data-i18n="colVal">القيمة</th>
                    <th data-i18n="colArea">التفاصيل</th>
                </tr>
            </thead>
            <tbody id="cut-list-body">
                <tr><td colspan="4" style="color:#64748b;" data-i18n="noItems">لا توجد قياسات محفوظة بعد</td></tr>
            </tbody>
        </table>
    </div>
</div>

<!-- Heart Rate & Breathing Rate Overlay -->
<div id="hr-overlay">
    <div>
        <h3 style="color:#fb7185; margin-bottom:4px;" data-i18n="hrTitle">❤️🫁 قياس النبض ومعدل التنفس</h3>
        <p style="font-size:0.82rem; color:#cbd5e1;" data-i18n="hrDesc">
            ضع طرف إصبعك برفق على الكاميرا الخلفية والفلاش وتنفس بشكل طبيعي لمدة 15 ثانية.
        </p>
    </div>

    <div>
        <div class="hr-video-box">
            <video id="hr-video" playsinline muted></video>
        </div>
        <div id="hr-finger-status" style="font-size:0.88rem; font-weight:800; color:#f59e0b; margin-bottom:6px;" data-i18n="placeFinger">
            👆 ضع إصبعك على الكاميرا الخلفية...
        </div>

        <div class="vitals-grid">
            <div class="vital-box heart">
                <div class="bpm-display" id="bpm-val">--</div>
                <div class="vital-unit" data-i18n="bpmLabel">❤️ نبضة / دقيقة (BPM)</div>
            </div>
            <div class="vital-box breath">
                <div class="rpm-display" id="rpm-val">--</div>
                <div class="vital-unit" data-i18n="rpmLabel">🫁 نفس / دقيقة (RPM)</div>
            </div>
        </div>

        <div class="progress-bar-bg"><div class="progress-bar-fill" id="hr-progress"></div></div>
        <canvas id="ecg-canvas" width="340" height="100"></canvas>
    </div>

    <div class="ar-sub-bar">
        <button class="btn-save" onclick="saveVitalsRecord()" data-i18n="saveHrBtn">💾 حفظ النتيجة</button>
        <button class="btn-clear" onclick="stopHeartRate()" data-i18n="exitBtn">✖ خروج</button>
    </div>
</div>

<!-- WebXR AR Overlay (Clean Non-Overlapping Flexbox) -->
<div id="ar-overlay">
    <div class="center-crosshair" id="crosshair"><div class="center-dot"></div></div>

    <div class="ar-top-container">
        <div class="ar-top-bar">
            <div class="status-pill" id="surface-status" data-i18n="scanning">⚠️ حرّك الهاتف ببطء لمسح المكان</div>
            <div class="live-readout" id="ar-readout">0.00 m</div>
            <div class="sub-readout" id="ar-sub-readout">0 cm | 0 mm</div>
        </div>

        <div class="mini-plan-box">
            <canvas id="mini-plan-canvas" width="96" height="78"></canvas>
            <div class="mini-plan-label" data-i18n="livePlan">المخطط الحي</div>
        </div>
    </div>

    <div class="ar-controls-wrap">
        <button class="ar-main-btn" onclick="arPlacePoint()" data-i18n="pinBtn">📍 ثبّت زاوية / نقطة</button>
        <div class="ar-sub-bar">
            <button class="btn-save" onclick="finishAndSaveShape()" data-i18n="saveBtn">✅ إنهاء وحفظ المخطط</button>
            <button class="btn-undo" onclick="undoLastPoint()" data-i18n="undoBtn">↩ تراجع</button>
            <button class="btn-clear" onclick="stopAR()" data-i18n="exitBtn">✖ خروج</button>
        </div>
    </div>
</div>

<script>
const i18n = {
    ar: {
        title: "متر أبو القيس الذكي",
        arTitle: "قياس شامل ورسم مخطط فوري (3D AR)",
        arDesc: "يقيس كل شيء (ارتفاع شجرة أو إنسان، عرض طريق، غرف، ألواح) مع تثبيت النقاط ضد الاهتزاز ورسم مخطط هندسي حي.",
        btnAr: "📷 ابدأ القياس ورسم المخطط",
        btnHr: "❤️🫁 قياس نبضات القلب ومعدل التنفس",
        lastBlueprint: "آخر مخطط هندسي تم رسمه",
        savedList: "سجل القياسات والنبض والتنفس",
        copyOpt: "📋 نسخ الكل",
        colType: "النوع",
        colVal: "القيمة",
        colArea: "التفاصيل",
        noItems: "لا توجد قياسات محفوظة بعد",
        livePlan: "المخطط الحي",
        scanning: "⚠️ حرّك الهاتف ببطء لمسح المحيط",
        surfaceReady: "✅ الهدف مقفل بثبات",
        pinBtn: "📍 ثبّت زاوية / نقطة",
        saveBtn: "✅ حفظ المخطط",
        undoBtn: "↩ تراجع",
        exitBtn: "✖ خروج",
        needTarget: "وجّه الدائرة نحو الأرض أو الجدار وحرّك الهاتف قليلاً حتى تصبح خضراء.",
        pointPinned: "تم تثبيت الزاوية",
        savedToast: "تم الحفظ في السجل بنجاح ✅",
        nothingToSave: "لا يوجد قياس مكتمل للحفظ!",
        copied: "تم نسخ جميع القياسات!",
        hrTitle: "❤️🫁 قياس النبض ومعدل التنفس",
        hrDesc: "ضع طرف إصبعك برفق على الكاميرا الخلفية والفلاش وتنفس بشكل طبيعي لمدة 15 ثانية.",
        placeFinger: "👆 ضع إصبعك على الكاميرا الخلفية...",
        measuringFinger: "💓 جاري رصد النبض والتنفس... أبقِ إصبعك ثابتاً",
        doneFinger: "✅ اكتمل القياس! يمكنك حفظ النتيجة",
        bpmLabel: "❤️ نبضة / دقيقة (BPM)",
        rpmLabel: "🫁 نفس / دقيقة (RPM)",
        saveHrBtn: "💾 حفظ النتيجة"
    },
    tr: {
        title: "Ebu El-Kays Akıllı Metre",
        arTitle: "Genel Ölçüm ve Canlı Plan Çizimi (3D AR)",
        arDesc: "Her şeyi ölçer (ağaç/insan boyu, yol genişliği, oda, ahşap) ve titreşimsiz canlı plan çizer.",
        btnAr: "📷 Ölçüm ve Plan Çizimini Başlat",
        btnHr: "❤️🫁 Kalp Atışı ve Solunum Hızı Ölçümü",
        lastBlueprint: "Son Çizilen Mühendislik Planı",
        savedList: "Ölçüm, Nabız ve Solunum Kayıtları",
        copyOpt: "📋 Tümünü Kopyala",
        colType: "Tür",
        colVal: "Değer",
        colArea: "Detay",
        noItems: "Henüz kayıtlı ölçüm yok",
        livePlan: "Canlı Plan",
        scanning: "⚠️ Yüzeyi taramak için yavaşça gezdirin",
        surfaceReady: "✅ Hedef kilitlendi",
        pinBtn: "📍 Köşe / Nokta Sabitle",
        saveBtn: "✅ Planı Kaydet",
        undoBtn: "↩ Geri Al",
        exitBtn: "✖ Çıkış",
        needTarget: "Halkayı zemine veya duvara tutun ve yeşile dönene kadar hafifçe hareket ettirin.",
        pointPinned: "Köşe sabitlendi",
        savedToast: "Kayıt başarıyla eklendi ✅",
        nothingToSave: "Kaydedilecek tamamlanmış ölçüm yok!",
        copied: "Tüm ölçüler kopyalandı!",
        hrTitle: "❤️🫁 Nabız ve Solunum Hızı Ölçümü",
        hrDesc: "Parmağınızın ucunu arka kameraya ve flaşa hafifçe koyun ve 15 saniye normal nefes alın.",
        placeFinger: "👆 Parmağınızı arka kameraya koyun...",
        measuringFinger: "💓 Nabız ve nefes ölçülüyor... Sabit tutun",
        doneFinger: "✅ Ölçüm tamamlandı! Sonucu kaydedebilirsiniz",
        bpmLabel: "❤️ Nabız / Dk (BPM)",
        rpmLabel: "🫁 Nefes / Dk (RPM)",
        saveHrBtn: "💾 Sonucu Kaydet"
    }
};

let currentLang = 'ar';
let savedRecords = [];

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.display = 'block';
    clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => { t.style.display = 'none'; }, 2200);
}

function toggleLang() {
    currentLang = currentLang === 'ar' ? 'tr' : 'ar';
    document.documentElement.lang = currentLang;
    document.documentElement.dir = currentLang === 'ar' ? 'rtl' : 'ltr';
    document.getElementById('langBtn').textContent = currentLang === 'ar' ? 'Türkçe' : 'العربية';
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (i18n[currentLang][key]) el.textContent = i18n[currentLang][key];
    });
}

/* ================= HEART RATE & BREATHING RATE ENGINE ================= */
let hrStream = null;
let hrAnimId = null;
let hrSamples = [];
let hrTimestamps = [];
let currentBpm = 0;
let currentRpm = 0;
let ecgPoints = [];
let breathWavePoints = [];

async function startHeartRate() {
    if (xrSession) {
        await stopAR();
    }
    try {
        hrStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 128 }, height: { ideal: 128 } }
        });
    } catch (err) {
        showToast("يرجى السماح بصلاحية الكاميرا لقياس النبض والتنفس");
        return;
    }

    const overlay = document.getElementById('hr-overlay');
    overlay.classList.add('active');
    const video = document.getElementById('hr-video');
    video.srcObject = hrStream;
    await video.play();

    const track = hrStream.getVideoTracks()[0];
    try {
        const caps = track.getCapabilities();
        if (caps.torch) {
            await track.applyConstraints({ advanced: [{ torch: true }] });
        }
    } catch (e) {}

    hrSamples = [];
    hrTimestamps = [];
    ecgPoints = [];
    breathWavePoints = [];
    currentBpm = 0;
    currentRpm = 0;
    document.getElementById('bpm-val').textContent = "--";
    document.getElementById('rpm-val').textContent = "--";
    document.getElementById('hr-progress').style.width = "0%";

    const offCanvas = document.createElement('canvas');
    offCanvas.width = 40;
    offCanvas.height = 40;
    const offCtx = offCanvas.getContext('2d', { willReadFrequently: true });

    const ecgCanvas = document.getElementById('ecg-canvas');
    const ecgCtx = ecgCanvas.getContext('2d');
    const statusEl = document.getElementById('hr-finger-status');

    function processFrame() {
        if (!hrStream) return;
        offCtx.drawImage(video, 0, 0, 40, 40);
        const frameData = offCtx.getImageData(0, 0, 40, 40).data;

        let redSum = 0, greenSum = 0, blueSum = 0;
        const pixelCount = frameData.length / 4;
        for (let i = 0; i < frameData.length; i += 4) {
            redSum += frameData[i];
            greenSum += frameData[i + 1];
            blueSum += frameData[i + 2];
        }
        const avgR = redSum / pixelCount;
        const avgG = greenSum / pixelCount;
        const avgB = blueSum / pixelCount;

        const fingerPresent = (avgR > 140 && avgR > (avgG + avgB) * 1.15);

        if (!fingerPresent) {
            statusEl.textContent = i18n[currentLang].placeFinger;
            statusEl.style.color = "#f59e0b";
            hrSamples = [];
            hrTimestamps = [];
            breathWavePoints = [];
            document.getElementById('hr-progress').style.width = "0%";
        } else {
            const now = performance.now();
            hrSamples.push(avgR);
            hrTimestamps.push(now);

            while (hrTimestamps.length > 0 && now - hrTimestamps[0] > 18000) {
                hrTimestamps.shift();
                hrSamples.shift();
            }

            const durationSec = (now - hrTimestamps[0]) / 1000;
            const pct = Math.min(100, Math.round((durationSec / 15) * 100));
            document.getElementById('hr-progress').style.width = pct + "%";

            if (pct >= 100) {
                statusEl.textContent = i18n[currentLang].doneFinger;
                statusEl.style.color = "#10b981";
            } else {
                statusEl.textContent = i18n[currentLang].measuringFinger;
                statusEl.style.color = "#fb7185";
            }

            if (hrSamples.length > 15) {
                const win = 10;
                const pulseSignal = [];
                for (let i = win; i < hrSamples.length; i++) {
                    let localMean = 0;
                    for (let j = i - win; j < i; j++) localMean += hrSamples[j];
                    localMean /= win;
                    pulseSignal.push(hrSamples[i] - localMean);
                }

                ecgPoints.push(pulseSignal[pulseSignal.length - 1]);
                if (ecgPoints.length > 120) ecgPoints.shift();

                if (durationSec >= 3.0) {
                    let peaks = [];
                    let maxAmp = Math.max(...pulseSignal.map(Math.abs), 0.2);
                    const threshold = maxAmp * 0.35;

                    for (let i = 2; i < pulseSignal.length - 2; i++) {
                        if (pulseSignal[i] > threshold &&
                            pulseSignal[i] > pulseSignal[i - 1] &&
                            pulseSignal[i] >= pulseSignal[i + 1]) {
                            const tPeak = hrTimestamps[i + win];
                            if (peaks.length === 0 || tPeak - peaks[peaks.length - 1] > 330) {
                                peaks.push(tPeak);
                            }
                        }
                    }

                    if (peaks.length >= 2) {
                        const spanMs = peaks[peaks.length - 1] - peaks[0];
                        const bpm = Math.round(((peaks.length - 1) * 60000) / spanMs);
                        if (bpm >= 45 && bpm <= 185) {
                            currentBpm = currentBpm === 0 ? bpm : Math.round(currentBpm * 0.7 + bpm * 0.3);
                            document.getElementById('bpm-val').textContent = currentBpm;
                        }
                    }
                }
            }

            if (hrSamples.length > 50) {
                const fastWin = 20;
                const slowWin = 90;
                const respSignal = [];
                const respTimes = [];

                for (let i = slowWin; i < hrSamples.length; i++) {
                    let fastAvg = 0;
                    for (let j = i - fastWin; j < i; j++) fastAvg += hrSamples[j];
                    fastAvg /= fastWin;

                    let slowAvg = 0;
                    for (let j = i - slowWin; j < i; j++) slowAvg += hrSamples[j];
                    slowAvg /= slowWin;

                    respSignal.push(fastAvg - slowAvg);
                    respTimes.push(hrTimestamps[i]);
                }

                if (respSignal.length > 0) {
                    breathWavePoints.push(respSignal[respSignal.length - 1]);
                    if (breathWavePoints.length > 120) breathWavePoints.shift();
                }

                if (durationSec >= 6.0 && respSignal.length > 20) {
                    let breathPeaks = [];
                    let maxResp = Math.max(...respSignal.map(Math.abs), 0.05);
                    const respThresh = maxResp * 0.25;

                    for (let i = 3; i < respSignal.length - 3; i++) {
                        if (respSignal[i] > respThresh &&
                            respSignal[i] > respSignal[i - 1] &&
                            respSignal[i] >= respSignal[i + 1]) {
                            const tBreath = respTimes[i];
                            if (breathPeaks.length === 0 || tBreath - breathPeaks[breathPeaks.length - 1] > 2000) {
                                breathPeaks.push(tBreath);
                            }
                        }
                    }

                    if (breathPeaks.length >= 2) {
                        const bSpanMs = breathPeaks[breathPeaks.length - 1] - breathPeaks[0];
                        const rpm = Math.round(((breathPeaks.length - 1) * 60000) / bSpanMs);
                        if (rpm >= 8 && rpm <= 32) {
                            currentRpm = currentRpm === 0 ? rpm : Math.round(currentRpm * 0.75 + rpm * 0.25);
                            document.getElementById('rpm-val').textContent = currentRpm;
                        }
                    }
                }
            }
        }

        ecgCtx.clearRect(0, 0, ecgCanvas.width, ecgCanvas.height);
        ecgCtx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
        ecgCtx.lineWidth = 1;
        for (let x = 0; x < ecgCanvas.width; x += 20) { ecgCtx.beginPath(); ecgCtx.moveTo(x, 0); ecgCtx.lineTo(x, ecgCanvas.height); ecgCtx.stroke(); }

        if (breathWavePoints.length > 2) {
            const maxB = Math.max(...breathWavePoints.map(Math.abs), 0.1);
            ecgCtx.strokeStyle = 'rgba(56, 189, 248, 0.75)';
            ecgCtx.lineWidth = 2;
            ecgCtx.beginPath();
            breathWavePoints.forEach((val, idx) => {
                const x = (idx / 120) * ecgCanvas.width;
                const y = (ecgCanvas.height / 2) - (val / maxB) * (ecgCanvas.height * 0.35);
                if (idx === 0) ecgCtx.moveTo(x, y);
                else ecgCtx.lineTo(x, y);
            });
            ecgCtx.stroke();
        }

        if (ecgPoints.length > 2) {
            const maxEcg = Math.max(...ecgPoints.map(Math.abs), 0.5);
            ecgCtx.strokeStyle = '#fb7185';
            ecgCtx.lineWidth = 2.5;
            ecgCtx.beginPath();
            ecgPoints.forEach((val, idx) => {
                const x = (idx / 120) * ecgCanvas.width;
                const y = (ecgCanvas.height / 2) - (val / maxEcg) * (ecgCanvas.height * 0.38);
                if (idx === 0) ecgCtx.moveTo(x, y);
                else ecgCtx.lineTo(x, y);
            });
            ecgCtx.stroke();
        }

        hrAnimId = requestAnimationFrame(processFrame);
    }

    hrAnimId = requestAnimationFrame(processFrame);
}

function saveVitalsRecord() {
    if (currentBpm <= 0) {
        showToast(i18n[currentLang].nothingToSave);
        return;
    }
    const hrStatus = currentBpm < 60 ? 'نبض بطيء' : (currentBpm <= 100 ? 'نبض طبيعي' : 'نبض سريع');
    const respText = currentRpm > 0 ? ` | 🫁 ${currentRpm} RPM` : '';
    const respStatus = currentRpm > 0 ? (currentRpm >= 12 && currentRpm <= 20 ? ' (تنفس طبيعي ✅)' : ' (تنفس غير منتظم)') : '';

    savedRecords.push({
        type: '❤️🫁 مؤشرات حيوية',
        dims: `${currentBpm} BPM${respText}`,
        summary: `${hrStatus}${respStatus}`
    });
    renderTable();
    showToast(i18n[currentLang].savedToast);
    stopHeartRate();
}

function stopHeartRate() {
    if (hrAnimId) cancelAnimationFrame(hrAnimId);
    if (hrStream) {
        hrStream.getTracks().forEach(t => t.stop());
        hrStream = null;
    }
    document.getElementById('hr-overlay').classList.remove('active');
}

/* ================= STABILIZED WEBXR AR & BLUEPRINT ENGINE ================= */
let smoothedPos = new THREE.Vector3();
let hasSmoothedInit = false;
const SMOOTHING_FACTOR = 0.22;

let pinnedPoints = [];
let segmentDistancesM = [];
let currentLiveDistM = 0;

function formatDist(meters) {
    const cm = (meters * 100).toFixed(1);
    const mm = Math.round(meters * 1000);
    return { main: `${meters.toFixed(2)} m`, sub: `${cm} cm | ${mm} mm` };
}

function drawBlueprint(canvasId, points3D, liveCursor3D = null) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    ctx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 20) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 20) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    const allPts = [...points3D];
    if (liveCursor3D && points3D.length > 0) allPts.push(liveCursor3D);
    if (allPts.length === 0) return;

    let minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;
    allPts.forEach(p => {
        if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
        if (p.z < minZ) minZ = p.z; if (p.z > maxZ) maxZ = p.z;
    });

    const useVerticalElevation = (maxY - minY) > (maxZ - minZ) * 1.5;
    const pts2D = allPts.map(p => ({ u: p.x, v: useVerticalElevation ? -p.y : p.z }));

    let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
    pts2D.forEach(p => {
        if (p.u < minU) minU = p.u; if (p.u > maxU) maxU = p.u;
        if (p.v < minV) minV = p.v; if (p.v > maxV) maxV = p.v;
    });

    const rangeU = Math.max(maxU - minU, 0.1);
    const rangeV = Math.max(maxV - minV, 0.1);
    const pad = 20;
    const scale = Math.min((W - pad * 2) / rangeU, (H - pad * 2) / rangeV);

    const cx = W / 2 - ((minU + maxU) / 2) * scale;
    const cy = H / 2 - ((minV + maxV) / 2) * scale;
    const mapped = pts2D.map(p => ({ x: cx + p.u * scale, y: cy + p.v * scale }));

    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    mapped.forEach((m, idx) => {
        if (idx === 0) ctx.moveTo(m.x, m.y);
        else ctx.lineTo(m.x, m.y);
    });
    ctx.stroke();

    ctx.font = 'bold 10px monospace';
    ctx.textAlign = 'center';
    mapped.forEach((m, idx) => {
        ctx.fillStyle = (liveCursor3D && idx === mapped.length - 1) ? '#f59e0b' : '#38bdf8';
        ctx.beginPath();
        ctx.arc(m.x, m.y, 3.5, 0, Math.PI * 2);
        ctx.fill();

        if (idx > 0) {
            const prev = mapped[idx - 1];
            const distM = allPts[idx].distanceTo(allPts[idx - 1]);
            ctx.fillStyle = '#f8fafc';
            ctx.fillText(`${distM.toFixed(2)}m`, (prev.x + m.x) / 2, (prev.y + m.y) / 2 - 5);
        }
    });
}

let xrSession = null, xrRefSpace = null, hitTestSource = null;
let arScene, arCamera, arRenderer, arReticle;
let arMeshes = [];
let liveLine3D = null;
let surfaceLocked = false;

async function startAR() {
    if (hrStream) {
        stopHeartRate();
    }
    if (!navigator.xr) { showToast("WebXR غير مدعوم في هذا المتصفح"); return; }
    const supported = await navigator.xr.isSessionSupported('immersive-ar');
    if (!supported) { showToast("تأكد من فتح الرابط عبر HTTPS في Chrome"); return; }

    const overlay = document.getElementById('ar-overlay');
    overlay.classList.add('active');
    pinnedPoints = [];
    segmentDistancesM = [];
    arMeshes = [];
    hasSmoothedInit = false;
    surfaceLocked = false;
    drawBlueprint('mini-plan-canvas', []);

    xrSession = await navigator.xr.requestSession('immersive-ar', {
        requiredFeatures: ['hit-test'],
        optionalFeatures: ['dom-overlay'],
        domOverlay: { root: overlay }
    });

    const glCanvas = document.createElement('canvas');
    const gl = glCanvas.getContext('webgl', { xrCompatible: true });

    arRenderer = new THREE.WebGLRenderer({ canvas: glCanvas, context: gl, alpha: true, antialias: true });
    arRenderer.autoClear = false;
    arRenderer.xr.enabled = true;
    arRenderer.xr.setReferenceSpaceType('local');
    await arRenderer.xr.setSession(xrSession);

    arScene = new THREE.Scene();
    arCamera = new THREE.PerspectiveCamera();

    const ringGeo = new THREE.RingGeometry(0.02, 0.036, 32).rotateX(-Math.PI / 2);
    arReticle = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0x10b981, side: THREE.DoubleSide }));
    arReticle.visible = false;
    arScene.add(arReticle);

    const viewerSpace = await xrSession.requestReferenceSpace('viewer');
    hitTestSource = await xrSession.requestHitTestSource({ space: viewerSpace });
    xrRefSpace = await xrSession.requestReferenceSpace('local');

    xrSession.addEventListener('end', () => {
        overlay.classList.remove('active');
        xrSession = null;
    });

    const statusPill = document.getElementById('surface-status');
    const crosshair = document.getElementById('crosshair');

    arRenderer.setAnimationLoop((timestamp, frame) => {
        if (!frame) return;
        const hitTestResults = frame.getHitTestResults(hitTestSource);
        if (hitTestResults.length > 0) {
            const pose = hitTestResults[0].getPose(xrRefSpace);
            const rawPos = new THREE.Vector3().setFromMatrixPosition(new THREE.Matrix4().fromArray(pose.transform.matrix));

            if (!hasSmoothedInit) {
                smoothedPos.copy(rawPos);
                hasSmoothedInit = true;
            } else if (smoothedPos.distanceTo(rawPos) > 0.0015) {
                smoothedPos.lerp(rawPos, SMOOTHING_FACTOR);
            }

            arReticle.visible = true;
            arReticle.position.copy(smoothedPos);

            if (!surfaceLocked) {
                surfaceLocked = true;
                statusPill.textContent = i18n[currentLang].surfaceReady;
                statusPill.classList.add('ready');
                crosshair.classList.add('locked');
            }

            if (pinnedPoints.length > 0) {
                const lastPt = pinnedPoints[pinnedPoints.length - 1];
                currentLiveDistM = lastPt.distanceTo(smoothedPos);
                const fmt = formatDist(currentLiveDistM);
                document.getElementById('ar-readout').textContent = fmt.main;
                document.getElementById('ar-sub-readout').textContent = fmt.sub;

                updateLive3DLine(lastPt, smoothedPos);
                drawBlueprint('mini-plan-canvas', pinnedPoints, smoothedPos);
            }
        } else {
            arReticle.visible = false;
            if (surfaceLocked) {
                surfaceLocked = false;
                statusPill.textContent = i18n[currentLang].scanning;
                statusPill.classList.remove('ready');
                crosshair.classList.remove('locked');
            }
        }
        arRenderer.render(arScene, arCamera);
    });
}

function updateLive3DLine(p1, p2) {
    if (liveLine3D) arScene.remove(liveLine3D);
    const geo = new THREE.BufferGeometry().setFromPoints([p1, p2]);
    liveLine3D = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 5 }));
    arScene.add(liveLine3D);
}

function arPlacePoint() {
    if (!surfaceLocked || !hasSmoothedInit) {
        showToast(i18n[currentLang].needTarget);
        return;
    }

    const pt = smoothedPos.clone();
    if (pinnedPoints.length >= 3 && pt.distanceTo(pinnedPoints[0]) < 0.08) {
        pt.copy(pinnedPoints[0]);
    }

    const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.015, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x38bdf8 })
    );
    sphere.position.copy(pt);
    arScene.add(sphere);
    arMeshes.push(sphere);

    if (pinnedPoints.length > 0) {
        const prev = pinnedPoints[pinnedPoints.length - 1];
        const dist = prev.distanceTo(pt);
        segmentDistancesM.push(dist);

        const lineGeo = new THREE.BufferGeometry().setFromPoints([prev, pt]);
        const solidLine = new THREE.Line(lineGeo, new THREE.LineBasicMaterial({ color: 0x10b981, linewidth: 5 }));
        arScene.add(solidLine);
        arMeshes.push(solidLine);
    }

    pinnedPoints.push(pt);
    drawBlueprint('mini-plan-canvas', pinnedPoints);
    showToast(`${i18n[currentLang].pointPinned} (${pinnedPoints.length})`);
}

function undoLastPoint() {
    if (pinnedPoints.length === 0) return;
    pinnedPoints.pop();
    if (segmentDistancesM.length > 0) segmentDistancesM.pop();

    const m1 = arMeshes.pop(); if (m1) arScene.remove(m1);
    if (pinnedPoints.length > 0) {
        const m2 = arMeshes.pop(); if (m2) arScene.remove(m2);
    }
    if (liveLine3D && pinnedPoints.length === 0) {
        arScene.remove(liveLine3D);
        liveLine3D = null;
        document.getElementById('ar-readout').textContent = "0.00 m";
        document.getElementById('ar-sub-readout').textContent = "0 cm | 0 mm";
    }
    drawBlueprint('mini-plan-canvas', pinnedPoints);
}

function finishAndSaveShape() {
    if (segmentDistancesM.length === 0) {
        showToast(i18n[currentLang].nothingToSave);
        return;
    }

    const totalPerimeterM = segmentDistancesM.reduce((a, b) => a + b, 0);
    const dimsStr = segmentDistancesM.map(d => `${d.toFixed(2)}m (${Math.round(d*1000)}mm)`).join(' × ');

    let areaText = `${totalPerimeterM.toFixed(2)} m`;
    if (pinnedPoints.length >= 3) {
        let area = 0;
        for (let i = 0; i < pinnedPoints.length; i++) {
            const j = (i + 1) % pinnedPoints.length;
            area += pinnedPoints[i].x * pinnedPoints[j].z;
            area -= pinnedPoints[j].x * pinnedPoints[i].z;
        }
        area = Math.abs(area) / 2;
        if (area > 0.01) areaText += ` | ${area.toFixed(2)} m²`;
    }

    savedRecords.push({
        type: pinnedPoints.length === 2 ? '📐 خط / ارتفاع' : `📐 مخطط (${pinnedPoints.length} زوايا)`,
        dims: dimsStr,
        summary: areaText
    });

    document.getElementById('blueprint-card').style.display = 'block';
    drawBlueprint('full-plan-canvas', [...pinnedPoints]);

    renderTable();
    showToast(i18n[currentLang].savedToast);

    pinnedPoints = [];
    segmentDistancesM = [];
    if (liveLine3D) { arScene.remove(liveLine3D); liveLine3D = null; }
    document.getElementById('ar-readout').textContent = "0.00 m";
    document.getElementById('ar-sub-readout').textContent = "0 cm | 0 mm";
    drawBlueprint('mini-plan-canvas', []);
}

function renderTable() {
    const tbody = document.getElementById('cut-list-body');
    if (savedRecords.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="color:#64748b;">${i18n[currentLang].noItems}</td></tr>`;
        return;
    }
    tbody.innerHTML = savedRecords.map((item, idx) => `
        <tr>
            <td>${idx + 1}</td>
            <td>${item.type}</td>
            <td><span class="badge-mm">${item.dims}</span></td>
            <td>${item.summary}</td>
        </tr>
    `).join('');
}

function copyAllMeasurements() {
    if (savedRecords.length === 0) return;
    const text = savedRecords.map((r, i) => `${i + 1}. ${r.type}: ${r.dims} -> ${r.summary}`).join('\n');
    navigator.clipboard.writeText(text).then(() => showToast(i18n[currentLang].copied));
}

async function stopAR() {
    if (xrSession) {
        await xrSession.end();
        xrSession = null;
    }
    document.getElementById('ar-overlay').classList.remove('active');
}
</script>
</body>
</html>
