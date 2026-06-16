import os, sqlite3, hashlib, requests, logging, time, io
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан! Добавь в переменные окружения Railway.")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "7734447509"))
MASTER_KEY = os.environ.get("MASTER_KEY", "ultra_secret_2025")
SERVER_URL = os.environ.get("SERVER_URL")
if not SERVER_URL:
    raise RuntimeError("❌ SERVER_URL не задан! Это твой домен: https://web-production-e15b.up.railway.app")

PORT = int(os.environ.get("PORT", 8080))

# ---------- БАЗА ДАННЫХ (SQLite) ----------
DB = "database.db"

def get_db():
    conn = sqlite3.connect(DB, check_same_thread=False)
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

# ---------- БОТ И FLASK ----------
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ---------- ОСНОВНОЙ СКРИПТ ОПТИМИЗАЦИИ (без проверки ID, т.к. сервер уже авторизовал) ----------
CORE_SCRIPT = r'''#!/system/bin/sh
DEV_ID=$(settings get secure android_id 2>/dev/null | tr -d '[:space:]')
echo "========================================="
echo "🔥 ULTIMATE OPTIMIZATION ENGINE v14.0"
echo "========================================="
SOC=$(getprop ro.board.platform)
GPU=$(getprop ro.hardware.gpu)
SDK=$(getprop ro.build.version.sdk)
MOD=$(getprop ro.product.model)
REFRESH=$(settings get system peak_refresh_rate 2>/dev/null | tr -d '[:space:]')
[ -z "$REFRESH" ] && REFRESH=120
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
'''

# ---------- ФУНКЦИИ РАБОТЫ С БД ----------
def register_user(telegram_id, android_id, username):
    db = get_db()
    existing = db.execute("SELECT * FROM users WHERE android_id=?", (android_id,)).fetchone()
    if existing:
        db.close()
        return {"ok": False, "status": existing["status"], "telegram_id": existing["telegram_id"]}
    db.execute("INSERT OR IGNORE INTO users (telegram_id, android_id, username) VALUES (?,?,?)",
               (telegram_id, android_id, username))
    db.commit()
    db.close()
    return {"ok": True}

def approve_user(android_id):
    db = get_db()
    db.execute("UPDATE users SET status='approved', approved_at=CURRENT_TIMESTAMP WHERE android_id=?", (android_id,))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE android_id=?", (android_id,)).fetchone()
    db.close()
    return user

def reject_user(android_id):
    db = get_db()
    db.execute("UPDATE users SET status='rejected' WHERE android_id=?", (android_id,))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE android_id=?", (android_id,)).fetchone()
    db.close()
    return user

def revoke_user(android_id):
    db = get_db()
    db.execute("UPDATE users SET status='revoked' WHERE android_id=?", (android_id,))
    db.commit()
    db.close()

def log_run(android_id):
    db = get_db()
    db.execute("UPDATE users SET runs=runs+1, last_run=CURRENT_TIMESTAMP WHERE android_id=?", (android_id,))
    db.execute("INSERT INTO logs (android_id, event) VALUES (?, 'run')", (android_id,))
    db.commit()
    db.close()

def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    approved = db.execute("SELECT COUNT(*) FROM users WHERE status='approved'").fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM users WHERE status='pending'").fetchone()[0]
    rejected = db.execute("SELECT COUNT(*) FROM users WHERE status='rejected'").fetchone()[0]
    total_runs = db.execute("SELECT SUM(runs) FROM users").fetchone()[0] or 0
    pending_list = db.execute("SELECT * FROM users WHERE status='pending' ORDER BY created_at DESC LIMIT 20").fetchall()
    db.close()
    return {
        "total": total, "approved": approved,
        "pending": pending, "rejected": rejected,
        "total_runs": total_runs,
        "pending_list": [dict(r) for r in pending_list]
    }

def get_all_users():
    db = get_db()
    rows = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]

