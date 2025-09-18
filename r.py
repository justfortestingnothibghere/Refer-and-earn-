import telebot
from telebot import types
import json, os, time, random, math

# ------------------ CONFIG ------------------
BOT_TOKEN = "7913272382:AAGnvD29s4bu_jmsejNmT5eWbl7HZnGy_OM"   # <<-- REPLACE this
ADMINS = [8163739723]          # list of admin Telegram IDs (integers)
UPI_ID = "mr-arman-01@fam"
DATA_FILE = "data.json"

MIN_DEPOSIT = 1
MIN_WITHDRAW = 2
REFERRAL_REWARD = 1
DAILY_BONUS_BASE = 1
MYSTERY_BOX_COST = 5
LOTTERY_TICKET_COST = 5
VIP_THRESHOLD = 100.0
# --------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def notify_admin(text):
    for admin_id in ADMINS:
        try:
            bot.send_message(int(admin_id), text)
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")


# ------------------ STORAGE ------------------
def load():
    if not os.path.exists(DATA_FILE):
        base = {
            "users": {},           # uid_str -> user data
            "deposits": {},        # deposit_id -> {uid, amount, status}
            "withdrawals": {},     # wid -> {uid, amount, upi, status}
            "activity": [],        # list of recent messages
            "lottery": {           # daily lottery structure
                "date": "",        # YYYY-MM-DD
                "tickets": {}      # uid_str -> number_of_tickets
            }
        }
        json.dump(base, open(DATA_FILE, "w"), indent=2)
        return base
    return json.load(open(DATA_FILE, "r"))

def save():
    json.dump(data, open(DATA_FILE, "w"), indent=2)

data = load()

def add_activity(text):
    ts = time.strftime("%d-%b %H:%M", time.localtime())
    entry = f"{ts} — {text}"
    data["activity"].insert(0, entry)
    if len(data["activity"]) > 30:
        data["activity"] = data["activity"][:30]
    save()

def ensure_user(uid, uname=""):
    s = str(uid)
    if s not in data["users"]:
        data["users"][s] = {
            "balance": 0.0,
            "ref_by": None,
            "referrals": [],
            "last_daily": 0,
            "streak": 0,
            "games": {"played": 0, "won": 0},
            "uname": uname or "",
            "vip": False,
            "transactions": [],  # list of strings
            "tickets": 0         # lottery tickets owned (for display convenience)
        }
        save()

def format_money(x):
    return f"₹{float(x):.2f}"

# ------------------ KEYBOARDS ------------------
def kb_main():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💼 Profile", "💰 Balance")
    kb.row("➕ Deposit", "💸 Withdraw")
    kb.row("🎮 Games Zone", "👥 Referral")
    kb.row("🎁 Daily Bonus", "🧩 Mystery Box")
    kb.row("🎟️ Lottery", "🏆 Leaderboard")
    kb.row("📜 Activity Feed")
    return kb

def admin_inline_for_deposit(deposit_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"dep_accept_{deposit_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"dep_reject_{deposit_id}")
    )
    return markup

def admin_inline_for_withdraw(wid):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Pay & Approve", callback_data=f"wd_accept_{wid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"wd_reject_{wid}")
    )
    return markup

# ------------------ UTIL ------------------
def is_admin(uid):
    return uid in ADMINS

def next_id(prefix):
    return f"{prefix}{int(time.time()*1000)}{random.randint(100,999)}"

# ------------------ START ------------------

@bot.message_handler(commands=["send"])
def send_money(m):
    uid = str(m.from_user.id)
    parts = m.text.split()
    if len(parts) < 3:
        return bot.reply_to(m, "❌ Usage: /send AMOUNT USER_ID")
    
    try:
        amt = float(parts[1])
        target_id = str(parts[2])
    except:
        return bot.reply_to(m, "❌ Invalid format. Example: /send 10 123456789")

    if amt <= 0:
        return bot.reply_to(m, "❌ Amount must be greater than 0")

    # Check balance
    if data["users"][uid]["balance"] < amt:
        return bot.reply_to(m, "❌ Not enough balance to send")

    # Check if target exists
    ensure_user(target_id)
    
    # Transfer
    data["users"][uid]["balance"] -= amt
    data["users"][target_id]["balance"] += amt
    save()

    bot.reply_to(m, f"✅ You sent ₹{amt:.2f} to user {target_id}")
    try:
        bot.send_message(int(target_id), f"💸 You received ₹{amt:.2f} from user {uid}")
    except:
        pass

    notify_admin(f"🔄 Transfer: {uid} ➡️ {target_id} | Amount: ₹{amt}")



@bot.message_handler(commands=["help"])
def help_cmd(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("💰 Deposit", callback_data="help_deposit"),
        types.InlineKeyboardButton("💸 Withdrawal", callback_data="help_withdraw")
    )
    kb.add(
        types.InlineKeyboardButton("🎮 Games", callback_data="help_games"),
        types.InlineKeyboardButton("🎁 Rewards", callback_data="help_rewards")
    )
    kb.add(
        types.InlineKeyboardButton("👥 Referrals", callback_data="help_referrals"),
        types.InlineKeyboardButton("💼 Wallet/Send", callback_data="help_wallet")
    )
    kb.add(
        types.InlineKeyboardButton("🏆 Leaderboard", callback_data="help_leaderboard"),
        types.InlineKeyboardButton("⚙️ Profile", callback_data="help_profile")
    )
    bot.send_message(m.chat.id, "📖 <b>Help Menu</b>\n\nChoose a topic below 👇", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("help_"))
