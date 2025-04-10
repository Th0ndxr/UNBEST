import discord
from discord.ext import commands
from discord import app_commands
import json, random, os
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

GACHA_COST = 5
ADMIN_ROLE_NAME = "Admin Gacha"
ANNOUNCE_CHANNEL_ID = 1359800062628069517  # ใส่ Channel ID จริง

RARITY_ROLES = {
    "SSR": "1%",
    "SR": "5%",
    "S": "10%",
    "R": "30%"
}

GACHA_POOL = [
    {"item": "1%", "rarity": "SSR", "rate": 1},
    {"item": "5%", "rarity": "SR", "rate": 5},
    {"item": "10%", "rarity": "S", "rate": 10},
    {"item": "30%", "rarity": "R", "rate": 21},
    {"item": "เกลือ", "rarity": "N", "rate": 21},
    {"item": "เกลือ", "rarity": "N", "rate": 21},
    {"item": "เกลือ", "rarity": "N", "rate": 21}
]

def load_userdata():
    if not os.path.exists("userdata.json"):
        return {}
    with open("userdata.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_userdata(data):
    with open("userdata.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def roll_item():
    roll = random.randint(1, 100)
    total = 0
    for i in GACHA_POOL:
        total += i["rate"]
        if roll <= total:
            return i
    return GACHA_POOL[-1]

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ บอทออนไลน์แล้ว: {bot.user}")

@bot.tree.command(name="gacha", description="สุ่มกาชา")
async def gacha(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_userdata()

    if user_id not in data or data[user_id]["balance"] < GACHA_COST:
        await interaction.response.send_message("❌ พอย์ทของคุณไม่เพียงพอ!", ephemeral=True)
        return

    data[user_id]["balance"] -= GACHA_COST
    data[user_id]["gacha_count"] = data[user_id].get("gacha_count", 0) + 1

    result = roll_item()
    data[user_id].setdefault("gacha_history", []).append({
        "item": result["item"],
        "rarity": result["rarity"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    role_name = RARITY_ROLES.get(result["rarity"])
    if role_name:
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role:
            await interaction.user.add_roles(role)
            role_msg = f"\n🎖️ ได้รับยศ: {role.mention}"
        else:
            role_msg = f"\n⚠️ ไม่พบ Role `{role_name}`"
    else:
        role_msg = ""

    announce_channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if announce_channel:
        await announce_channel.send(
            f"📢 {interaction.user.mention} ได้รับ **{result['item']}** ({result['rarity']}) จากกาชา!"
        )

    save_userdata(data)
    await interaction.response.send_message(
        f"🎉 คุณสุ่มกาชาได้: **{result['item']}** ({result['rarity']})!{role_msg}",
        ephemeral=False
    )

# ✅ /gacha10 (สุ่มหลายครั้ง)
@bot.tree.command(name="gacha10", description="สุ่มกาชาหลายครั้ง")
@app_commands.describe(times="จำนวนครั้ง (สูงสุด 10)")
async def multi_gacha(interaction: discord.Interaction, times: int):
    if times < 1 or times > 10:
        await interaction.response.send_message("❌ เลือกระหว่าง 1-10", ephemeral=True)
        return

    user_id = str(interaction.user.id)
    data = load_userdata()
    cost = times * GACHA_COST

    if user_id not in data or data[user_id]["balance"] < cost:
        await interaction.response.send_message("❌ พอยท์ไม่พอ", ephemeral=True)
        return

    data[user_id]["balance"] -= cost
    data[user_id]["gacha_count"] = data[user_id].get("gacha_count", 0) + times

    pulls, granted_roles = [], set()
    for _ in range(times):
        result = roll_item()
        pulls.append(f"- **{result['item']}** ({result['rarity']})")
        data[user_id].setdefault("gacha_history", []).append({
            "item": result["item"],
            "rarity": result["rarity"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        role_name = RARITY_ROLES.get(result["rarity"])
        if role_name:
            granted_roles.add(role_name)

    role_msgs = []
    for role_name in granted_roles:
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role:
            await interaction.user.add_roles(role)
            role_msgs.append(f"🎖️ ได้รับยศ: {role.mention}")
        else:
            role_msgs.append(f"⚠️ ไม่พบ Role `{role_name}`")

    save_userdata(data)
    await interaction.response.send_message(
        f"🎉 สุ่ม {times} ครั้ง ได้:\n" + "\n".join(pulls) + "\n\n" + "\n".join(role_msgs),
        ephemeral=False
    )

# ✅ /point (เช็คพอยท์)
@bot.tree.command(name="point", description="เช็คพอยท์ของคุณ")
async def check_point(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_userdata()
    balance = data.get(user_id, {}).get("balance", 0)
    gacha_count = data.get(user_id, {}).get("gacha_count", 0)
    history = data.get(user_id, {}).get("history", [])
    total_topup = sum(h.get("amount", 0) for h in history if h.get("type") == "topup")

    await interaction.response.send_message(
        f"📊 **Check Point**\n💸 พอยท์: `{balance}` บาท\n💰 เติมรวม: `{total_topup}` บาท\n🎲 สุ่มแล้ว: `{gacha_count}` ครั้ง",
        ephemeral=True
    )

# ✅ /admin (เพิ่ม/ลบพอยท์ ดูประวัติ)
@bot.tree.command(name="admin", description="🛠 จัดการผู้ใช้: เพิ่ม/ลบพอยท์ + ดูประวัติ")
@app_commands.describe(
    action="เลือกการกระทำ",
    member="สมาชิก",
    amount="จำนวนพอยท์"
)
@app_commands.choices(action=[
    app_commands.Choice(name="เพิ่มพอยท์", value="add"),
    app_commands.Choice(name="ลบพอยท์", value="remove"),
    app_commands.Choice(name="ดูประวัติ", value="history")
])
async def admin_manage(interaction: discord.Interaction, action: app_commands.Choice[str], member: discord.Member, amount: int = 0):
    if ADMIN_ROLE_NAME not in [role.name for role in interaction.user.roles]:
        await interaction.response.send_message("⛔ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (ต้องมี Role Admin)", ephemeral=True)
        return

    data = load_userdata()
    user_id = str(member.id)
    data.setdefault(user_id, {"balance": 0, "gacha_count": 0, "gacha_history": []})

    if action.value == "add":
        data[user_id]["balance"] += amount
        save_userdata(data)
        await interaction.response.send_message(f"✅ เพิ่ม {amount} พอยท์ให้ {member.mention}")

    elif action.value == "remove":
        data[user_id]["balance"] = max(0, data[user_id]["balance"] - amount)
        save_userdata(data)
        await interaction.response.send_message(f"🗑 ลบ {amount} พอยท์จาก {member.mention}")

    elif action.value == "history":
        history = data[user_id].get("gacha_history", [])[-5:]
        if not history:
            msg = f"📜 ไม่มีประวัติของ {member.mention}"
        else:
            msg = f"📜 ประวัติสุ่มล่าสุดของ {member.mention}:\n"
            msg += "\n".join(f"- `{h['timestamp']}`: {h['item']} ({h['rarity']})" for h in history)
        await interaction.response.send_message(msg)

# 🔑 Token ของคุณ
bot.run("MTM1OTUzNDA4NDUxODU3NjE3OA.G1BHTd.rn6W785yVO0CnN8O36_lOLGexQ90Z-GLYBnMMM")

# --- Merged from gacha.py ---

import discord
from discord.ext import commands
from discord import app_commands
import json, random, os
from datetime import datetime

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

GACHA_COST = 5  # ราคาในการสุ่ม 1 ครั้ง

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ บอทออนไลน์แล้ว: {bot.user}")

# ฟังก์ชันโหลดและบันทึก
def load_userdata():
    if not os.path.exists("userdata.json"):
        return {}
    with open("userdata.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_userdata(data):
    with open("userdata.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ตารางไอเทมกาชา
GACHA_POOL = [
    {"item": "1%", "rarity": "SSR", "rate": 1},
    {"item": "5%", "rarity": "SR", "rate": 5},
    {"item": "9%", "rarity": "S", "rate": 10},
    {"item": "20%", "rarity": "R", "rate": 21},
    {"item": "เกลือ", "rarity": "N", "rate": 21},
    {"item": "เกลือ", "rarity": "N", "rate": 21},
    {"item": "เกลือ", "rarity": "N", "rate": 21}
]

# ชื่อ role ตามระดับ
RARITY_ROLES = {
    "SSR": "1%",
    "SR": "5%",
    "S": "10%",
    "R": "30%"
}

# ฟังก์ชันสุ่มไอเทม
def roll_item():
    roll = random.randint(1, 100)
    total = 0
    for i in GACHA_POOL:
        total += i["rate"]
        if roll <= total:
            return i
    return GACHA_POOL[-1]

# ✅ คำสั่ง /gacha
@bot.tree.command(name="gacha", description="สุ่มกาชา")
async def gacha(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_userdata()

    if user_id not in data or data[user_id]["balance"] < GACHA_COST:
        await interaction.response.send_message("❌ พอยท์ของคุณไม่เพียงพอ!", ephemeral=True)
        return

    data[user_id]["balance"] -= GACHA_COST
    data[user_id]["gacha_count"] = data[user_id].get("gacha_count", 0) + 1

    result = roll_item()

    data[user_id].setdefault("gacha_history", []).append({
        "item": result["item"],
        "rarity": result["rarity"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    # แจก role
    rarity = result["rarity"]
    role_name = RARITY_ROLES.get(rarity)
    if role_name:
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role:
            await interaction.user.add_roles(role)
            role_msg = f"\n🎖️ ได้รับยศ: {role.mention}"
        else:
            role_msg = f"\n⚠️ ไม่พบ Role `{role_name}` (ต้องสร้างใน Discord ก่อน)"
    else:
        role_msg = ""

    save_userdata(data)

    await interaction.response.send_message(
        f"🎉 คุณสุ่มกาชาได้: **{result['item']}** ({result['rarity']})!{role_msg}",
        ephemeral=False
    )

# ✅ คำสั่ง /multi_gacha
@bot.tree.command(name="gacha10", description="สุ่มกาชาหลายครั้ง")
@app_commands.describe(times="จำนวนครั้ง (สูงสุด 10)")
async def multi_gacha(interaction: discord.Interaction, times: int):
    # โค้ดของคำสั่งตรงนี้
    user_id = str(interaction.user.id)
    data = load_userdata()

    if times < 1 or times > 10:
        await interaction.response.send_message("❌ กรุณาเลือกจำนวนครั้งระหว่าง 1 ถึง 10", ephemeral=True)
        return

    total_cost = GACHA_COST * times
    if user_id not in data or data[user_id]["balance"] < total_cost:
        await interaction.response.send_message("❌ พอยท์ของคุณไม่เพียงพอ!", ephemeral=True)
        return

    data[user_id]["balance"] -= total_cost
    data[user_id]["gacha_count"] = data[user_id].get("gacha_count", 0) + times

    pulls = []
    history = data[user_id].setdefault("gacha_history", [])
    granted_roles = set()

    for _ in range(times):
        result = roll_item()
        pulls.append(f"- **{result['item']}** ({result['rarity']})")
        history.append({
            "item": result["item"],
            "rarity": result["rarity"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        rarity = result["rarity"]
        role_name = RARITY_ROLES.get(rarity)
        if role_name:
            granted_roles.add(role_name)

    role_msgs = []
    for role_name in granted_roles:
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role:
            await interaction.user.add_roles(role)
            role_msgs.append(f"🎖️ ได้รับยศ: {role.mention}")
        else:
            role_msgs.append(f"⚠️ ไม่พบ Role `{role_name}`")

    save_userdata(data)

    await interaction.response.send_message(
        f"🎉 คุณสุ่มกาชา {times} ครั้ง ได้:\n" + "\n".join(pulls) + "\n\n" + "\n".join(role_msgs),
        ephemeral=False
    )

# 🔑 Token ของคุณ
bot.run("MTM1OTUzNDA4NDUxODU3NjE3OA.GhpMh4.Ofd1tr0JxaTyM_XtteIVURBg373qpLUUTB7kjI")