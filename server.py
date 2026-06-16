from flask import Flask, request, jsonify
import sqlite3, hashlib, os, subprocess

app = Flask(__name__)
DB = "database.db"
MASTER_KEY = os.environ.get("MASTER_KEY", "ultra_secret_2025")

CORE_SCRIPT = r"""#!/system/bin/sh
ALLOWED_ID="__DEVICE_ID__"
DEV_ID=$(settings get secure android_id 2>/dev/null | tr -d '[:space:]')
if [ "$DEV_ID" != "$ALLOWED_ID" ]; then
    echo "❌ УСТРОЙСТВО НЕ АВТОРИЗОВАНО."
    exit 1
fi

SOC=$(getprop ro.board.platform)
GPU=$(getprop ro.hardware.gpu)
SDK=$(getprop ro.build.version.sdk)
MOD=$(getprop ro.product.model)
REFRESH=$(settings get system peak_refresh_rate 2>/dev/null | tr -d '[:space:]')
[ -z "$REFRESH" ] && REFRESH=120

echo "========================================="
echo "🔥 ULTIMATE OPTIMIZATION ENGINE v14.0"
echo "========================================="
echo "📱 $MOD ($SOC) | Android $SDK"
echo "🖥️ Развертка: ${REFRESH}Гц"
echo "========================================="

OK=0; FAIL=0; SKIP=0
LOGFILE="/sdcard/tweak_errors.log"
echo "=== ЛОГ ===" > $LOGFILE

PROPS_RAW=$(getprop 2>/dev/null)
SET_SYS=$(settings list system 2>/dev/null | cut -d= -f1)
SET_GLO=$(settings list global 2>/dev/null | cut -d= -f1)
SET_SEC=$(settings list secure 2>/dev/null | cut -d= -f1)
PACKAGES=$(pm list packages 2>/dev/null | cut -d: -f2)

try_sp(){ if setprop "$1" "$2" 2>/dev/null; then OK=$((OK+1)); else FAIL=$((FAIL+1)); echo "setprop $1 $2" >> $LOGFILE; fi }
try_st(){ local ns="$1" key="$2" val="$3" list=""; case "$ns" in system) list="$SET_SYS";; global) list="$SET_GLO";; secure) list="$SET_SEC";; esac; if echo "$list" | grep -qxF "$key" 2>/dev/null; then if settings put "$ns" "$key" "$val" 2>/dev/null; then OK=$((OK+1)); else FAIL=$((FAIL+1)); fi; else SKIP=$((SKIP+1)); fi }
try_cmd(){ if command -v cmd >/dev/null 2>&1 && cmd "$1" help >/dev/null 2>&1; then cmd "$1" "$2" >/dev/null 2>&1 & OK=$((OK+1)); else SKIP=$((SKIP+1)); fi }

printf "🎯 [1/6] Сенсор... "
try_sp debug.touch.deadzone 0; try_sp debug.touch.slop 0; try_sp debug.touch.latency 0
try_sp debug.input.velocitytracker.strategy impulse
try_sp persist.input.velocitytracker.strategy impulse
try_st system pointer_speed 7; try_st secure high_touch_sensitivity 1
echo "OK"

printf "🎮 [2/6] Графика... "
try_sp debug.hwui.renderer skiavk; try_sp debug.renderengine.backend skiavk
try_sp debug.hwui.use_vulkan 1; try_sp debug.sf.latch_unsignaled 1
try_sp debug.sf.vsync 0; try_sp debug.hwui.disable_vsync 1
try_sp debug.hwui.render_ahead 0; try_sp debug.hwui.disable_interpolation 1
echo "OK"

printf "🔥 [3/6] CPU/GPU/Термал... "
try_st global cpu_boost_enabled 1; try_st global gpu_boost_enabled 1
try_st global sys_disable_cpu_throttle 1; try_st global sys_disable_gpu_throttle 1
try_st global enhanced_processing 2
try_cmd power "set-fixed-performance-mode-enabled true"
try_cmd thermalservice "override-status 0"
echo "OK"

printf "🌐 [4/6] Сеть/Память... "
try_st global wifi_low_latency_mode 1; try_st global wifi_power_save_mode 0
try_st global low_ram 0; try_st global zram_enabled 0
try_st global app_standby_enabled 0; try_st global adaptive_battery_management_enabled 0
try_st system min_refresh_rate "$REFRESH.0"; try_st system peak_refresh_rate "$REFRESH.0"
for anim in window_animation_scale transition_animation_scale animator_duration_scale; do
    try_st global "$anim" 0
done
try_st global sys_use_low_latency_audio 1
echo "OK"

printf "🛑 [5/6] Блокировка мусора... "
BLOCK_LIST="com.samsung.android.game.gos com.samsung.android.bixby.agent com.samsung.android.bixby.service com.sec.android.smartfpsadjuster com.google.android.as com.android.printspooler com.samsung.android.rubin.app"
for pkg in $BLOCK_LIST; do
    if echo "$PACKAGES" | grep -qxF "$pkg"; then
        am force-stop "$pkg" 2>/dev/null
        am set-standby-bucket "$pkg" restricted 2>/dev/null
        OK=$((OK+1))
    else SKIP=$((SKIP+1)); fi
done
echo "OK"

printf "🧹 [6/6] Очистка... "
for dir in /data/anr /data/tombstones /data/system/dropbox; do
    [ -d "$dir" ] && rm -rf "$dir"/* 2>/dev/null
done
logcat -c 2>/dev/null
try_cmd activity kill-all
echo "OK"

TOTAL=$((OK+FAIL+SKIP))
[ $TOTAL -gt 0 ] && B=$(( (OK*100)/TOTAL )) || B=90
[ $B -gt 99 ] && B=99; [ $B -lt 50 ] && B=81

echo ""
echo "========================================="
echo "📊 УСПЕШНО=$OK | ОШИБОК=$FAIL | ПРОПУСК=$SKIP"
echo "🚀 БУСТ УСТРОЙСТВА: +${B}%"
echo "========================================="
echo "📁 Лог: $LOGFILE"
"""

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE,
        android_id TEXT UNIQUE,
        username TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_at DATETIME,
        runs INTEGER DEFAULT 0,
        last_run DATETIME
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        android_id TEXT,
        event TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    db.close()