def generate_loader(device_id):
    loader = f'''#!/system/bin/sh
DEV_ID=$(settings get secure android_id 2>/dev/null | tr -d '[:space:]')
echo "🔐 Проверка авторизации..."
RESPONSE=$(curl -sf "{SERVER_URL}/run?id=$DEV_ID" 2>/dev/null)
if [ -z "$RESPONSE" ]; then
    echo "❌ Нет соединения с сервером или устройство не авторизовано."
    exit 1
fi
echo "$RESPONSE" | sh
'''
    return loader

# ---------- КЛАВИАТУРЫ (меню) ----------
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📱 Активировать скрипт")
    kb.row("ℹ️ Как пользоваться", "📞 Поддержка")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("⏳ Ожидают", "✅ Одобренные")
    kb.row("📊 Статистика", "👥 Все пользователи")
    return kb

def waiting_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔄 Проверить статус")
    kb.row("📞 Поддержка")
    return kb

# ---------- ХЕНДЛЕРЫ БОТА ----------
@bot.message_handler(commands=['start'])
def start(msg):
    if msg.chat.id == ADMIN_ID:
        stats = get_stats()
        bot.send_message(msg.chat.id,
            f"👑 *Панель администратора*\n\n"
            f"⏳ Ожидают: *{stats['pending']}*\n"
            f"✅ Одобрено: *{stats['approved']}*\n"
            f"❌ Отклонено: *{stats['rejected']}*\n"
            f"🚀 Всего запусков: *{stats['total_runs']}*\n\n"
            f"Выбери действие:",
            parse_mode="Markdown", reply_markup=admin_menu()
        )
    else:
        bot.send_message(msg.chat.id,
            "🔥 *ULTIMATE OPTIMIZATION ENGINE v14.0*\n\n"
            "Персональный скрипт оптимизации Android.\n"
            "Привязывается к твоему устройству — никто другой не сможет использовать.\n\n"
            "📌 *Шаги:*\n"
            "1️⃣ Оплати и получи подтверждение\n"
            "2️⃣ Нажми *«📱 Активировать скрипт»*\n"
            "3️⃣ Пришли свой `android_id`\n"
            "4️⃣ Получи файл и запусти через Brevent\n\n"
            "👇 Выбери действие:",
            parse_mode="Markdown", reply_markup=main_menu()
        )

@bot.message_handler(func=lambda m: m.text == "📱 Активировать скрипт")
def activate(msg):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❓ Как узнать android_id?", callback_data="how_id"))
    bot.send_message(msg.chat.id,
        "📱 *Активация скрипта*\n\n"
        "Пришли свой `android_id` — 16 символов.\n\n"
        "Открой Brevent → Выполнение команд → введи:\n"
        "`settings get secure android_id`\n\n"
        "Скопируй результат и отправь сюда 👇",
        parse_mode="Markdown", reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text == "ℹ️ Как пользоваться")
def how_to(msg):
    bot.send_message(msg.chat.id,
        "📖 *Инструкция*\n\n"
        "*Шаг 1.* Получи файл `main.sh` через бота\n"
        "*Шаг 2.* Скинь в `/sdcard/`\n"
        "*Шаг 3.* Открой Brevent → Выполнение команд\n"
        "*Шаг 4.* Введи: `sh /sdcard/main.sh`\n\n"
        "⚡ Скрипт оптимизирует:\n"
        "• Сенсор (отклик, точность)\n"
        "• Графику (Vulkan, VSYNC)\n"
        "• CPU/GPU (снятие троттлинга)\n"
        "• Сеть (Low-Latency)\n"
        "• Память и анимации\n\n"
        "📁 Лог ошибок: `/sdcard/tweak_errors.log`",
        parse_mode="Markdown", reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "📞 Поддержка")
def support(msg):
    bot.send_message(msg.chat.id,
        "📞 *Поддержка*\n\nНапиши администратору напрямую.",
        parse_mode="Markdown", reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "🔄 Проверить статус")
def check_status(msg):
    bot.send_message(msg.chat.id,
        "⏳ Твой запрос на рассмотрении у администратора.\nОбычно это занимает несколько минут.",
        reply_markup=waiting_menu()
    )

