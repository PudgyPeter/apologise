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
MAX_SEARCH_RESULTS = 200

# --- PATHS ---
RAILWAY_DIR = pathlib.Path("/mnt/data")
RAILWAY_APP_DIR = pathlib.Path("/app/data")
LOCAL_DIR = pathlib.Path(os.getcwd()) / "data"

# Check Railway paths first (both common mount points)
if RAILWAY_DIR.exists() and os.access(RAILWAY_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_DIR
elif RAILWAY_APP_DIR.exists() and os.access(RAILWAY_APP_DIR, os.W_OK):
    BASE_LOG_DIR = RAILWAY_APP_DIR
else:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    BASE_LOG_DIR = LOCAL_DIR
BASE_LOG_DIR.mkdir(parents=True, exist_ok=True)

LIVE_MESSAGES_FILE = BASE_LOG_DIR / "live_messages.json"
MAX_LIVE_MESSAGES = 500  # Keep last 500 messages

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
        log_path.write_text("[]", encoding="utf-8")
        return []

def append_to_live_messages(entry: dict):
    """Append message to live feed (keeps last MAX_LIVE_MESSAGES)"""
    try:
        print(f"[🔴 LIVE] Appending to live messages file: {LIVE_MESSAGES_FILE}")
        print(f"[🔴 LIVE] File exists: {LIVE_MESSAGES_FILE.exists()}")
        messages = load_log(LIVE_MESSAGES_FILE)
        print(f"[🔴 LIVE] Current message count: {len(messages)}")
        messages.append(entry)
        # Keep only last MAX_LIVE_MESSAGES
        messages = messages[-MAX_LIVE_MESSAGES:]
        print(f"[🔴 LIVE] Writing {len(messages)} messages to file")
        with open(LIVE_MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        print(f"[🔴 LIVE] Successfully wrote to live messages file")
    except Exception as e:
        print(f"[💥] Live messages error: {e}")
        import traceback
        traceback.print_exc()

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
    append_to_live_messages(entry)  # Also add to live feed

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

# --- FUZZY HELPERS ---
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
    text = (text or "").lower()
    keyword = (keyword or "").lower()
    if keyword in text:
        return True
    if len(keyword) == 0 or len(text) < len(keyword):
        return False
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
group_cache = {}  # (author_id, channel_id) -> data
message_to_group = {}  # message_id -> (group_key, index)
channel_last_author = {}  # channel_id -> (author_id, message_id, timestamp) to prevent grouping across other authors

# --- BUILD ENTRY FROM MESSAGE ---
async def build_entry_from_message(message: discord.Message):
    attachments = [a.url for a in message.attachments]
    reply_preview = None
    if message.reference and getattr(message.reference, "message_id", None):
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
        "author_id": message.author.id,
        "avatar_url": message.author.display_avatar.url,
        "content": message.content or "",
        "created_at": message.created_at,
        "created_at_iso": message.created_at.isoformat(),
        "readable_time": message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "channel": message.channel.name,
        "attachments": attachments,
        "reactions": {},  # emoji -> {"count": int, "users": [names]}
        "reply_preview": reply_preview
    }

# --- BUILD GROUP EMBED ---
def build_group_embed(group_key):
    data = group_cache.get(group_key)
    if not data or not data.get("messages"):
        return None
    first = data["messages"][0]
    author_display = first.get("author_display", "Unknown")
    
    # Get the author's highest role color
    color = discord.Color.blurple()  # default fallback
    if data.get("guild") and data.get("author_id"):
        try:
            member = data["guild"].get_member(data["author_id"])
            if member and member.top_role and member.top_role.color.value != 0:
                color = member.top_role.color
        except Exception:
            pass  # fallback to blurple if we can't get the role color
    
    embed = discord.Embed(color=color, timestamp=data["messages"][-1]["created_at"])
    embed.set_author(name=f"{author_display}")
    if data.get("thumbnail"):
        embed.set_thumbnail(url=data["thumbnail"])
    description_parts = []
    for m in data["messages"]:
        ts = m["created_at"].strftime("%H:%M:%S") if hasattr(m["created_at"], "strftime") else str(m["created_at"])
        line = f"**[{ts}]** {m['content'] or '(no text)'}"
        if m.get("reply_preview"):
            rp = m["reply_preview"]
            line = f"↩️ replying to **{rp['author']}**: `{rp['content']}`\n{line}"
        if m.get("attachments"):
            for i, aurl in enumerate(m["attachments"]):
                # Check if it's an image/gif/video that should be embedded
                is_media = re.search(r"\.(gif|png|jpe?g|webp|mp4|mov|webm)$", aurl, re.IGNORECASE)
                if i == 0 and is_media:
                    # first media attachment will be shown as embed image
                    pass
                else:
                    # Show link for non-media or additional attachments
                    filename = aurl.split("/")[-1].split("?")[0]
                    line += f"\n📎 [{filename}]({aurl})"
        if m.get("reactions"):
            parts = []
            for emoji, info in m["reactions"].items():
                users = info.get("users", [])
                snippet = ", ".join(users[:5]) if users else ""
                parts.append(f"{emoji} x{info.get('count',0)} ({snippet})")
            if parts:
                line += f"\n🔁 Reactions: {' • '.join(parts)}"
        description_parts.append(line)
    embed.description = "\n\n".join(description_parts)[:4000]
    embed.set_footer(text=f"#{data.get('channel_name','unknown')} • {len(data.get('messages',[]))} messages")
    return embed, data.get("image_url")

# --- ADD MESSAGE TO GROUP ---
async def add_message_to_group(message: discord.Message):
    group_key = (message.author.id, message.channel.id)
    now = datetime.utcnow()
    entry = await build_entry_from_message(message)
    thumbnail = message.author.avatar.url if message.author.avatar else None

    # check channel last author to prevent grouping across other users
    chan_info = channel_last_author.get(message.channel.id)
    if chan_info:
        last_author_id, last_msg_id, last_ts = chan_info
    else:
        last_author_id, last_msg_id, last_ts = (None, None, None)

    existing = group_cache.get(group_key)
    can_group = False
    if existing and (now - existing["last_time"]).total_seconds() <= GROUP_WINDOW:
        # also require that the last message in the channel was from the same author and it wasn't interrupted
        if last_author_id == message.author.id and last_msg_id == existing["messages"][-1]["message_id"]:
            can_group = True

    if can_group:
        existing["messages"].append(entry)
        existing["last_time"] = now
        idx = len(existing["messages"]) - 1
        message_to_group[message.id] = (group_key, idx)
        if not existing.get("image_url"):
            if entry["attachments"]:
                for aurl in entry["attachments"]:
                    if re.search(r"\.(gif|png|jpe?g|webp|mp4|mov|webm)$", aurl, re.IGNORECASE):
                        existing["image_url"] = aurl
                        break
            else:
                link_img = find_image_url(entry["content"])
                if link_img:
                    existing["image_url"] = link_img
        try:
            log_chan = bot.get_channel(existing["log_channel_id"])
            if log_chan:
                log_msg = await log_chan.fetch_message(existing["log_message_id"])
                existing["thumbnail"] = thumbnail
                result = build_group_embed(group_key)
                if result:
                    new_embed, image_url = result
                    await log_msg.edit(embed=new_embed)
                # Send all attachment URLs from the new message as plain text for Discord auto-embedding
                if entry["attachments"]:
                    for aurl in entry["attachments"]:
                        await log_chan.send(aurl)
        except Exception as e:
            print(f"[💥] update group embed error: {e}")
    else:
        # start new group
        group_cache[group_key] = {
            "last_time": now,
            "messages": [entry],
            "log_channel_id": message.channel.id,  # replaced with actual log channel below
            "log_message_id": None,
            "thumbnail": thumbnail,
            "image_url": None,
            "channel_name": message.channel.name,
            "guild": message.guild,
            "author_id": message.author.id,
        }
        if entry["attachments"]:
            for aurl in entry["attachments"]:
                if re.search(r"\.(gif|png|jpe?g|webp|mp4|mov|webm)$", aurl, re.IGNORECASE):
                    group_cache[group_key]["image_url"] = aurl
                    break
        else:
            link_img = find_image_url(entry["content"])
            if link_img:
                group_cache[group_key]["image_url"] = link_img
        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if not log_chan:
            # still update channel_last_author info so next message grouping logic works
            channel_last_author[message.channel.id] = (message.author.id, message.id, now)
            return
        group_cache[group_key]["log_channel_id"] = LOG_CHANNEL_ID
        result = build_group_embed(group_key)
        try:
            embed, image_url = result
            sent = await log_chan.send(embed=embed)
            # Send all attachment URLs as plain text for Discord auto-embedding
            if entry["attachments"]:
                for aurl in entry["attachments"]:
                    await log_chan.send(aurl)
            group_cache[group_key]["log_message_id"] = sent.id
            message_to_group[message.id] = (group_key, 0)
        except Exception as e:
            print(f"[💥] send group embed error: {e}")

    # update last author tracker for the channel
    channel_last_author[message.channel.id] = (message.author.id, message.id, now)

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
            view = View(); view.add_item(jump_button)
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
    mg = message_to_group.get(before.id)
    if mg:
        group_key, idx = mg
        data = group_cache.get(group_key)
        if data and idx < len(data["messages"]):
            data["messages"][idx]["content"] = after.content or ""
            data["messages"][idx]["created_at"] = after.edited_at or datetime.utcnow()
            try:
                log_chan = bot.get_channel(data["log_channel_id"])
                log_msg = await log_chan.fetch_message(data["log_message_id"])
                result = build_group_embed(group_key)
                if result:
                    new_embed, image_url = result
                    await log_msg.edit(embed=new_embed)
            except Exception as e:
                print(f"[💥] update on edit error: {e}")
    else:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.gold(), timestamp=datetime.utcnow())
            embed.add_field(name="Before", value=before.content or "(no text)", inline=False)
            embed.add_field(name="After", value=after.content or "(no text)", inline=False)
            
            attachment_urls = []
            if after.attachments:
                attachment_urls = [a.url for a in after.attachments]
                embed.add_field(name="📎 Attachments", value="\n".join(f"[{a.filename}]({a.url})" for a in after.attachments), inline=False)
            
            # Collect embed URLs from the message
            embed_urls = []
            if after.embeds:
                for e in after.embeds:
                    try:
                        if getattr(e, "url", None):
                            embed_urls.append(e.url)
                    except Exception:
                        continue
            
            embed.set_thumbnail(url=before.author.avatar.url if before.author.avatar else discord.Embed.Empty)
            embed.set_footer(text=datetime.utcnow().strftime("%b %d • %H:%M:%S UTC"))
            await log_channel.send(embed=embed)
            
            # Send attachment URLs as plain text for Discord auto-embedding
            for url in attachment_urls:
                await log_channel.send(url)
            
            # Send embed URLs as plain text for Discord auto-embedding
            for url in embed_urls:
                await log_channel.send(url)

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
    
    # Always create a NEW embed for deleted messages (don't edit the original)
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention}\n**Channel:** <#{message.channel.id}>",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        # Add message content
        if message.content:
            content_preview = message.content[:1024] if len(message.content) > 1024 else message.content
            embed.add_field(name="💬 Content", value=content_preview, inline=False)
        else:
            embed.add_field(name="💬 Content", value="(no text)", inline=False)
        
        # Handle attachments - collect URLs to send separately
        all_attachment_urls = []
        attachment_links = []
        if message.attachments:
            for att in message.attachments:
                # Check if it's media that can be embedded
                is_image = any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"])
                is_video = any(att.filename.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm"])
                
                # Collect all attachment URLs for sending
                all_attachment_urls.append(att.url)
                
                # Also add as links in embed
                attachment_links.append(f"[{att.filename}]({att.url})")
            
            # Add links for attachments in the embed
            if attachment_links:
                embed.add_field(name="📎 Attachments", value="\n".join(attachment_links), inline=False)
        
        # Handle embeds from the original message (like linked images)
        embed_urls = []
        if message.embeds:
            for e in message.embeds:
                try:
                    if getattr(e, "type", None) == "image" and getattr(e, "url", None):
                        embed_urls.append(e.url)
                    elif getattr(e, "url", None):
                        embed_urls.append(e.url)
                except Exception:
                    continue
        
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty)
        embed.set_footer(text=f"Original message from {message.created_at.strftime('%b %d • %H:%M:%S UTC')}")
        
        try:
            await log_channel.send(embed=embed)
            
            # Send attachment URLs as plain text so Discord auto-embeds them
            for url in all_attachment_urls:
                await log_channel.send(url)
            
            # Send embed URLs as plain text so Discord auto-embeds them
            for url in embed_urls:
                await log_channel.send(url)
        except Exception as e:
            print(f"[💥] send delete embed error: {e}")

