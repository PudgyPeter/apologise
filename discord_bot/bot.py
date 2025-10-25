# file: bot.py
import discord
from discord.ext import commands
import json
import os
import pathlib
from datetime import datetime
import asyncio
from discord.ui import Button, View

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 1430766113721028658
ALERT_CHANNEL_ID = 1431130781975187537
KEYWORDS = ["jordan", "pudge", "pudgy", "jorganism"]
FUZZY_TOLERANCE = 2

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

# ⭐ updated: writes both JSON and TXT for each event
def append_log(entry: dict):
    try:
        log_path_json = get_daily_log_path()
        logs = load_log(log_path_json)
        logs.append(entry)
        with open(log_path_json, "w", encoding="utf-8") as f:
            json.dump(logs[-5000:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[💥] JSON logging error: {e}")
    append_log_text(entry)

def append_log_text(entry: dict):
    log_file_txt = get_daily_log_path().with_suffix(".txt")
    log_file_txt.parent.mkdir(parents=True, exist_ok=True)
    ts = entry.get("readable_time") or entry.get("created_at", "")
    content = entry.get("content", "(no text)")
    type_emoji = {"create": "💬", "edit": "✏️", "delete": "🗑️"}.get(entry.get("type"), "💬")
    if entry["type"] == "edit":
        before = entry.get("before", "(no text)")
        after = content
        log_line = f"[{ts}] ({entry['channel']}) {entry['author']} {type_emoji}\nBefore: {before}\nAfter : {after}\n\n"
    elif entry["type"] == "delete":
        log_line = f"[{ts}] ({entry['channel']}) {entry['author']} {type_emoji}\n{content}\n\n"
    else:
        log_line = f"[{ts}] ({entry['channel']}) {entry['author']} {type_emoji}\n{content}\n\n"
    with open(log_file_txt, "a", encoding="utf-8") as f:
        f.write(log_line)

# --- DISCORD INTENTS ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- FUZZY UTILS ---
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

# --- EMBED CREATION ---
# ⭐ improved: allows images/gifs/links to embed properly
def create_message_embed(message: discord.Message) -> discord.Embed:
    user = message.author
    color = user.color if user.color.value != 0 else discord.Color.blurple()
    embed = discord.Embed(
        description=message.content or "(no text)",
        color=color,
        timestamp=message.created_at
    )
    embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else discord.Embed.Empty)
    embed.set_footer(text=f"#{message.channel.name}")
    if message.attachments:
        for a in message.attachments:
            if a.content_type and a.content_type.startswith("image/"):
                embed.set_image(url=a.url)
            else:
                embed.add_field(name="Attachment", value=a.url, inline=False)
    if message.embeds:
        for e in message.embeds:
            if e.url:
                embed.add_field(name="Linked Embed", value=e.url, inline=False)
    return embed

# --- EVENTS ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    entry = {
        "id": message.id,
        "author": str(message.author),
        "content": message.content,
        "channel": message.channel.name,
        "created_at": message.created_at.isoformat(),
        "readable_time": message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "type": "create",
    }
    append_log(entry)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel and message.channel.id != LOG_CHANNEL_ID:
        embed = create_message_embed(message)
        await log_channel.send(embed=embed)

    if fuzzy_match(message.content, KEYWORDS):
        alert = discord.Embed(
            title="🚨 Keyword Detected!",
            description=f"**[{message.author}]** mentioned a watched term in <#{message.channel.id}>:\n\n> {message.content}",
            color=discord.Color.red(),
        )
        alert.set_thumbnail(url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty)
        alert.set_footer(text=f"Detected at {datetime.utcnow().strftime('%H:%M:%S UTC')}")
        alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            jump_button = Button(label="Jump to Message", style=discord.ButtonStyle.link, url=message.jump_url)
            view = View()
            view.add_item(jump_button)
            await alert_channel.send(embed=alert, view=view)

    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    entry = {
        "id": before.id,
        "author": str(before.author),
        "content": after.content,
        "channel": before.channel.name,
        "created_at": datetime.utcnow().isoformat(),
        "readable_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "type": "edit",
        "before": before.content or "(no text)"
    }
    append_log(entry)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title=f"✏️ Edited Message by {before.author}", color=discord.Color.gold())
        embed.add_field(name="Before", value=before.content or "(no text)", inline=False)
        embed.add_field(name="After", value=after.content or "(no text)", inline=False)
        await log_channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    entry = {
        "id": message.id,
        "author": str(message.author),
        "content": message.content,
        "channel": message.channel.name,
        "created_at": datetime.utcnow().isoformat(),
        "readable_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "type": "delete",
    }
    append_log(entry)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author}\n**Channel:** <#{message.channel.id}>\n\n> {message.content or '(no text)'}",
            color=discord.Color.dark_gray(),
        )
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty)
        await log_channel.send(embed=embed)