def help_sections(c):
    section = c.data.split("_")[1]

    if section == "deposit":
        text = (
            "💰 <b>Deposit Help</b>\n\n"
            "1️⃣ Click <b>➕ Deposit</b>\n"
            "2️⃣ Send money to the UPI shown\n"
            "3️⃣ Use /deposit TXID AMOUNT\n"
            "4️⃣ Admin will approve ✅\n\n"
            "⚡ Min Deposit: ₹1"
        )
    elif section == "withdraw":
        text = (
            "💸 <b>Withdrawal Help</b>\n\n"
            "1️⃣ Click <b>Withdraw</b>\n"
            "2️⃣ Type /withdraw AMOUNT UPI_ID\n"
            "3️⃣ Example: /withdraw 50 myupi@upi\n"
            "4️⃣ Wait for admin approval ⏳\n\n"
            f"⚡ Min Withdrawal: ₹{MIN_WITHDRAW}"
        )
    elif section == "games":
        text = (
            "🎮 <b>Games Help</b>\n\n"
            "Available Games:\n"
            "🪙 Coin Flip → Bet & win double\n"
            "🎡 Lucky Spin → Random win upto ₹50\n"
            "🔢 Number Guess → Guess right & win 4x\n"
            "📦 Mystery Box → ₹5 → win random upto ₹50\n\n"
            "⚡ Games deduct balance directly."
        )
    elif section == "rewards":
        text = (
            "🎁 <b>Rewards Help</b>\n\n"
            "• Daily Bonus (₹0–₹1)\n"
            "• Streak Bonus (7 days = ₹10)\n"
            f"• Referral Reward = ₹{REFERRAL_REWARD}\n"
            "• VIP Bonus (extra perks for deposits ≥ ₹100)"
        )
    elif section == "referrals":
        text = (
            "👥 <b>Referral Help</b>\n\n"
            "Invite friends using your referral link.\n"
            "Every friend = ₹1 in your wallet.\n"
            "Your link: https://t.me/{bot.get_me().username}?start=ref_USERID"
        )
    elif section == "wallet":
        text = (
            "💼 <b>Wallet & Send Money</b>\n\n"
            "• /balance → check wallet\n"
            "• /send AMOUNT USERID → send money\n"
            "Example: /send 10 123456789\n\n"
            "⚡ Instant transfer between users."
        )
    elif section == "leaderboard":
        text = (
            "🏆 <b>Leaderboard Help</b>\n\n"
            "• Shows Top Referrers\n"
            "• Shows Top Winners\n"
            "• Shows Top Depositors\n\n"
            "Compete & be the best 💪"
        )
    elif section == "profile":
        text = (
            "⚙️ <b>Profile Help</b>\n\n"
            "• /profile → See your details:\n"
            "- Username\n"
            "- Balance\n"
            "- Referrals\n"
            "- VIP Status\n"
            "- Games Played\n"
        )
    else:
        text = "❌ Unknown section"

    # Edit same message
    bot.edit_message_text(
        text,
        c.message.chat.id,
        c.message.message_id,
        reply_markup=None
    )
    bot.answer_callback_query(c.id)

@bot.message_handler(commands=["start"])
def cmd_start(m):
    uid = m.from_user.id
    uname = m.from_user.username or m.from_user.first_name or "user"
    ensure_user(uid, uname)
    # check referral param
    if m.text and "ref_" in m.text:
        try:
            refid = m.text.split("ref_")[-1]
            if refid != str(uid):
                u = data["users"][str(uid)]
                if not u["ref_by"]:
                    u["ref_by"] = refid
                    ref = data["users"].get(refid)
                    if ref:
                        ref["balance"] += REFERRAL_REWARD
                        ref["referrals"].append(str(uid))
                        save()
                        bot.send_message(int(refid), f"🎉 You earned {format_money(REFERRAL_REWARD)} for referring @{uname}!")
                        add_activity(f"💞 @{ref.get('uname','user')} earned referral {format_money(REFERRAL_REWARD)}")
        except Exception:
            pass
    bot.send_message(uid, f"👋 Welcome <b>{uname}</b>!\nI am your Earn & Play bot — play games, earn, refer, withdraw.", reply_markup=kb_main())