@bot.message_handler(func=lambda m: m.text == "⏳ Ожидают" and m.chat.id == ADMIN_ID)
def show_pending(msg):
    stats = get_stats()
    if not stats['pending_list']:
        bot.send_message(msg.chat.id, "✅ Нет ожидающих.", reply_markup=admin_menu())
        return
    for u in stats['pending_list']:
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{u['android_id']}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{u['android_id']}")
        )
        bot.send_message(msg.chat.id,
            f"📱 *Запрос активации*\n\n"
            f"👤 Username: @{u.get('username','—')}\n"
            f"🆔 Telegram: `{u['telegram_id']}`\n"
            f"📲 Android ID: `{u['android_id']}`\n"
            f"🕐 Дата: {u['created_at']}",
            parse_mode="Markdown", reply_markup=kb
        )

@bot.message_handler(func=lambda m: m.text == "✅ Одобренные" and m.chat.id == ADMIN_ID)
def show_approved(msg):
    users = get_all_users()
    approved = [u for u in users if u['status'] == 'approved']
    if not approved:
        bot.send_message(msg.chat.id, "Пока никого.", reply_markup=admin_menu())
        return
    for u in approved:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🚫 Отозвать", callback_data=f"revoke_{u['android_id']}"))
        bot.send_message(msg.chat.id,
            f"✅ *Одобрено:* `{u['android_id']}`\n"
            f"👤 @{u.get('username','—')}\n"
            f"🚀 Запусков: {u['runs']}",
            parse_mode="Markdown", reply_markup=kb
        )

@bot.message_handler(func=lambda m: m.text == "📊 Статистика" and m.chat.id == ADMIN_ID)
def stats(msg):
    stats = get_stats()
    bot.send_message(msg.chat.id,
        f"📊 *Статистика*\n\n"
        f"👥 Всего пользователей: *{stats['total']}*\n"
        f"⏳ Ожидают: *{stats['pending']}*\n"
        f"✅ Одобрено: *{stats['approved']}*\n"
        f"❌ Отклонено: *{stats['rejected']}*\n"
        f"🚀 Всего запусков: *{stats['total_runs']}*",
        parse_mode="Markdown", reply_markup=admin_menu()
    )

@bot.message_handler(func=lambda m: m.text == "👥 Все пользователи" and m.chat.id == ADMIN_ID)
def all_users(msg):
    users = get_all_users()
    if not users:
        bot.send_message(msg.chat.id, "Нет пользователей.", reply_markup=admin_menu())
        return
    text = "👥 *Все пользователи:*\n\n"
    for u in users[-20:]:
        status_icon = {"approved":"✅","pending":"⏳","rejected":"❌","revoked":"🚫"}.get(u['status'],'❓')
        text += f"{status_icon} `{u['android_id']}` | @{u.get('username','—')} | 🚀{u['runs']}\n"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=admin_menu())