# --- REACTIONS ---
async def update_reaction_on_embed(message: discord.Message, reaction: discord.Reaction):
    mg = message_to_group.get(message.id)
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
        entry = data["messages"][idx]
        entry["reactions"][emoji] = {"count": count, "users": user_names}
        try:
            log_chan = bot.get_channel(data["log_channel_id"])
            log_msg = await log_chan.fetch_message(data["log_message_id"])
            result = build_group_embed(group_key)
            if result:
                new_embed, image_url = result
                await log_msg.edit(embed=new_embed)
        except Exception as e:
            print(f"[💥] update reaction embed error: {e}")
    else:
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

# --- LOG COMMANDS (list/download/search) ---
@bot.group(invoke_without_command=True)
async def logs(ctx):
    await ctx.send("Use `!logs list`, `!logs search <term>`, `!logs download <date|today>`, or `!logs prune <name>`")

@logs.command(name="list")
async def logs_list(ctx):
    files = sorted(BASE_LOG_DIR.glob("logs_*.txt"))
    custom = sorted(BASE_LOG_DIR.glob("custom_*.txt"))
    files = files + custom
    if not files:
        await ctx.send("No logs found yet.")
        return
    embed = discord.Embed(title="Available Logs", color=discord.Color.blurple())
    view = View()
    for f in files:
        date_str = f.stem.replace("logs_", "").replace("custom_", "")
        size_kb = f.stat().st_size // 1024
        embed.add_field(name=f"🗓️ {date_str} ({size_kb} KB)", value=f"Click below to download.", inline=False)
        btn = Button(label=f"Download {date_str}", style=discord.ButtonStyle.primary)
        async def download_callback(interaction, file=f):
            await interaction.response.send_message(file=discord.File(file, filename=file.name), ephemeral=True)
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
    # search both daily and custom JSON logs
    for log_file in sorted(BASE_LOG_DIR.glob("*.json")):
        data = load_log(log_file)
        for entry in data:
            if fuzzy_contains(entry.get("content", ""), term):
                results.append(entry)
        if len(results) > MAX_SEARCH_RESULTS:
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
            snippet = (r['content'][:180] + "...") if len(r.get('content','')) > 180 else r.get('content','')
            embed.add_field(name=f"{r['author']} — #{r['channel']} ({r.get('type','')})", value=f"[{ts}] {snippet}", inline=False)
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