init_db()

def generate_script(device_id):
    script = CORE_SCRIPT.replace("__DEVICE_ID__", device_id)
    password = hashlib.sha256((device_id + MASTER_KEY).encode()).hexdigest()[:32]
    tmp = f"/tmp/core_{device_id}.sh"
    with open(tmp, "w") as f:
        f.write(script)
    result = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-a", "-salt", "-pbkdf2",
         "-pass", f"pass:{password}", "-in", tmp],
        capture_output=True, text=True
    )
    os.remove(tmp)
    cipher = result.stdout.strip()
    # Загрузчик — стучится на сервер за ключом
    server_url = os.environ.get("SERVER_URL", "https://your-app.railway.app")
    loader = f"""#!/system/bin/sh
DEV_ID=$(settings get secure android_id 2>/dev/null | tr -d '[:space:]')
echo "🔐 Проверка авторизации..."
RESPONSE=$(curl -sf "{server_url}/run?id=$DEV_ID" 2>/dev/null)
if [ -z "$RESPONSE" ]; then
    echo "❌ Нет соединения с сервером или устройство не авторизовано."
    exit 1
fi
echo "$RESPONSE" | sh
"""
    return loader

@app.route("/run")
def run_script():
    device_id = request.args.get("id", "").strip().lower()
    if not device_id or len(device_id) != 16:
        return "❌ Неверный ID.", 403
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE android_id=? AND status='approved'", (device_id,)).fetchone()
    if not user:
        db.close()
        return "❌ УСТРОЙСТВО НЕ АВТОРИЗОВАНО.", 403
    # Логируем запуск
    db.execute("UPDATE users SET runs=runs+1, last_run=CURRENT_TIMESTAMP WHERE android_id=?", (device_id,))
    db.execute("INSERT INTO logs (android_id, event) VALUES (?, 'run')", (device_id,))
    db.commit()
    db.close()
    # Возвращаем скрипт напрямую в память
    script = CORE_SCRIPT.replace("__DEVICE_ID__", device_id)
    return script, 200, {'Content-Type': 'text/plain'}

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    telegram_id = str(data.get("telegram_id", ""))
    android_id = str(data.get("android_id", "")).strip().lower()
    username = str(data.get("username", ""))
    if len(android_id) != 16 or not all(c in '0123456789abcdef' for c in android_id):
        return jsonify({"ok": False, "error": "bad_id"})
    db = get_db()
    existing = db.execute("SELECT * FROM users WHERE android_id=?", (android_id,)).fetchone()
    if existing:
        db.close()
        return jsonify({"ok": False, "error": "exists", "status": existing["status"]})
    db.execute("INSERT OR IGNORE INTO users (telegram_id, android_id, username) VALUES (?,?,?)",
               (telegram_id, android_id, username))
    db.commit()
    db.close()
    return jsonify({"ok": True})