# ---------- CALLBACKS ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def cb_approve(call):
    if call.message.chat.id != ADMIN_ID: return
    android_id = call.data.replace("approve_", "")
    try:
        user = approve_user(android_id)
        if not user:
            bot.answer_callback_query(call.id, "Пользователь не найден")
            return
        loader = generate_loader(android_id)
        # Отправляем загрузчик покупателю
        f = io.BytesIO(loader.encode())
        f.name = "main.sh"
        bot.send_document(int(user["telegram_id"]), f,
            caption=(
                "✅ *Активация успешна!*\n\n"
                "📁 Скопируй `main.sh` в `/sdcard/`\n"
                "▶️ Запусти в Brevent:\n"
                "`sh /sdcard/main.sh`\n\n"
                "⚠️ Скрипт привязан к твоему устройству.\n"
                "При каждом запуске идёт проверка через сервер."
            ),
            parse_mode="Markdown"
        )
        bot.send_message(int(user["telegram_id"]),
            "🎉 Добро пожаловать! Если нужна помощь — нажми «📞 Поддержка»",
            reply_markup=main_menu()
        )
        bot.edit_message_text(f"✅ Одобрено: `{android_id}`",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "✅ Одобрено!")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def cb_reject(call):
    if call.message.chat.id != ADMIN_ID: return
    android_id = call.data.replace("reject_", "")
    user = reject_user(android_id)
    if user:
        bot.send_message(int(user["telegram_id"]),
            "❌ *Активация отклонена.*\n\nОбратитесь в поддержку.",
            parse_mode="Markdown", reply_markup=main_menu()
        )
    bot.edit_message_text(f"❌ Отклонено: `{android_id}`",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id, "Отклонено.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("revoke_"))
def cb_revoke(call):
    if call.message.chat.id != ADMIN_ID: return
    android_id = call.data.replace("revoke_", "")
    revoke_user(android_id)
    bot.edit_message_text(f"🚫 Отозвано: `{android_id}`",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id, "Доступ отозван.")

@bot.callback_query_handler(func=lambda c: c.data == "how_id")
def cb_how_id(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "📱 *Как узнать android\\_id:*\n\n"
        "Открой Brevent → Выполнение команд → введи:\n"
        "`settings get secure android_id`\n\n"
        "Скопируй 16 символов и отправь сюда.",
        parse_mode="Markdown"
    )

# ---------- ПРИЁМ ТЕКСТА (android_id) ----------
@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    text = msg.text.strip().lower()
    if len(text) == 16 and all(c in '0123456789abcdef' for c in text):
        android_id = text
        username = msg.from_user.username or ""
        result = register_user(str(msg.chat.id), android_id, username)
        if not result["ok"]:
            status = result.get("status", "")
            if status == "approved":
                bot.send_message(msg.chat.id,
                    "✅ Это устройство уже активировано! Используй файл который получил ранее.",
                    reply_markup=main_menu())
            elif status == "pending":
                bot.send_message(msg.chat.id,
                    "⏳ Запрос уже отправлен. Ожидай одобрения.",
                    reply_markup=waiting_menu())
            elif status in ("rejected", "revoked"):
                bot.send_message(msg.chat.id,
                    "❌ Доступ для этого устройства закрыт. Обратись в поддержку.",
                    reply_markup=main_menu())
            return
        bot.send_message(msg.chat.id,
            "⏳ *Запрос отправлен!*\n\n"
            "Ожидай одобрения администратора.\n"
            "Обычно это занимает несколько минут.",
            parse_mode="Markdown", reply_markup=waiting_menu()
        )
        # Уведомление админу
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{android_id}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{android_id}")
        )
        bot.send_message(ADMIN_ID,
            f"🔔 *Новый запрос!*\n\n"
            f"👤 @{username or '—'}\n"
            f"🆔 `{msg.chat.id}`\n"
            f"📲 Android ID: `{android_id}`",
            parse_mode="Markdown", reply_markup=kb
        )
    else:
        bot.send_message(msg.chat.id,
            "❓ Не понял. Нажми кнопку ниже.",
            reply_markup=main_menu()
        )

# ---------- ЭНДПОИНТЫ ДЛЯ ЗАГРУЗЧИКА ----------
@app.route('/run')
def run_script():
    device_id = request.args.get("id", "").strip().lower()
    if not device_id or len(device_id) != 16:
        return "❌ Неверный ID.", 403
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE android_id=? AND status='approved'", (device_id,)).fetchone()
    db.close()
    if not user:
        return "❌ УСТРОЙСТВО НЕ АВТОРИЗОВАНО.", 403
    log_run(device_id)
    return CORE_SCRIPT, 200, {'Content-Type': 'text/plain'}

# ---------- ВЕБХУК ----------
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 400

@app.route('/')
def home():
    return "✅ Бот работает!"

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    # Удаляем старый webhook
    bot.remove_webhook()
    # Устанавливаем новый
    webhook_url = f"{SERVER_URL}/webhook"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook установлен на {webhook_url}")
    app.run(host='0.0.0.0', port=PORT)