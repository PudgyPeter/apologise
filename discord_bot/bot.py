# file: bot.py
import discord
from discord.ext import commands, tasks
import json
import os
import pathlib
from datetime import datetime, timedelta
import re
import asyncio
from discord.ui import Button, View

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 1430766113721028658
ALERT_CHANNEL_ID = 1431130781975187537
KEYWORDS = ["jordan", "pudge", "pudgy", "jorganism"]
FUZZY_TOLERANCE = 2
GROUP_WINDOW = 10  # seconds to group messages
GROUP_PRUNE = 60   # seconds after which an inactive group is pruned

# --- PATHS ---
RAILWAY_DIR = pathlib.Path("/mnt/data")
LOCAL_DIR = pathlib.Path(os.getcwd()) / "data"
if RAILWAY_DIR.exists() and os.access(RAILWAY_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_DIR
else:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    BASE_LOG_DIR = LOCAL_DIR
BASE_LOG_DIR.mkdir(parents=True, exist_ok=True)
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
            json.dump(logs[-5000:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[💥] JSON logging error: {e}")
    append_log_text(entry)

def append_log_text(entry: dict):
    log_file_txt = get_daily_log_path().with_suffix(".txt")
    log_file_txt.parent.mkdir(parents=True, exist_ok=True)
    ts = entry.get("readable_time") or entry.get("created_at", "")
    content = entry.get("content", "(no text)")
    type_emoji = {"create": "💬", "edit": "✏️", "delete": "🗑️", "reaction": "🔁"}.get(entry.get("type"), "💬")
    if entry["type"] == "edit":
        before = entry.get("before", "(no text)")
        after = content
        log_line = f"[{ts}] ({entry['channel']}) {entry['author']} {type_emoji}\nBefore: {before}\nAfter : {after}\n\n"
    elif entry["type"] == "delete":
        log_line = f"[{ts}] ({entry['channel']}) {entry['author']} {type_emoji}\n{content}\n\n"
    elif entry["type"] == "reaction":
        emoji = entry.get("emoji")
        count = entry.get("count", 0)
        users = ", ".join(entry.get("users", []))
        log_line = f"[{ts}] ({entry['channel']}) {entry['author']} {type_emoji}\nReaction: {emoji} x{count} ({users}) on message {entry.get('message_id')}\n\n"
    else:
        log_line = f"[{ts}] ({entry['channel']}) {entry['author']} {type_emoji}\n{content}\n\n"
    with open(log_file_txt, "a", encoding="utf-8") as f:
        f.write(log_line)

# --- DISCORD SETUP ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.reactions = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- UTILS: fuzzy match ---
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

def fuzzy_contains(text, keyword, tolerance=FUZZY_TOLERANCE):
    text = text.lower()
    keyword = keyword.lower()
    if keyword in text:
        return True
    for i in range(len(text) - len(keyword) + 1):
        window = text[i:i + len(keyword)]
        if levenshtein(window, keyword) <= tolerance:
            return True
    return False

def fuzzy_match(text: str, keywords: list[str]) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for kw in keywords:
        if fuzzy_contains(text_lower, kw):
            return True
    return False

# --- IMAGE/GIF LINK DETECTION ---
def find_image_url(text: str):
    if not text:
        return None
    pattern = re.compile(
        r"(https?://(?:cdn\.discordapp\.com|media\.discordapp\.net|i\.imgur\.com/\S+|tenor\.com/.+|giphy\.com/.+|media\.giphy\.com/media/\S+/\S+\.gif))",
        re.IGNORECASE
    )
    match = pattern.search(text)
    return match.group(1) if match else None

# --- GROUPING CACHE & MAPPINGS ---
group_cache = {}  # (author_id, channel_id) -> {'last_time': dt, 'messages': [entry], 'log_channel_id': int, 'log_message_id': int}
message_to_group = {}  # message_id -> (group_key, index)

# build entry helper
async def build_entry_from_message(message: discord.Message):
    attachments = [a.url for a in message.attachments]
    reply_preview = None
    if message.reference and message.reference.message_id:
        try:
            ref = await message.channel.fetch_message(message.reference.message_id)
            preview = (ref.content or "(no text)").strip()
            if len(preview) > 140:
                preview = preview[:137] + "..."
            reply_preview = {"author": str(ref.author), "content": preview, "id": ref.id}
        except Exception:
            reply_preview = {"author": "Unknown", "content": "(unavailable)", "id": message.reference.message_id}
    return {
        "message_id": message.id,
        "author": str(message.author),
        "author_display": message.author.display_name,
        "content": message.content or "",
        "created_at": message.created_at,
        "created_at_iso": message.created_at.isoformat(),
        "readable_time": message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "channel": message.channel.name,
        "attachments": attachments,
        "reactions": {},  # emoji -> {"count": int, "users": [names]}
        "reply_preview": reply_preview
    }

# --- EMBED BUILDING & UPDATE ---
def build_group_embed(group_key):
    data = group_cache.get(group_key)
    if not data or not data["messages"]:
        return None
    first = data["messages"][0]
    author_display = first["author_display"]
    color = discord.Color.blurple()
    # try to set color based on member role (best-effort)
    try:
        guild = data.get("guild")
        if guild:
            member = guild.get_member(int(first["author"].split("#")[0]) )  # best-effort, ignore if fails
    except Exception:
        pass
    embed = discord.Embed(color=color, timestamp=data["messages"][-1]["created_at"])
    embed.set_author(name=f"{author_display}")
    # thumbnail = sender avatar URL stored separately in cache
    if data.get("thumbnail"):
        embed.set_thumbnail(url=data["thumbnail"])
    description_parts = []
    for m in data["messages"]:
        ts = m["created_at"].strftime("%H:%M:%S")
        line = f"**[{ts}]** {m['content'] or '(no text)'}"
        if m["reply_preview"]:
            rp = m["reply_preview"]
            line = f"↩️ replying to **{rp['author']}**: `{rp['content']}`\n{line}"
        if m["attachments"]:
            for i, aurl in enumerate(m["attachments"]):
                if i == 0:
                    # already set image separately if it's an image; we still show the URL for others
                    pass
                else:
                    line += f"\n📎 {aurl}"
        # reactions summary
        if m["reactions"]:
            parts = []
            for emoji, info in m["reactions"].items():
                users = info.get("users", [])
                snippet = ", ".join(users[:5])
                parts.append(f"{emoji} x{info.get('count',0)} ({snippet})")
            line += f"\n🔁 Reactions: {' • '.join(parts)}"
        description_parts.append(line)
    embed.description = "\n\n".join(description_parts)[:4000]
    embed.set_footer(text=f"#{data['channel_name']} • {len(data['messages'])} messages")
    # set image: prefer first attachment image or detected link image
    if data.get("image_url"):
        embed.set_image(url=data["image_url"])
    return embed

# helper to send or update group
async def add_message_to_group(message: discord.Message):
    group_key = (message.author.id, message.channel.id)
    now = datetime.utcnow()
    entry = await build_entry_from_message(message)
    # add thumbnail url (author avatar)
    thumbnail = message.author.avatar.url if message.author.avatar else None
    existing = group_cache.get(group_key)
    if existing and (now - existing["last_time"]).total_seconds() <= GROUP_WINDOW:
        existing["messages"].append(entry)
        existing["last_time"] = now
        # map message id
        idx = len(existing["messages"]) - 1
        message_to_group[message.id] = (group_key, idx)
        # update image_url if not set and first attachment is image or link
        if not existing.get("image_url"):
            if entry["attachments"]:
                # set first image attachment if any
                for aurl in entry["attachments"]:
                    if re.search(r"\.(gif|png|jpe?g|webp)$", aurl, re.IGNORECASE):
                        existing["image_url"] = aurl
                        break
            else:
                link_img = find_image_url(entry["content"])
                if link_img:
                    existing["image_url"] = link_img
        # update embed
        try:
            log_chan = bot.get_channel(existing["log_channel_id"])
            if log_chan:
                log_msg = await log_chan.fetch_message(existing["log_message_id"])
                # update thumbnail if not present
                existing["thumbnail"] = thumbnail
                new_embed = build_group_embed(group_key)
                if new_embed:
                    await log_msg.edit(embed=new_embed)
        except Exception as e:
            print(f"[💥] update group embed error: {e}")
    else:
        # create a new group
        group_cache[group_key] = {
            "last_time": now,
            "messages": [entry],
            "log_channel_id": message.channel.id,  # will update below to real log channel id
            "log_message_id": None,
            "thumbnail": thumbnail,
            "image_url": None,
            "channel_name": message.channel.name,
            "guild": message.guild,
        }
        # set image_url if available
        if entry["attachments"]:
            for aurl in entry["attachments"]:
                if re.search(r"\.(gif|png|jpe?g|webp)$", aurl, re.IGNORECASE):
                    group_cache[group_key]["image_url"] = aurl
                    break
        else:
            link_img = find_image_url(entry["content"])
            if link_img:
                group_cache[group_key]["image_url"] = link_img
        # send embed to log channel
        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if not log_chan:
            return
        group_cache[group_key]["log_channel_id"] = LOG_CHANNEL_ID
        embed = build_group_embed(group_key)
        try:
            sent = await log_chan.send(embed=embed)
            group_cache[group_key]["log_message_id"] = sent.id
            message_to_group[message.id] = (group_key, 0)
        except Exception as e:
            print(f"[💥] send group embed error: {e}")

# --- PRUNE TASK ---
@tasks.loop(seconds=15)
async def prune_groups():
    now = datetime.utcnow()
    to_remove = []
    for key, data in list(group_cache.items()):
        if (now - data["last_time"]).total_seconds() >= GROUP_PRUNE:
            to_remove.append(key)
    for k in to_remove:
        group_cache.pop(k, None)

@prune_groups.before_loop
async def before_prune():
    await bot.wait_until_ready()

# --- EVENTS: message / edit / delete / reactions ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    # log entry
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
    # mirror and grouping
    await add_message_to_group(message)
    # KEYWORD ALERT: only when there is non-link text and no attachments
    has_attachments = len(message.attachments) > 0
    content_lower = (message.content or "").strip().lower()
    looks_like_link = bool(re.match(r"^https?://\S+$", content_lower))
    has_text = bool(content_lower and not looks_like_link)
    if has_text and not has_attachments and fuzzy_match(message.content, KEYWORDS):
        alert = discord.Embed(
            title="🚨 Keyword Detected!",
            description=f"**[{message.author}]** mentioned a watched term in <#{message.channel.id}>:\n\n> {message.content}",
            color=discord.Color.red(),
            timestamp=message.created_at
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
    # update cache if present
    mg = message_to_group.get(before.id)
    if mg:
        group_key, idx = mg
        data = group_cache.get(group_key)
        if data and idx < len(data["messages"]):
            data["messages"][idx]["content"] = after.content or ""
            data["messages"][idx]["created_at"] = after.edited_at or datetime.utcnow()
            # rebuild embed
            try:
                log_chan = bot.get_channel(data["log_channel_id"])
                log_msg = await log_chan.fetch_message(data["log_message_id"])
                new_embed = build_group_embed(group_key)
                if new_embed:
                    await log_msg.edit(embed=new_embed)
            except Exception as e:
                print(f"[💥] update on edit error: {e}")
    else:
        # send a separate edited embed
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title=f"✏️ Edited Message by {before.author}", color=discord.Color.gold(), timestamp=datetime.utcnow())
            embed.add_field(name="Before", value=before.content or "(no text)", inline=False)
            embed.add_field(name="After", value=after.content or "(no text)", inline=False)
            embed.set_footer(text=datetime.utcnow().strftime("%b %d • %H:%M:%S UTC"))
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
    mg = message_to_group.get(message.id)
    if mg:
        group_key, idx = mg
        data = group_cache.get(group_key)
        if data and idx < len(data["messages"]):
            data["messages"][idx]["content"] = "(message deleted)"
            try:
                log_chan = bot.get_channel(data["log_channel_id"])
                log_msg = await log_chan.fetch_message(data["log_message_id"])
                new_embed = build_group_embed(group_key)
                if new_embed:
                    await log_msg.edit(embed=new_embed)
            except Exception as e:
                print(f"[💥] update on delete error: {e}")
    else:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🗑️ Message Deleted",
                description=f"**Author:** {message.author}\n**Channel:** <#{message.channel.id}>\n\n> {message.content or '(no text)'}",
                color=discord.Color.dark_gray(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty)
            embed.set_footer(text=datetime.utcnow().strftime("%b %d • %H:%M:%S UTC"))
            await log_channel.send(embed=embed)

# --- REACTIONS ---
async def update_reaction_on_embed(message: discord.Message, reaction: discord.Reaction):
    mg = message_to_group.get(message.id)
    # prepare reaction summary
    try:
        users = await reaction.users().flatten()
        user_names = [str(u) for u in users if not u.bot][:5]
    except Exception:
        user_names = []
    emoji = str(reaction.emoji)
    count = reaction.count
    if mg:
        group_key, idx = mg
        data = group_cache.get(group_key)
        if not data:
            return
        # store into entry
        entry = data["messages"][idx]
        entry["reactions"][emoji] = {"count": count, "users": user_names}
        # edit embed
        try:
            log_chan = bot.get_channel(data["log_channel_id"])
            log_msg = await log_chan.fetch_message(data["log_message_id"])
            new_embed = build_group_embed(group_key)
            if new_embed:
                await log_msg.edit(embed=new_embed)
        except Exception as e:
            print(f"[💥] update reaction embed error: {e}")
    else:
        # message not mapped; send small reaction embed
        entry = {
            "id": message.id,
            "author": str(message.author),
            "content": message.content,
            "channel": message.channel.name,
            "created_at": datetime.utcnow().isoformat(),
            "readable_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "type": "reaction",
            "emoji": emoji,
            "count": count,
            "users": user_names,
            "message_id": message.id
        }
        append_log(entry)
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="🔁 Reaction Update", color=discord.Color.orange(), timestamp=datetime.utcnow())
            embed.add_field(name="Message", value=f"{message.content[:200] or '(no text)'}", inline=False)
            embed.add_field(name="Reaction", value=f"{emoji} x{count} — {', '.join(user_names[:5])}", inline=False)
            embed.set_footer(text=f"#{message.channel.name}")
            await log_channel.send(embed=embed)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    message = reaction.message
    await update_reaction_on_embed(message, reaction)

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    message = reaction.message
    await update_reaction_on_embed(message, reaction)

# --- PRUNE START ---
@bot.event
async def on_ready():
    prune_groups.start()
    print(f"[✅] Logged in as {bot.user} (ID: {bot.user.id})")

# --- LOG COMMANDS (list/download/search: simplified) ---
@bot.group(invoke_without_command=True)
async def logs(ctx):
    await ctx.send("Use `!logs list`, `!logs search <term>`, or `!logs download <date>`")

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
            await ctx.send("Please provide the date in `YYYY-MM-DD` format.")
            return
    if not log_file_txt.exists():
        await ctx.send(f"No log file found for `{date or 'today'}`.")
        return
    await ctx.send(file=discord.File(log_file_txt, filename=f"{log_file_txt.stem}.txt"))

@logs.command(name="search")
async def logs_search(ctx, *, term: str):
    await ctx.trigger_typing()
    results = []
    for log_file in sorted(BASE_LOG_DIR.glob("logs_*.json")):
        data = load_log(log_file)
        for entry in data:
            if fuzzy_contains(entry.get("content", ""), term):
                results.append(entry)
        if len(results) > 200:
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
            snippet = (r['content'][:180] + "...") if len(r['content']) > 180 else r['content']
            embed.add_field(name=f"{r['author']} — #{r['channel']} ({r['type']})", value=f"[{ts}] {snippet}", inline=False)
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

bot.run(TOKEN)