# --- LOG COMMANDS ---
@bot.group(invoke_without_command=True)
async def logs(ctx):
    await ctx.send("Use `!logs list`, `!logs download <date>`, or `!logs search <term>`")

@logs.command(name="list")
async def logs_list(ctx):
    files = sorted(BASE_LOG_DIR.glob("logs_*.txt"))
    if not files:
        await ctx.send("No logs found yet.")
        return
    embed = discord.Embed(title="Available Logs", color=discord.Color.blurple())
    view = View()
    for f in files:
        date_str = f.stem.replace("logs_", "")
        size_kb = f.stat().st_size // 1024
        embed.add_field(name=f"🗓️ {date_str} ({size_kb} KB)", value=f"Click below to download.", inline=False)
        btn = Button(label=f"Download {date_str}", style=discord.ButtonStyle.primary)
        async def download_callback(interaction, file=f):
            await interaction.response.send_message(file=discord.File(file, filename=f"{file.stem}.txt"), ephemeral=True)
        btn.callback = download_callback
        view.add_item(btn)
    await ctx.send(embed=embed, view=view)

@logs.command(name="download")
async def logs_download(ctx, date: str = None):
    if date is None or date.lower() == "today":
        log_file_txt = get_daily_log_path().with_suffix(".txt")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
            log_file_txt = BASE_LOG_DIR / f"logs_{date}.txt"
        except ValueError:
            await ctx.send("Please use the `YYYY-MM-DD` format.")
            return
    if not log_file_txt.exists():
        await ctx.send(f"No log file found for `{date or 'today'}`.")
        return
    await ctx.send(file=discord.File(log_file_txt, filename=f"{log_file_txt.stem}.txt"))

# ⭐ NEW: fuzzy search command
@logs.command(name="search")
async def logs_search(ctx, *, term: str):
    await ctx.trigger_typing()
    results = []
    for log_file in sorted(BASE_LOG_DIR.glob("logs_*.json")):
        data = load_log(log_file)
        for entry in data:
            if fuzzy_contains(entry.get("content", ""), term, FUZZY_TOLERANCE):
                results.append(entry)
        if len(results) > 100:
            break
    if not results:
        await ctx.send(f"No results found for `{term}`.")
        return
    per_page = 10
    total_pages = (len(results) + per_page - 1) // per_page
    def make_page(page):
        start, end = page * per_page, (page + 1) * per_page
        embed = discord.Embed(title=f"🔍 Results for '{term}' ({page+1}/{total_pages})", color=discord.Color.green())
        for r in results[start:end]:
            ts = datetime.fromisoformat(r["created_at"]).strftime("%H:%M:%S")
            embed.add_field(name=f"{r['author']} ({r['channel']})", value=f"[{ts}] {r['content'][:150]}", inline=False)
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
            if str(reaction.emoji) == "⏮️": page = 0
            elif str(reaction.emoji) == "◀️" and page > 0: page -= 1
            elif str(reaction.emoji) == "▶️" and page < total_pages - 1: page += 1
            elif str(reaction.emoji) == "⏭️": page = total_pages - 1
            await msg.edit(embed=make_page(page))
        except asyncio.TimeoutError:
            break

@bot.event
async def on_ready():
    print(f"[✅] Logged in as {bot.user} (ID: {bot.user.id})")

bot.run(TOKEN)