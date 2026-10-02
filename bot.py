import os, random, sqlite3, discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="c!", intents=intents)

db = sqlite3.connect("cowo.db")
cur = db.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY, coins INTEGER DEFAULT 100, xp INTEGER DEFAULT 0,
level INTEGER DEFAULT 1, daily INTEGER DEFAULT 0)""")
cur.execute("""CREATE TABLE IF NOT EXISTS inventory(
user_id INTEGER, item TEXT, amount INTEGER DEFAULT 1,
PRIMARY KEY(user_id,item))""")
db.commit()

ANIMALS = [
    ("Cat", 20), ("Dog", 30), ("Fox", 50), ("Wolf", 80),
    ("Tiger", 150), ("Dragon", 500), ("Phoenix", 1000)
]
SHOP = {"cookie": 25, "potion": 100, "diamond": 500}

def user(uid):
    cur.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
    db.commit()
    cur.execute("SELECT coins,xp,level FROM users WHERE id=?", (uid,))
    return cur.fetchone()

@bot.event
async def on_ready():
    print(f"COWO online as {bot.user}")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(e)

@bot.command()
async def balance(ctx):
    coins, xp, level = user(ctx.author.id)
    await ctx.send(f"💰 **{ctx.author.display_name}**: `{coins}` coins | ⭐ Level `{level}`")

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def hunt(ctx):
    user(ctx.author.id)
    animal, value = random.choice(ANIMALS)
    bonus = random.randint(0, value)
    coins = value + bonus
    cur.execute("UPDATE users SET coins=coins+?, xp=xp+10 WHERE id=?", (coins, ctx.author.id))
    cur.execute("""INSERT INTO inventory(user_id,item,amount) VALUES(?,?,1)
                   ON CONFLICT(user_id,item) DO UPDATE SET amount=amount+1""",
                (ctx.author.id, animal))
    db.commit()
    await ctx.send(f"🐾 You hunted a **{animal}** and earned **{coins} 💰**!")

@hunt.error
async def hunt_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Wait `{error.retry_after:.1f}s` before hunting again.")

@bot.command()
async def daily(ctx):
    import time
    coins, xp, level = user(ctx.author.id)
    cur.execute("SELECT daily FROM users WHERE id=?", (ctx.author.id,))
    last = cur.fetchone()[0]
    now = int(time.time())
    if now - last < 86400:
        await ctx.send("🎁 You already claimed your daily reward. Come back later!")
        return
    reward = random.randint(100, 300)
    cur.execute("UPDATE users SET coins=coins+?, daily=? WHERE id=?", (reward, now, ctx.author.id))
    db.commit()
    await ctx.send(f"🎁 Daily reward: **{reward} 💰**")

@bot.command()
async def inventory(ctx):
    user(ctx.author.id)
    cur.execute("SELECT item,amount FROM inventory WHERE user_id=? ORDER BY amount DESC", (ctx.author.id,))
    rows = cur.fetchall()
    if not rows:
        await ctx.send("🎒 Your inventory is empty.")
        return
    text = "\n".join(f"• **{item}** × `{amount}`" for item, amount in rows)
    await ctx.send(f"🎒 **{ctx.author.display_name}'s Inventory**\n{text}")

@bot.command()
async def shop(ctx):
    text = "\n".join(f"• `{item}` — **{price} 💰**" for item, price in SHOP.items())
    await ctx.send(f"🛒 **COWO Shop**\n{text}\n\nBuy with `c!buy <item>`")

@bot.command()
async def buy(ctx, item: str):
    item = item.lower()
    if item not in SHOP:
        await ctx.send("❌ Item not found. Use `c!shop`.")
        return
    coins, xp, level = user(ctx.author.id)
    price = SHOP[item]
    if coins < price:
        await ctx.send("❌ You don't have enough coins.")
        return
    cur.execute("UPDATE users SET coins=coins-? WHERE id=?", (price, ctx.author.id))
    cur.execute("""INSERT INTO inventory(user_id,item,amount) VALUES(?,?,1)
                   ON CONFLICT(user_id,item) DO UPDATE SET amount=amount+1""",
                (ctx.author.id, item))
    db.commit()
    await ctx.send(f"🛍️ Bought **{item}** for **{price} 💰**!")

@bot.command()
async def battle(ctx, member: discord.Member):
    if member.bot or member.id == ctx.author.id:
        await ctx.send("❌ Choose another player.")
        return
    winner = random.choice([ctx.author, member])
    reward = random.randint(50, 200)
    user(ctx.author.id); user(member.id)
    cur.execute("UPDATE users SET coins=coins+? WHERE id=?", (reward, winner.id))
    db.commit()
    await ctx.send(f"⚔️ **{ctx.author.display_name}** vs **{member.display_name}**\n🏆 Winner: **{winner.display_name}**\n💰 Prize: `{reward}`")

@bot.command()
async def leaderboard(ctx):
    cur.execute("SELECT id,coins FROM users ORDER BY coins DESC LIMIT 10")
    rows = cur.fetchall()
    if not rows:
        await ctx.send("🏆 No players yet.")
        return
    lines = []
    for i,(uid,coins) in enumerate(rows,1):
        member = ctx.guild.get_member(uid)
        name = member.display_name if member else f"User {uid}"
        lines.append(f"**{i}.** {name} — `{coins} 💰`")
    await ctx.send("🏆 **COWO Leaderboard**\n" + "\n".join(lines))

@bot.command()
@commands.has_permissions(administrator=True)
async def addcoins(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be positive.")
        return
    user(member.id)
    cur.execute("UPDATE users SET coins=coins+? WHERE id=?", (amount, member.id))
    db.commit()
    await ctx.send(f"👑 Added **{amount} 💰** to {member.mention}.")

@bot.command()
async def profile(ctx):
    coins, xp, level = user(ctx.author.id)
    await ctx.send(
        f"👤 **{ctx.author.display_name}'s COWO Profile**\n"
        f"💰 Coins: `{coins}`\n⭐ XP: `{xp}`\n🎚️ Level: `{level}`"
    )

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**🐮 COWO COMMANDS**\n"
        "`c!hunt` • hunt animals\n"
        "`c!balance` • check coins\n"
        "`c!daily` • daily reward\n"
        "`c!inventory` • inventory\n"
        "`c!shop` • shop\n"
        "`c!buy <item>` • buy item\n"
        "`c!battle @user` • battle\n"
        "`c!leaderboard` • top players\n"
        "`c!profile` • profile\n"
        "`c!addcoins @user <amount>` • admin"
    )

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing in .env")
bot.run(TOKEN)