# ------------------ PROFILE & BALANCE ------------------
@bot.message_handler(func=lambda m: m.text=="💼 Profile")
def cmd_profile(m):
    uid = str(m.from_user.id); ensure_user(int(uid))
    u = data["users"][uid]
    vip_text = "👑 VIP" if u["vip"] else "Normal"
    msg = (f"<b>📊 Profile</b>\n\n"
           f"👤 @{u['uname']}\n"
           f"🆔 {uid}\n"
           f"💰 Balance: {format_money(u['balance'])}\n"
           f"👥 Referrals: {len(u['referrals'])}\n"
           f"🎮 Games Played: {u['games']['played']} | Won: {u['games']['won']}\n"
           f"🎁 Streak: {u['streak']} days\n"
           f"🎫 Tickets: {u.get('tickets',0)}\n"
           f"⭐ Status: {vip_text}\n")
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text=="💰 Balance")
def cmd_balance(m):
    uid = str(m.from_user.id)
    ensure_user(int(uid))
    bal = data["users"][uid]["balance"]
    bot.reply_to(m, f"💰 Your Balance: <b>{format_money(bal)}</b>")

# ------------------ REFERRAL ------------------
@bot.message_handler(func=lambda m: m.text=="👥 Referral")
def cmd_referral(m):
    uid = m.from_user.id
    username = bot.get_me().username or "bot"
    link = f"https://t.me/{username}?start=ref_{uid}"
    refs = len(data["users"][str(uid)]["referrals"])
    bot.send_message(uid, f"👥 Share your referral link:\n{link}\n\nYou have <b>{refs}</b> referrals.\nReward per referral: {format_money(REFERRAL_REWARD)}")

# ------------------ DAILY BONUS ------------------
@bot.message_handler(func=lambda m: m.text=="🎁 Daily Bonus")
def cmd_daily(m):
    uid = str(m.from_user.id); ensure_user(int(uid))
    u = data["users"][uid]
    now = time.time()
    if now - u["last_daily"] < 86400:
        bot.reply_to(m, "⏳ You already claimed daily bonus. Come back later!")
        return
    # increase streak if claimed within ~48 hours (allow some leeway)
    # simple approach: exact day check
    u["last_daily"] = now
    u["streak"] = u.get("streak",0) + 1
    reward = DAILY_BONUS_BASE * u["streak"]
    # cap streak reward to sane value
    reward = min(reward, 20)
    # VIP gets extra
    if u.get("vip"):
        reward += 1
    u["balance"] += reward
    u["transactions"].append(f"Daily Bonus {format_money(reward)}")
    if u["balance"] >= VIP_THRESHOLD and not u["vip"]:
        u["vip"] = True
        add_activity(f"👑 @{u['uname']} became VIP")
    save()
    bot.reply_to(m, f"🎁 Daily Bonus: {format_money(reward)} (Streak {u['streak']} days)\nNew Balance: {format_money(u['balance'])}")
    add_activity(f"🎁 @{u['uname']} claimed daily {format_money(reward)}")

# ------------------ MYSTERY BOX ------------------
@bot.message_handler(func=lambda m: m.text=="🧩 Mystery Box")
def cmd_mystery(m):
    uid = str(m.from_user.id); ensure_user(int(uid))
    u = data["users"][uid]
    cost = MYSTERY_BOX_COST
    if u["balance"] < cost:
        bot.send_message(m.chat.id, f"❌ You need {format_money(cost)} to open a Mystery Box.")
        return
    u["balance"] -= cost
    # rewards distribution (more small wins, rare big wins)
    reward = random.choices([0,1,2,5,10,20,50], weights=[30,25,20,12,8,4,1])[0]
    # VIP increased odds slightly
    if u["vip"] and random.random() < 0.12:
        reward = max(reward, random.choice([5,10,20]))
    u["balance"] += reward
    u["transactions"].append(f"Mystery Box -{format_money(cost)} +{format_money(reward)}")
    save()
    bot.send_message(m.chat.id, f"🎁 Mystery Box opened!\nYou got: {format_money(reward)}\nBalance: {format_money(u['balance'])}")
    add_activity(f"🧩 @{u['uname']} opened Mystery Box → {format_money(reward)}")

# ------------------ DEPOSIT ------------------
@bot.message_handler(func=lambda m: m.text=="➕ Deposit")
def cmd_deposit_info(m):
    bot.send_message(m.chat.id, f"➕  Sᴇɴᴅ ᴍᴏɴᴇʏ ᴛᴏ ᴛʜɪs UPI:\n<b>{UPI_ID}</b>\n\nAғᴛᴇʀ Pᴀʏᴍᴇɴᴛ, Tʏᴘᴇ :\n/deposit AMOUNT\n(Example: /deposit 50)")

@bot.message_handler(commands=["deposit"])
def cmd_deposit(m):
    uid = str(m.from_user.id)
    ensure_user(int(uid))
    parts = m.text.split()
    if len(parts) < 2:
        return bot.reply_to(m, "Usage: /deposit AMOUNT")
    try:
        amt = float(parts[1])
    except:
        return bot.reply_to(m, "❌ Invalid amount.")
    if amt < MIN_DEPOSIT:
        return bot.reply_to(m, f"❌ Minimum deposit is {format_money(MIN_DEPOSIT)}")

    dep_id = next_id("DEP")
    data["deposits"][dep_id] = {"uid": uid, "amount": float(amt), "status": "pending", "ts": int(time.time())}
    save()
    # notify admins with inline approve/reject
    for a in ADMINS:
        try:
            bot.send_message(a, f"💰 Deposit Request\nID: {dep_id}\nUser: @{data['users'][uid]['uname']} ({uid})\nAmount: {format_money(amt)}", reply_markup=admin_inline_for_deposit(dep_id))
        except Exception:
            pass
    bot.send_message(m.chat.id, "📤 Deposit request sent to admin. Wait for approval.")
    add_activity(f"💰 Deposit request by @{data['users'][uid]['uname']} {format_money(amt)}")


