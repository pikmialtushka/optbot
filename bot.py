import os, requests
try:
    import telebot
    from telebot import types
except ImportError:
    os.system("pip install pyTelegramBotAPI --break-system-packages -q")
    import telebot
    from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8960693137:AAEl96_M3gjtd29uqrDbELKa18BfMxAlAH8")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "7734447509"))
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000")
MASTER_KEY = os.environ.get("MASTER_KEY", "ultra_secret_2025")

bot = telebot.TeleBot(BOT_TOKEN)

# ── Меню ─────────────────────────────────────────────────

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

# ── /start ───────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def start(msg):
    if msg.chat.id == ADMIN_ID:
        r = requests.get(f"{SERVER_URL}/stats?key={MASTER_KEY}", timeout=5).json()
        bot.send_message(msg.chat.id,
            f"👑 *Панель администратора*\n\n"
            f"⏳ Ожидают: *{r['pending']}*\n"
            f"✅ Одобрено: *{r['approved']}*\n"
            f"❌ Отклонено: *{r['rejected']}*\n"
            f"🚀 Всего запусков: *{r['total_runs']}*\n\n"
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

# ── Активация ────────────────────────────────────────────

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

# ── Админ кнопки ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "⏳ Ожидают" and m.chat.id == ADMIN_ID)
def show_pending(msg):
    r = requests.get(f"{SERVER_URL}/stats?key={MASTER_KEY}", timeout=5).json()
    if not r['pending_list']:
        bot.send_message(msg.chat.id, "✅ Нет ожидающих.", reply_markup=admin_menu())
        return
    for u in r['pending_list']:
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
    r = requests.get(f"{SERVER_URL}/users?key={MASTER_KEY}", timeout=5).json()
    approved = [u for u in r if u['status'] == 'approved']
    if not approved:
        bot.send_message(msg.chat.id, "Пока никого.", reply_markup=admin_menu())
        return
    text = "✅ *Одобренные:*\n\n"
    for u in approved:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🚫 Отозвать", callback_data=f"revoke_{u['android_id']}"))
        bot.send_message(msg.chat.id,
            f"• `{u['android_id']}` | @{u.get('username','—')}\n"
            f"  Запусков: {u['runs']} | Последний: {u.get('last_run','—')}",
            parse_mode="Markdown", reply_markup=kb
        )

@bot.message_handler(func=lambda m: m.text == "📊 Статистика" and m.chat.id == ADMIN_ID)
def stats(msg):
    r = requests.get(f"{SERVER_URL}/stats?key={MASTER_KEY}", timeout=5).json()
    bot.send_message(msg.chat.id,
        f"📊 *Статистика*\n\n"
        f"👥 Всего пользователей: *{r['total']}*\n"
        f"⏳ Ожидают: *{r['pending']}*\n"
        f"✅ Одобрено: *{r['approved']}*\n"
        f"❌ Отклонено: *{r['rejected']}*\n"
        f"🚀 Всего запусков: *{r['total_runs']}*",
        parse_mode="Markdown", reply_markup=admin_menu()
    )

@bot.message_handler(func=lambda m: m.text == "👥 Все пользователи" and m.chat.id == ADMIN_ID)
def all_users(msg):
    r = requests.get(f"{SERVER_URL}/users?key={MASTER_KEY}", timeout=5).json()
    if not r:
        bot.send_message(msg.chat.id, "Нет пользователей.", reply_markup=admin_menu())
        return
    text = "👥 *Все пользователи:*\n\n"
    for u in r[-20:]:
        status_icon = {"approved":"✅","pending":"⏳","rejected":"❌","revoked":"🚫"}.get(u['status'],'❓')
        text += f"{status_icon} `{u['android_id']}` | @{u.get('username','—')} | 🚀{u['runs']}\n"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=admin_menu())

# ── Callbacks ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def cb_approve(call):
    if call.message.chat.id != ADMIN_ID: return
    android_id = call.data.replace("approve_", "")
    try:
        r = requests.post(f"{SERVER_URL}/approve",
            json={"android_id": android_id, "key": MASTER_KEY}, timeout=10).json()
        if r.get("ok"):
            loader = r["loader"]
            user_tid = r["telegram_id"]
            # Отправляем загрузчик покупателю
            import io
            f = io.BytesIO(loader.encode())
            f.name = "main.sh"
            bot.send_document(int(user_tid), f,
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
            bot.send_message(int(user_tid),
                "🎉 Добро пожаловать! Если нужна помощь — нажми «📞 Поддержка»",
                reply_markup=main_menu()
            )
            bot.edit_message_text(f"✅ Одобрено: `{android_id}`",
                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, f"Ошибка: {r.get('error')}")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Ошибка: {e}")
    bot.answer_callback_query(call.id, "✅ Одобрено!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def cb_reject(call):
    if call.message.chat.id != ADMIN_ID: return
    android_id = call.data.replace("reject_", "")
    r = requests.post(f"{SERVER_URL}/reject",
        json={"android_id": android_id, "key": MASTER_KEY}, timeout=5).json()
    if r.get("ok") and r.get("telegram_id"):
        bot.send_message(int(r["telegram_id"]),
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
    requests.post(f"{SERVER_URL}/revoke",
        json={"android_id": android_id, "key": MASTER_KEY}, timeout=5)
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

# ── Приём android_id ──────────────────────────────────────

@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    text = msg.text.strip().lower()
    if len(text) == 16 and all(c in '0123456789abcdef' for c in text):
        android_id = text
        username = msg.from_user.username or ""
        r = requests.post(f"{SERVER_URL}/register", json={
            "telegram_id": str(msg.chat.id),
            "android_id": android_id,
            "username": username
        }, timeout=5).json()

        if not r.get("ok"):
            status = r.get("status", "")
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

# Сброс webhook
try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
except: pass

print("🤖 Бот запущен...")
bot.infinity_polling(skip_pending=True)