# --- CUSTOM LOG CREATION AND PRUNING ---
@bot.command(name="create")
@commands.has_permissions(manage_messages=True)
async def create_custom_log(ctx, subcommand=None, amount: int = None, name: str = None, channel_id: int = None):
    if subcommand != "log" or not amount or not name:
        await ctx.send("Usage: `!create log <amount> <name> [channel_id]`")
        return
    if amount > 5000:
        await ctx.send("❌ You can only export up to 5000 messages at once.")
        return
    
    # Determine which channel to use
    if channel_id:
        try:
            target_channel = bot.get_channel(channel_id)
            if not target_channel:
                await ctx.send(f"❌ Channel with ID `{channel_id}` not found.")
                return
        except Exception as e:
            await ctx.send(f"❌ Invalid channel ID: {e}")
            return
    else:
        target_channel = ctx.channel
    
    await ctx.send(f"Creating custom log `{name}` with last {amount} messages from #{target_channel.name}... ⏳")
    messages = []
    async for msg in target_channel.history(limit=amount):
        if msg.author.bot:
            continue
        messages.append({
            "id": msg.id,
            "author": str(msg.author),
            "content": msg.content or "",
            "created_at": msg.created_at.isoformat(),
            "readable_time": msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "channel": target_channel.name,
            "attachments": [a.url for a in msg.attachments],
        })
    
    # Reverse to get chronological order (oldest to newest)
    messages.reverse()
    
    json_path = BASE_LOG_DIR / f"custom_{name}.json"
    txt_path = BASE_LOG_DIR / f"custom_{name}.txt"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(messages, jf, indent=2, ensure_ascii=False)
    with open(txt_path, "w", encoding="utf-8") as tf:
        for m in messages:
            tf.write(f"[{m['readable_time']}] {m['author']}:\n{m['content'] or '(no text)'}\n")
            if m["attachments"]:
                tf.write("  📎 " + ", ".join(m["attachments"]) + "\n")
            tf.write("\n")
    btn = Button(label="Download Log", style=discord.ButtonStyle.success)
    async def cb(interaction):
        await interaction.response.send_message(file=discord.File(txt_path, filename=txt_path.name), ephemeral=True)
    btn.callback = cb
    view = View(); view.add_item(btn)
    e = discord.Embed(title="✅ Custom Log Created", description=f"Saved as `{txt_path.name}` from #{target_channel.name}", color=discord.Color.green())
    await ctx.send(embed=e, view=view)

@logs.command(name="prune")
@commands.has_permissions(manage_messages=True)
async def logs_prune(ctx, *, name: str):
    removed = False
    for ext in [".json", ".txt"]:
        p = BASE_LOG_DIR / f"custom_{name}{ext}"
        if p.exists():
            p.unlink()
            removed = True
    await ctx.send(f"{'🗑️ Deleted' if removed else '❌ No such log found'} `{name}`")

@logs.command(name="delete")
@commands.has_permissions(manage_messages=True)
async def logs_prune(ctx, *, name: str):
    removed = False
    for ext in [".json", ".txt"]:
        p = BASE_LOG_DIR / f"custom_{name}{ext}"
        if p.exists():
            p.unlink()
            removed = True
    await ctx.send(f"{'🗑️ Deleted' if removed else '❌ No such log found'} `{name}`")

# --- START BOT ---
bot.run(TOKEN)
