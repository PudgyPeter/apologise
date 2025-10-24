# file: bot.py
import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime
import pathlib
import asyncio

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 123456789012345678  # <- Replace with your log channel ID
KEYWORDS = ["jordan", "pudge", "pudgy"]
FUZZY_TOLERANCE = 2  # allowable typos for search

# --- PATHS ---
RAILWAY_DIR = pathlib.Path("/mnt/data")
LOCAL_DIR = pathlib.Path(os.getcwd()) / "data"

if RAILWAY_DIR.exists() and os.access(RAILWAY_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_DIR
else:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    BASE_LOG_DIR = LOCAL_DIR

print(f"[📂] Using persistent log directory at: {BASE_LOG_DIR}")

# --- DAILY LOG HELPERS ---
def get_daily_log_path() -> pathlib.Path:
    today_str = datetime.utcnow().strftime("logs_%Y-%m-%d.json")
    return BASE_LOG_DIR / today_str

def load_log(log_path: pathlib.Path):
    if not log_path.exists():
        log_path.write_text("[]", encoding="utf-8")
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[⚠️] Log file {log_path.name} corrupted, resetting.")
        log_path.write_text("[]", encoding="utf-8")
        return []

def append_log(entry: dict):
    try:
        log_path = get_daily_log_path()
        logs = load_log(log_path)
        logs.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs[-5000:], f, indent=2)
    except Exception as e:
        print(f"[💥] Logging error: {e}")

# --- DISCORD INTENTS ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- UTILS ---
def levenshtein(a, b):
    if len(a) < len(b):
        return levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    previous_row = range(len(b) + 1)
    for i, ca in enumerate(a):
        current_row = [i + 1]
        for j, cb in enumerate(b):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (ca != cb)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def fuzzy_contains(text, keyword, tolerance=2):
    text = text.lower()
    keyword = keyword.lower()
    for i in range(len(text) - len(keyword) + 1):
        window = text[i:i + len(keyword)]
        if levenshtein(window, keyword) <= tolerance:
            return True
    return False

def fuzzy_match(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower or fuzzy_contains(text_lower, kw, FUZZY_TOLERANCE):
            return True
    return False

def create_message_embed(messages: list[discord.Message]) -> discord.Embed:
    user = messages[0].author
    color = user.color if user.color.value != 0 else discord.Color.blurple()
    embed = discord.Embed(title=f"💬 Message from {user.display_name}", color=color)
    embed.set_thumbnail(url=user.avatar.url if user.avatar else discord.Embed.Empty)
    m = messages[0]
    desc = f"**[{m.created_at.strftime('%H:%M:%S')}]** {m.content or '(no text)'}"
    if m.attachments:
        desc += "\n📎 " + ", ".join(a.url for a in m.attachments)
    embed.description = desc
    embed.set_footer(text=f"#{m.channel.name} • {m.created_at.strftime('%b %d, %H:%M')}")
    return embed

# --- EVENTS ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    append_log({
        "id": message.id,
        "author": str(message.author),
        "content": message.content,
        "channel": message.channel.name,
        "created_at": message.created_at.isoformat(),
        "type": "create",
    })

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel or message.channel.id == LOG_CHANNEL_ID:
        return

    embed = create_message_embed([message])
    await log_channel.send(embed=embed)

    if fuzzy_match(message.content, KEYWORDS):
        alert = discord.Embed(
            title="🚨 Keyword Detected!",
            description=f"**[{message.author}]** mentioned a watched term in <#{message.channel.id}>:\n\n> {message.content}",
            color=discord.Color.red(),
        )
        alert.set_thumbnail(url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty)
        alert.set_footer(text=f"Detected at {datetime.utcnow().strftime('%H:%M:%S UTC')}")
        await log_channel.send(embed=alert)

    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    append_log({
        "id": before.id,
        "author": str(before.author),
        "content": after.content,
        "channel": before.channel.name,
        "created_at": datetime.utcnow().isoformat(),
        "type": "edit",
    })
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title=f"✏️ Edited Message by {before.author}",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Before", value=before.content or "(no text)", inline=False)
        embed.add_field(name="After", value=after.content or "(no text)", inline=False)
        embed.set_footer(text=datetime.utcnow().strftime("%b %d • %H:%M:%S UTC"))
        await log_channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    append_log({
        "id": message.id,
        "author": str(message.author),
        "content": message.content,
        "channel": message.channel.name,
        "created_at": datetime.utcnow().isoformat(),
        "type": "delete",
    })
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author}\n**Channel:** <#{message.channel.id}>\n\n> {message.content or '(no text)'}",
            color=discord.Color.dark_gray(),
        )
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty)
        embed.set_footer(text=datetime.utcnow().strftime("%b %d • %H:%M:%S UTC"))
        await log_channel.send(embed=embed)

# --- LOG COMMANDS ---
@bot.group(invoke_without_command=True)
async def logs(ctx):
    await ctx.send("Use `!logs list` or `!logs search <term>`")

@logs.command(name="list")
async def logs_list(ctx):
    files = sorted(BASE_LOG_DIR.glob("logs_*.json"))
    if not files:
        await ctx.send("No logs found yet.")
        return
    desc = "\n".join(f"🗓️ `{f.name.replace('logs_', '').replace('.json','')}` ({f.stat().st_size//1024} KB)" for f in files)
    await ctx.send(embed=discord.Embed(title="Available Logs", description=desc, color=discord.Color.blurple()))

@logs.command(name="search")
async def logs_search(ctx, term: str, date: str = None):
    await ctx.trigger_typing()
    results = []
    if date and date.lower() == "today":
        log_files = [get_daily_log_path()]
    else:
        log_files = sorted(BASE_LOG_DIR.glob("logs_*.json"))

    for log_file in log_files:
        data = load_log(log_file)
        for entry in data:
            content = entry.get("content", "")
            if fuzzy_contains(content, term, FUZZY_TOLERANCE) or re.search(term, content, re.IGNORECASE):
                results.append(entry)
        if len(results) > 100:
            break

    if not results:
        await ctx.send(f"No results found for `{term}`.")
        return

    # Pagination setup
    per_page = 10
    total_pages = (len(results) + per_page - 1) // per_page

    def make_page(page):
        start, end = page * per_page, (page + 1) * per_page
        chunk = results[start:end]
        embed = discord.Embed(title=f"🔍 Results for `{term}` — Page {page+1}/{total_pages}", color=discord.Color.green())
        for r in chunk:
            ts = datetime.fromisoformat(r["created_at"]).strftime("%b %d • %H:%M")
            snippet = (r['content'][:180] + "...") if len(r['content']) > 180 else r['content']
            embed.add_field(name=f"{r['author']} — #{r['channel']} ({r['type']})", value=f"**[{ts}]** {snippet}", inline=False)
        return embed

    page = 0
    msg = await ctx.send(embed=make_page(page))

    for emoji in ["⏮️", "◀️", "▶️", "⏭️"]:
        await msg.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⏮️", "◀️", "▶️", "⏭️"]

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)
            await msg.remove_reaction(reaction.emoji, user)

            if str(reaction.emoji) == "⏮️":
                page = 0
            elif str(reaction.emoji) == "◀️" and page > 0:
                page -= 1
            elif str(reaction.emoji) == "▶️" and page < total_pages - 1:
                page += 1
            elif str(reaction.emoji) == "⏭️":
                page = total_pages - 1

            await msg.edit(embed=make_page(page))
        except asyncio.TimeoutError:
            break

@bot.event
async def on_ready():
    print(f"[✅] Logged in as {bot.user} (ID: {bot.user.id})")

bot.run(TOKEN)