# ------------------ WITHDRAW ------------------
@bot.message_handler(func=lambda m: m.text=="💸 Withdraw")
def cmd_withdraw_info(m):
    bot.send_message(m.chat.id, f"💸 To withdraw, type:\n/withdraw AMOUNT UPI_ID\n(Min {format_money(MIN_WITHDRAW)})")

@bot.message_handler(commands=["withdraw"])
def cmd_withdraw(m):
    uid = str(m.from_user.id); ensure_user(int(uid))
    parts = m.text.split()
    if len(parts) < 3:
        return bot.reply_to(m, "Usage: /withdraw AMOUNT UPI_ID")
    try:
        amt = float(parts[1])
    except:
        return bot.reply_to(m, "❌ Invalid amount.")
    upi = parts[2]
    u = data["users"][uid]
    if amt < MIN_WITHDRAW:
        return bot.reply_to(m, f"❌ Minimum withdraw is {format_money(MIN_WITHDRAW)}")
    if u["balance"] < amt:
        return bot.reply_to(m, "❌ Not enough balance.")
    wid = next_id("WD")
    data["withdrawals"][wid] = {"uid": uid, "amount": float(amt), "upi": upi, "status": "pending", "ts": int(time.time())}
    save()
    # notify admins
    for a in ADMINS:
        try:
            bot.send_message(a, f"💸 Withdraw Request\nID: {wid}\nUser: @{u['uname']} ({uid})\nAmount: {format_money(amt)}\nUPI: {upi}", reply_markup=admin_inline_for_withdraw(wid))
        except Exception:
            pass
    bot.send_message(m.chat.id, "✅ Withdraw request submitted to admin for approval.")
    add_activity(f"💸 Withdraw request by @{u['uname']} {format_money(amt)}")

# ------------------ ADMIN CALLBACKS (deposit/withdraw approve) ------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("dep_accept_") or call.data.startswith("dep_reject_") or call.data.startswith("wd_accept_") or call.data.startswith("wd_reject_"))
def admin_decisions(call):
    data_s = call.data
    caller = call.from_user.id
    if not is_admin(caller):
        bot.answer_callback_query(call.id, "❌ Not authorized")
        return
    # deposit accept/reject
    if data_s.startswith("dep_accept_") or data_s.startswith("dep_reject_"):
        parts = data_s.split("_",2)
        action = parts[1]  # accept or reject
        dep_id = parts[2]
        dep = data["deposits"].get(dep_id)
        if not dep:
            bot.answer_callback_query(call.id, "Deposit not found.")
            return
        if dep["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed.")
            return
        if action == "accept":
            dep["status"] = "approved"
            uid = dep["uid"]
            amt = float(dep["amount"])
            ensure_user(int(uid))
            data["users"][uid]["balance"] += amt
            data["users"][uid]["transactions"].append(f"Deposit +{format_money(amt)} (admin)")
            if data["users"][uid]["balance"] >= VIP_THRESHOLD:
                data["users"][uid]["vip"] = True
            save()
            bot.send_message(int(uid), f"✅ Your deposit {format_money(amt)} has been approved by admin.\nBalance: {format_money(data['users'][uid]['balance'])}")
            bot.send_message(call.from_user.id, f"👍 Approved deposit {dep_id}")
            add_activity(f"💰 Deposit approved {format_money(amt)} by admin for @{data['users'][uid]['uname']}")
        else:
            dep["status"] = "rejected"
            save()
            uid = dep["uid"]
            bot.send_message(int(uid), f"❌ Your deposit {format_money(dep['amount'])} was rejected by admin.")
            bot.send_message(call.from_user.id, f"⚠️ Rejected deposit {dep_id}")
            add_activity(f"❌ Deposit rejected {dep_id}")
        bot.answer_callback_query(call.id, "Done")
        return

    # withdraw accept/reject
    if data_s.startswith("wd_accept_") or data_s.startswith("wd_reject_"):
        parts = data_s.split("_",2)
        action = parts[1]
        wid = parts[2]
        wd = data["withdrawals"].get(wid)
        if not wd:
            bot.answer_callback_query(call.id, "Withdraw not found.")
            return
        if wd["status"] != "pending":
            bot.answer_callback_query(call.id, "Already processed.")
            return
        uid = wd["uid"]
        amt = float(wd["amount"])
        if action == "accept":
            wd["status"] = "paid"
            # in real system you'd send money; here admin marks paid
            data["users"][uid]["transactions"].append(f"Withdrawal -{format_money(amt)} (paid)")
            data["users"][uid]["balance"] -= amt
            save()
            bot.send_message(int(uid), f"✅ Your withdrawal {format_money(amt)} has been marked as paid by admin.\nRemaining Balance: {format_money(data['users'][uid]['balance'])}")
            bot.send_message(call.from_user.id, f"👍 Marked paid withdrawal {wid}")
            add_activity(f"💸 Withdrawal paid {format_money(amt)} for @{data['users'][uid]['uname']}")
        else:
            wd["status"] = "rejected"
            save()
            bot.send_message(int(uid), f"❌ Your withdrawal {format_money(amt)} was rejected by admin.")
            bot.send_message(call.from_user.id, f"⚠️ Rejected withdrawal {wid}")
            add_activity(f"❌ Withdrawal rejected {wid}")
        bot.answer_callback_query(call.id, "Done")
        return