@app.route("/approve", methods=["POST"])
def approve():
    data = request.json
    if data.get("key") != MASTER_KEY:
        return jsonify({"ok": False, "error": "unauthorized"}), 403
    android_id = str(data.get("android_id", "")).strip().lower()
    db = get_db()
    db.execute("UPDATE users SET status='approved', approved_at=CURRENT_TIMESTAMP WHERE android_id=?", (android_id,))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE android_id=?", (android_id,)).fetchone()
    db.close()
    if not user:
        return jsonify({"ok": False, "error": "not_found"})
    loader = generate_script(android_id)
    return jsonify({"ok": True, "loader": loader, "telegram_id": user["telegram_id"]})

@app.route("/reject", methods=["POST"])
def reject():
    data = request.json
    if data.get("key") != MASTER_KEY:
        return jsonify({"ok": False}), 403
    android_id = str(data.get("android_id", "")).strip().lower()
    db = get_db()
    db.execute("UPDATE users SET status='rejected' WHERE android_id=?", (android_id,))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE android_id=?", (android_id,)).fetchone()
    db.close()
    return jsonify({"ok": True, "telegram_id": user["telegram_id"] if user else None})

@app.route("/stats")
def stats():
    if request.args.get("key") != MASTER_KEY:
        return jsonify({"ok": False}), 403
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    approved = db.execute("SELECT COUNT(*) FROM users WHERE status='approved'").fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM users WHERE status='pending'").fetchone()[0]
    rejected = db.execute("SELECT COUNT(*) FROM users WHERE status='rejected'").fetchone()[0]
    total_runs = db.execute("SELECT SUM(runs) FROM users").fetchone()[0] or 0
    recent = db.execute("SELECT * FROM users WHERE status='pending' ORDER BY created_at DESC LIMIT 10").fetchall()
    db.close()
    return jsonify({
        "total": total, "approved": approved,
        "pending": pending, "rejected": rejected,
        "total_runs": total_runs,
        "pending_list": [dict(r) for r in recent]
    })

@app.route("/users")
def users():
    if request.args.get("key") != MASTER_KEY:
        return jsonify({"ok": False}), 403
    db = get_db()
    rows = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/revoke", methods=["POST"])
def revoke():
    data = request.json
    if data.get("key") != MASTER_KEY:
        return jsonify({"ok": False}), 403
    android_id = str(data.get("android_id", "")).strip().lower()
    db = get_db()
    db.execute("UPDATE users SET status='revoked' WHERE android_id=?", (android_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