# ------------------ GAMES ZONE ------------------
@bot.message_handler(func=lambda m: m.text=="🎮 Games Zone")
def cmd_games(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🪙 Coin Flip", callback_data="g_coin"))
    kb.add(types.InlineKeyboardButton("🎡 Lucky Spin", callback_data="g_spin"))
    kb.add(types.InlineKeyboardButton("🔢 Number Guess", callback_data="g_guess"))
    kb.add(types.InlineKeyboardButton("✊✋✌️ RPS", callback_data="g_rps"))
    bot.send_message(m.chat.id, "🎮 Choose a game:", reply_markup=kb)

# --- COIN FLIP ---
@bot.callback_query_handler(func=lambda c: c.data=="g_coin")
def g_coin_menu(c):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Bet ₹1", callback_data="coin_bet_1"))
    kb.add(types.InlineKeyboardButton("Bet ₹5", callback_data="coin_bet_5"))
    kb.add(types.InlineKeyboardButton("Bet ₹10", callback_data="coin_bet_10"))
    bot.edit_message_text("🪙 Choose your bet:", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("coin_bet_"))
def coin_bet(c):
    amt = float(c.data.split("_")[-1])
    uid = str(c.from_user.id); ensure_user(int(uid))
    u = data["users"][uid]
    if u["balance"] < amt:
        return bot.answer_callback_query(c.id, "❌ Not enough balance.")
    # ask heads/tails
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Heads", callback_data=f"coin_play_{amt}_heads"))
    kb.add(types.InlineKeyboardButton("Tails", callback_data=f"coin_play_{amt}_tails"))
    bot.edit_message_text(f"🎲 Betting {format_money(amt)} — choose:", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("coin_play_"))
def coin_play(c):
    _, _, amt, choice = c.data.split("_")
    amt = float(amt); uid = str(c.from_user.id); ensure_user(int(uid))
    u = data["users"][uid]
    if u["balance"] < amt:
        return bot.answer_callback_query(c.id, "❌ Not enough balance.")
    u["balance"] -= amt
    u["games"]["played"] += 1
    # VIP slight advantage
    if u.get("vip") and random.random() < 0.08:
        flip = choice
    else:
        flip = random.choice(["heads","tails"])
    if flip == choice:
        win_amt = amt * 2
        u["balance"] += win_amt
        u["games"]["won"] += 1
        res = f"🎉 It's {flip}! You WON {format_money(win_amt - amt)} (Return {format_money(win_amt)})"
    else:
        res = f"😢 It's {flip}. You lost {format_money(amt)}"
    u["transactions"].append(f"CoinFlip -{format_money(amt)} => {res.splitlines()[0]}")
    save()
    bot.edit_message_text(f"{res}\nBalance: {format_money(u['balance'])}", c.message.chat.id, c.message.message_id)
    add_activity(f"🪙 CoinFlip @{u['uname']} → {res.split('!')[0]}")

# --- LUCKY SPIN ---
@bot.callback_query_handler(func=lambda c: c.data=="g_spin")
def g_spin(c):
    uid = str(c.from_user.id); ensure_user(int(uid))
    u = data["users"][uid]
    # allow choose bet (2,5,10)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Bet ₹2", callback_data="spin_bet_2"))
    kb.add(types.InlineKeyboardButton("Bet ₹5", callback_data="spin_bet_5"))
    kb.add(types.InlineKeyboardButton("Bet ₹10", callback_data="spin_bet_10"))
    bot.edit_message_text("🎡 Choose spin bet:", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("spin_bet_"))
def spin_bet(c):
    amt = float(c.data.split("_")[-1])
    uid = str(c.from_user.id); ensure_user(int(uid))
    u = data["users"][uid]
    if u["balance"] < amt:
        return bot.answer_callback_query(c.id, "❌ Not enough balance.")
    u["balance"] -= amt
    u["games"]["played"] += 1
    # spin reward weighted
    choices = [0,0,1,2,5,10,20,50]
    weights = [25,20,15,12,10,8,6,4]
    reward = random.choices(choices, weights)[0]
    # VIP slight boost
    if u.get("vip") and random.random() < 0.12:
        reward = max(reward, random.choice([2,5,10]))
    u["balance"] += reward
    if reward > 0:
        u["games"]["won"] += 1
    u["transactions"].append(f"Spin -{format_money(amt)} +{format_money(reward)}")
    save()
    bot.edit_message_text(f"🎡 Spin Result: {format_money(reward)}\nBalance: {format_money(u['balance'])}", c.message.chat.id, c.message.message_id)
    add_activity(f"🎡 LuckySpin @{u['uname']} → {format_money(reward)}")

# --- NUMBER GUESS ---
@bot.callback_query_handler(func=lambda c: c.data=="g_guess")
def g_guess_menu(c):
    # show choices 1-5 and bet fixed ₹1
    kb = types.InlineKeyboardMarkup()
    row = []
    for i in range(1,6):
        row.append(types.InlineKeyboardButton(str(i), callback_data=f"guess_play_{i}"))
    for b in row:
        kb.add(b)
    bot.edit_message_text("🔢 Guess a number (1–5) | Bet ₹1", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("guess_play_"))
def guess_play(c):
    picked = int(c.data.split("_")[-1])
    uid = str(c.from_user.id); ensure_user(int(uid)); u = data["users"][uid]
    cost = 1.0
    if u["balance"] < cost:
        return bot.answer_callback_query(c.id, "❌ Not enough balance.")
    u["balance"] -= cost; u["games"]["played"] += 1
    correct = random.randint(1,5)
    if picked == correct:
        reward_multiplier = 4
        reward = cost * reward_multiplier
        u["balance"] += reward
        u["games"]["won"] += 1
        res = f"🎉 Correct! Number was {correct}. You won {format_money(reward)}"
    else:
        res = f"😢 Wrong! Number was {correct}. You lost {format_money(cost)}"
    u["transactions"].append(f"Guess -{format_money(cost)} => {res}")
    save()
    bot.edit_message_text(f"{res}\nBalance: {format_money(u['balance'])}", c.message.chat.id, c.message.message_id)
    add_activity(f"🔢 Guess @{u['uname']} guessed {picked} → {correct}")

# --- ROCK PAPER SCISSORS (RPS) ---
@bot.callback_query_handler(func=lambda c: c.data=="g_rps")
def g_rps_menu(c):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Bet ₹1", callback_data="rps_bet_1"))
    kb.add(types.InlineKeyboardButton("Bet ₹5", callback_data="rps_bet_5"))
    bot.edit_message_text("✊✋✌️ Choose bet:", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rps_bet_"))
def rps_choose(c):
    bet = float(c.data.split("_")[-1])
    uid = str(c.from_user.id); ensure_user(int(uid)); u = data["users"][uid]
    if u["balance"] < bet:
        return bot.answer_callback_query(c.id, "❌ Not enough balance.")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✊ Rock", callback_data=f"rps_play_{bet}_rock"))
    kb.add(types.InlineKeyboardButton("✋ Paper", callback_data=f"rps_play_{bet}_paper"))
    kb.add(types.InlineKeyboardButton("✌️ Scissors", callback_data=f"rps_play_{bet}_scissors"))
    bot.edit_message_text("Choose your move:", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rps_play_"))
def rps_play(c):
    _, _, bet, user_move = c.data.split("_")
    bet = float(bet); uid = str(c.from_user.id); ensure_user(int(uid)); u = data["users"][uid]
    if u["balance"] < bet:
        return bot.answer_callback_query(c.id, "❌ Not enough balance.")
    moves = ["rock","paper","scissors"]
    bot_move = random.choice(moves)
    u["balance"] -= bet; u["games"]["played"] += 1
    win = False; tie = False
    if user_move == bot_move:
        tie = True
    else:
        if (user_move=="rock" and bot_move=="scissors") or (user_move=="scissors" and bot_move=="paper") or (user_move=="paper" and bot_move=="rock"):
            win = True
    if tie:
        u["balance"] += bet  # refund
        res = f"🤝 Tie! Bot chose {bot_move}. Your bet returned."
    elif win:
        payout = bet * 2.5
        u["balance"] += payout
        u["games"]["won"] += 1
        res = f"🎉 You beat the bot! Bot chose {bot_move}. You win {format_money(payout)}"
    else:
        res = f"😢 You lost. Bot chose {bot_move}. Lost {format_money(bet)}"
    u["transactions"].append(f"RPS -{format_money(bet)} => {res}")
    save()
    bot.edit_message_text(f"{res}\nBalance: {format_money(u['balance'])}", c.message.chat.id, c.message.message_id)
    add_activity(f"✊ RPS @{u['uname']} vs bot → {res.split('.')[0]}")

# ------------------ LOTTERY ------------------
@bot.message_handler(func=lambda m: m.text=="🎟️ Lottery")
def cmd_lottery(m):
    uid = str(m.from_user.id); ensure_user(int(uid))
    # show options: buy tickets, view tickets, admin draw (if admin)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Buy Ticket (₹5)", callback_data="lot_buy_1"))
    kb.add(types.InlineKeyboardButton("View My Tickets", callback_data="lot_view"))
    if is_admin(m.from_user.id):
        kb.add(types.InlineKeyboardButton("🔔 Draw Lottery (admin)", callback_data="lot_draw"))
    bot.send_message(m.chat.id, "🎟️ Lottery — buy tickets for daily draw!", reply_markup=kb)

def ensure_lottery_date():
    today = time.strftime("%Y-%m-%d")
    if data["lottery"].get("date") != today:
        data["lottery"] = {"date": today, "tickets": {}}
        # reset users' tickets count
        for u in data["users"].values():
            u["tickets"] = 0
        save()

@bot.callback_query_handler(func=lambda c: c.data.startswith("lot_"))
def handle_lottery(c):
    ensure_lottery_date()
    parts = c.data.split("_")
    action = parts[1]
    uid = str(c.from_user.id)
    ensure_user(int(uid))
    if action == "buy":
        # parts like lot_buy_1 means buy 1 ticket
        count = int(parts[2]) if len(parts)>2 else 1
        cost = LOTTERY_TICKET_COST * count
        if data["users"][uid]["balance"] < cost:
            return bot.answer_callback_query(c.id, "❌ Not enough balance.")
        data["users"][uid]["balance"] -= cost
        data["lottery"]["tickets"][uid] = data["lottery"]["tickets"].get(uid, 0) + count
        data["users"][uid]["tickets"] = data["lottery"]["tickets"][uid]
        save()
        bot.answer_callback_query(c.id, f"✅ Bought {count} ticket(s).")
        bot.edit_message_text(f"🎟️ You bought {count} ticket(s) for today's lottery!\nYour tickets: {data['users'][uid]['tickets']}\nBalance: {format_money(data['users'][uid]['balance'])}", c.message.chat.id, c.message.message_id)
        add_activity(f"🎟️ @{data['users'][uid]['uname']} bought {count} ticket(s)")
    elif action == "view":
        tickets = data["lottery"]["tickets"].get(uid,0)
        bot.answer_callback_query(c.id, f"You have {tickets} tickets today.")
        bot.edit_message_text(f"🎟️ You have {tickets} ticket(s) for today's lottery.", c.message.chat.id, c.message.message_id)
    elif action == "draw":
        # admin draw
        if not is_admin(c.from_user.id):
            return bot.answer_callback_query(c.id, "❌ Not authorized")
        tickets = data["lottery"]["tickets"]
        total_tickets = sum(tickets.values())
        if total_tickets == 0:
            return bot.answer_callback_query(c.id, "No tickets sold today.")
        # build pool
        pool = []
        for k, cnt in tickets.items():
            pool.extend([k]*cnt)
        winner = random.choice(pool)
        # choose prize amount (you can customize). For example 50% of pot
        pot = total_tickets * LOTTERY_TICKET_COST
        prize = pot * 0.6
        prize = round(prize, 2)
        # reward winner
        ensure_user(int(winner))
        data["users"][winner]["balance"] += prize
        data["users"][winner]["transactions"].append(f"Lottery prize +{format_money(prize)}")
        add_activity(f"🎉 Lottery winner @{data['users'][winner]['uname']} won {format_money(prize)}")
        # reset lottery
        data["lottery"] = {"date": "", "tickets": {}}
        # reset user tickets
        for u in data["users"].values():
            u["tickets"] = 0
        save()
        bot.edit_message_text(f"🎉 Lottery Drawn! Winner: @{data['users'][winner]['uname']} — Prize {format_money(prize)}", c.message.chat.id, c.message.message_id)
        # notify winner
        bot.send_message(int(winner), f"🎊 Congrats! You won the lottery: {format_money(prize)}")
        return

# ------------------ LEADERBOARD & ACTIVITY ------------------
@bot.message_handler(func=lambda m: m.text=="🏆 Leaderboard")
def cmd_leaderboard(m):
    # top by balance, top referrers, top winners (games won)
    users = data["users"]
    top_balance = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
    top_refs = sorted(users.items(), key=lambda x: len(x[1].get("referrals",[])), reverse=True)[:10]
    top_wins = sorted(users.items(), key=lambda x: x[1]["games"].get("won",0), reverse=True)[:10]
    msg = "<b>🏆 Leaderboards</b>\n\n<b>Top Balances</b>\n"
    for i,(uid,u) in enumerate(top_balance[:5],1):
        msg += f"{i}. @{u.get('uname','user')} — {format_money(u['balance'])}\n"
    msg += "\n<b>Top Referrers</b>\n"
    for i,(uid,u) in enumerate(top_refs[:5],1):
        msg += f"{i}. @{u.get('uname','user')} — {len(u.get('referrals',[]))} refs\n"
    msg += "\n<b>Top Game Winners</b>\n"
    for i,(uid,u) in enumerate(top_wins[:5],1):
        msg += f"{i}. @{u.get('uname','user')} — {u['games'].get('won',0)} wins\n"
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text=="📜 Activity Feed")
def cmd_activity(m):
    if not data["activity"]:
        return bot.send_message(m.chat.id, "No recent activity.")
    msg = "<b>📜 Recent Activity</b>\n\n" + "\n".join(data["activity"][:12])
    bot.send_message(m.chat.id, msg)

# ------------------ ADMIN COMMANDS: /admin /broadcast /stats ------------------
@bot.message_handler(commands=["admin"])
def cmd_admin(m):
    if not is_admin(m.from_user.id):
        return bot.reply_to(m, "❌ Not authorized.")
    # construct admin keyboard
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("/stats", "/users")
    kb.row("/broadcast", "/pending")
    kb.row("/draw_lottery", "/cancel")
    bot.send_message(m.chat.id, "Admin panel:", reply_markup=kb)

@bot.message_handler(commands=["stats"])
def cmd_stats(m):
    if not is_admin(m.from_user.id): return
    total_users = len(data["users"])
    total_balance = sum(u["balance"] for u in data["users"].values())
    total_deposits = sum(d["amount"] for d in data["deposits"].values() if d["status"]=="approved")
    total_withdrawals = sum(w["amount"] for w in data["withdrawals"].values() if w["status"] in ("paid","approved"))
    msg = (f"<b>📊 Bot Stats</b>\n\n"
           f"Users: {total_users}\n"
           f"Total Balance (all wallets): {format_money(total_balance)}\n"
           f"Total Approved Deposits: {format_money(total_deposits)}\n"
           f"Total Paid Withdrawals: {format_money(total_withdrawals)}\n")
    bot.send_message(m.chat.id, msg)

@bot.message_handler(commands=["users"])
def cmd_users(m):
    if not is_admin(m.from_user.id): return
    # list top 30 users by balance
    top = sorted(data["users"].items(), key=lambda x: x[1]["balance"], reverse=True)[:30]
    lines = []
    for uid,u in top:
        lines.append(f"@{u.get('uname','user')} ({uid}) — {format_money(u['balance'])} refs:{len(u.get('referrals',[]))}")
    bot.send_message(m.chat.id, "<b>Top users</b>\n\n" + "\n".join(lines))

@bot.message_handler(commands=["pending"])
def cmd_pending(m):
    if not is_admin(m.from_user.id): return
    # show pending deposits and withdrawals
    deps = [f"{k}: @{data['users'][v['uid']]['uname']} {format_money(v['amount'])}" for k,v in data["deposits"].items() if v["status"]=="pending"]
    wds = [f"{k}: @{data['users'][v['uid']]['uname']} {format_money(v['amount'])} -> {v['upi']}" for k,v in data["withdrawals"].items() if v["status"]=="pending"]
    msg = "<b>Pending</b>\n\n<strong>Deposits</strong>\n" + ("\n".join(deps) if deps else "None") + "\n\n<strong>Withdrawals</strong>\n" + ("\n".join(wds) if wds else "None")
    bot.send_message(m.chat.id, msg)

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(m):
    if not is_admin(m.from_user.id): return
    # /broadcast Hello everyone...
    text = m.text.partition(" ")[2].strip()
    if not text:
        return bot.reply_to(m, "Usage: /broadcast Your message here")
    sent = 0
    for uid in list(data["users"].keys()):
        try:
            bot.send_message(int(uid), f"📢 <b>Broadcast</b>\n\n{text}")
            sent += 1
        except Exception:
            pass
    bot.reply_to(m, f"Broadcast sent to {sent} users.")
    add_activity(f"📢 Admin broadcast: {text}")

@bot.message_handler(commands=["draw_lottery"])
def cmd_draw_lottery(m):
    # admin quick draw shortcut
    if not is_admin(m.from_user.id): return
    # call lottery draw logic
    ensure_lottery_date()
    tickets = data["lottery"]["tickets"]
    total_tickets = sum(tickets.values())
    if total_tickets == 0:
        return bot.reply_to(m, "No tickets sold today.")
    pool = []
    for k, cnt in tickets.items():
        pool.extend([k]*cnt)
    winner = random.choice(pool)
    pot = total_tickets * LOTTERY_TICKET_COST
    prize = round(pot * 0.6, 2)
    ensure_user(int(winner))
    data["users"][winner]["balance"] += prize
    data["users"][winner]["transactions"].append(f"Lottery +{format_money(prize)}")
    add_activity(f"🎉 Lottery winner @{data['users'][winner]['uname']} won {format_money(prize)} (admin draw)")
    # reset
    data["lottery"] = {"date": "", "tickets": {}}
    for u in data["users"].values():
        u["tickets"] = 0
    save()
    bot.send_message(m.chat.id, f"🎉 Lottery drawn. Winner: @{data['users'][winner]['uname']} Prize: {format_money(prize)}")
    bot.send_message(int(winner), f"🎊 Congrats! You won the lottery: {format_money(prize)}")

# ------------------ FALLBACK ------------------
@bot.message_handler(func=lambda m: True)
def fallback(m):
    # update user name if changed
    uid = str(m.from_user.id)
    if uid in data["users"]:
        un = m.from_user.username or m.from_user.first_name or data["users"][uid]["uname"]
        if data["users"][uid].get("uname") != un:
            data["users"][uid]["uname"] = un
            save()
    bot.send_message(m.chat.id, "Use the menu below 👇", reply_markup=kb_main())

# ------------------ START POLLING ------------------
if __name__ == "__main__":
    print("✅ Bot running...")
    bot.infinity_polling()
