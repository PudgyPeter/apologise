# file: bot.py
import discord
from discord.ext import commands, tasks
import json
import os
import pathlib
from datetime import datetime, timedelta
import re
import asyncio
from discord.ui import Button, View, Modal, TextInput
import requests

# --- CONFIGURATION ---
TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 1430766113721028658
ALERT_CHANNEL_ID = 1431130781975187537
IGNORED_CHANNEL_ID = 1462042281258389576
KEYWORDS = ["jordan", "pudge", "pudgy", "jorganism"]
FUZZY_TOLERANCE = 2
GROUP_WINDOW = 10  # seconds to group messages
GROUP_PRUNE = 60   # seconds after which an inactive group is pruned
MAX_SEARCH_RESULTS = 200
LOCAL_TIMEZONE_OFFSET = 11  # UTC+11 for Australian Eastern Daylight Time

# --- PATHS ---
RAILWAY_DIR = pathlib.Path("/mnt/data")
RAILWAY_APP_DIR = pathlib.Path("/app/data")
LOCAL_DIR = pathlib.Path(__file__).parent.parent / "data"  # Project root / data

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
    # Use local timezone for daily log files
    local_time = datetime.utcnow() + timedelta(hours=LOCAL_TIMEZONE_OFFSET)
    today_str = local_time.strftime("logs_%Y-%m-%d.json")
    return BASE_LOG_DIR / today_str

def load_log(log_path: pathlib.Path):
    if not log_path.exists():
        log_path.write_text("[]", encoding="utf-8")
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        log_path.write_text("[]", encoding="utf-8")
        return []

def _send_live_message_sync(entry_copy: dict):
    """Synchronous helper — runs inside an executor thread."""
    try:
        api_url = os.getenv("WEB_API_URL", "https://apologise-production.up.railway.app")
        endpoint = f"{api_url}/api/live"
        response = requests.post(endpoint, json=entry_copy, timeout=5)
        if response.status_code != 200:
            print(f"[� LIVE] API returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[💥] Live messages error: {e}")

def append_to_live_messages(entry: dict):
    """Send message to web API for live feed (non-blocking)."""
    try:
        entry_copy = entry.copy()
        if 'created_at' in entry_copy and hasattr(entry_copy['created_at'], 'isoformat'):
            entry_copy['created_at'] = entry_copy['created_at'].isoformat()
        # Run the blocking HTTP call in a background thread so the event loop is not stalled
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _send_live_message_sync, entry_copy)
    except Exception as e:
        print(f"[💥] Live messages dispatch error: {e}")

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
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot_start_time = datetime.utcnow()

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
    """Check if keyword appears in text with fuzzy matching, respecting word boundaries"""
    text = (text or "").lower()
    keyword = (keyword or "").lower()
    if len(keyword) == 0 or len(text) < len(keyword):
        return False
    
    # Split text into words (alphanumeric sequences)
    words = re.findall(r'\b\w+\b', text)
    
    # Check each word for exact or fuzzy match
    for word in words:
        # Exact match
        if keyword == word:
            return True
        # Fuzzy match only if word length is close to keyword length
        # AND the first character matches (prevents "dude" matching "pudge")
        if abs(len(word) - len(keyword)) <= tolerance:
            if word[0] == keyword[0] and levenshtein(word, keyword) <= tolerance:
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
        "channel_id": message.channel.id,
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
        if not result:
            channel_last_author[message.channel.id] = (message.author.id, message.id, now)
            return
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
        data = group_cache.pop(k, None)
        if data:
            # Clean up message_to_group references pointing to this group
            stale_ids = [mid for mid, (gk, _) in message_to_group.items() if gk == k]
            for mid in stale_ids:
                message_to_group.pop(mid, None)

@prune_groups.before_loop
async def before_prune():
    await bot.wait_until_ready()

# --- EVENTS: message / edit / delete / reactions ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    
    if message.channel.id == IGNORED_CHANNEL_ID:
        await bot.process_commands(message)
        return

    # Get role color
    role_color = None
    if message.guild and isinstance(message.author, discord.Member):
        if message.author.top_role and message.author.top_role.color.value != 0:
            role_color = f"#{message.author.top_role.color.value:06x}"
    
    entry = {
        "id": message.id,
        "author": str(message.author),
        "author_display": message.author.display_name,
        "author_id": message.author.id,
        "avatar_url": message.author.display_avatar.url,
        "role_color": role_color,
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
            description=f"**[{message.author}]** mentioned a watched term in <#{message.channel.id}>:\n\n> {message.content}"[:4000],
            color=discord.Color.red(),
            timestamp=message.created_at
        )
        alert.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
        alert.set_footer(text=f"Detected at {datetime.utcnow().strftime('%H:%M:%S UTC')}")
        alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            # Try to get the log message URL instead of original message
            log_url = message.jump_url  # fallback to original
            group_info = message_to_group.get(message.id)
            if group_info:
                group_key, _ = group_info
                group_data = group_cache.get(group_key)
                if group_data and group_data.get("log_message_id") and group_data.get("log_channel_id"):
                    # Build jump URL to log channel message
                    log_url = f"https://discord.com/channels/{message.guild.id}/{group_data['log_channel_id']}/{group_data['log_message_id']}"
            
            jump_button = Button(label="Jump to Log", style=discord.ButtonStyle.link, url=log_url)
            view = View(); view.add_item(jump_button)
            await alert_channel.send(embed=alert, view=view)

    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.channel.id == IGNORED_CHANNEL_ID:
        return
    
    # Ignore phantom edits (embed previews loading, no actual content change)
    if before.content == after.content:
        return
    
    # Populate editsnipe cache
    last_edited[before.channel.id] = {
        "author": str(before.author),
        "before": before.content,
        "after": after.content,
        "avatar_url": before.author.display_avatar.url,
        "timestamp": datetime.utcnow(),
    }
    
    # Get role color
    role_color = None
    if before.guild and isinstance(before.author, discord.Member):
        if before.author.top_role and before.author.top_role.color.value != 0:
            role_color = f"#{before.author.top_role.color.value:06x}"
    
    entry = {
        "id": before.id,
        "author": str(before.author),
        "author_display": before.author.display_name,
        "author_id": before.author.id,
        "avatar_url": before.author.display_avatar.url,
        "role_color": role_color,
        "content": after.content,
        "channel": before.channel.name,
        "channel_id": before.channel.id,
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
            before_text = (before.content or "(no text)")[:1024]
            after_text = (after.content or "(no text)")[:1024]
            embed.add_field(name="Before", value=before_text, inline=False)
            embed.add_field(name="After", value=after_text, inline=False)
            
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
            
            embed.set_thumbnail(url=before.author.avatar.url if before.author.avatar else None)
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
    
    if message.channel.id == IGNORED_CHANNEL_ID:
        return
    
    # Get role color
    role_color = None
    if message.guild and isinstance(message.author, discord.Member):
        if message.author.top_role and message.author.top_role.color.value != 0:
            role_color = f"#{message.author.top_role.color.value:06x}"
    
    # Populate snipe cache
    last_deleted[message.channel.id] = {
        "author": str(message.author),
        "content": message.content,
        "avatar_url": message.author.display_avatar.url,
        "timestamp": datetime.utcnow(),
        "attachments": [att.url for att in message.attachments] if message.attachments else [],
    }

    entry = {
        "id": message.id,
        "author": str(message.author),
        "author_display": message.author.display_name,
        "author_id": message.author.id,
        "avatar_url": message.author.display_avatar.url,
        "role_color": role_color,
        "content": message.content,
        "channel": message.channel.name,
        "channel_id": message.channel.id,
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
                all_attachment_urls.append(att.url)
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
        
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
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
        users = [u async for u in reaction.users()]
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
        # Get role color
        role_color = None
        if message.guild and isinstance(message.author, discord.Member):
            if message.author.top_role and message.author.top_role.color.value != 0:
                role_color = f"#{message.author.top_role.color.value:06x}"
        
        entry = {
            "id": message.id,
            "author": str(message.author),
            "author_display": message.author.display_name,
            "author_id": message.author.id,
            "avatar_url": message.author.display_avatar.url,
            "role_color": role_color,
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
            embed.add_field(name="Message", value=(message.content[:200] if message.content else "(no text)"), inline=False)
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
    if not prune_groups.is_running():
        prune_groups.start()
    guild_list = ', '.join(f"{g.name} ({g.member_count} members)" for g in bot.guilds)
    print(f"[✅] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[✅] Connected to {len(bot.guilds)} guild(s): {guild_list}")

# --- LOG COMMANDS (list/download/search) ---
@bot.command(name="ping")
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    uptime = datetime.utcnow() - bot_start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(f"🏓 Pong! **{latency_ms}ms** latency • Uptime: **{hours}h {minutes}m {seconds}s**")

@bot.command(name="help")
async def custom_help(ctx):
    embed = discord.Embed(
        title="📖 Bot Commands",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="📡 General",
        value="`!ping` — Latency & uptime\n`!help` — This message\n`!inviteme` — Invite links for all servers",
        inline=False
    )
    embed.add_field(
        name="📄 Logs",
        value=(
            "`!logs list [page]` — Browse available logs\n"
            "`!logs download <YYYY-MM-DD|today|name>` — Download a log file\n"
            "`!logs search <term>` — Search across all logs\n"
            "`!logs prune <name>` — Delete a custom log\n"
            "`!logs delete <name>` — Alias for prune"
        ),
        inline=False
    )
    embed.add_field(
        name="🛠️ Admin *(Manage Messages)*",
        value="`!create log <amount> <name> [channel_id]` — Export messages to a custom log",
        inline=False
    )
    embed.set_footer(text="Prefix: !")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`. Use `!help` for usage info.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Bad argument: {error}. Use `!help` for usage info.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Silently ignore unknown commands
    else:
        print(f"[💥] Command error in {ctx.command}: {error}")

@bot.group(invoke_without_command=True)
async def logs(ctx):
    await ctx.send("Use `!logs list`, `!logs search <term>`, `!logs download <date|today>`, or `!logs prune <name>`")

class PageModal(Modal, title="Go to Page"):
    page_input = TextInput(label="Page Number", placeholder="Enter page number...", required=True, max_length=5)
    
    def __init__(self, ctx, files, total_pages):
        super().__init__()
        self.ctx = ctx
        self.files = files
        self.total_pages = total_pages
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_input.value)
            if page < 1 or page > self.total_pages:
                await interaction.response.send_message(f"❌ Invalid page number. Please use a page between 1 and {self.total_pages}.", ephemeral=True)
                return
            
            embed, view = create_logs_list_page(self.files, page, self.total_pages, self.ctx)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

class LogsListView(View):
    def __init__(self, ctx, files, current_page, total_pages):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.files = files
        self.current_page = current_page
        self.total_pages = total_pages
        
        # Previous button
        prev_button = Button(label="◀ Previous", style=discord.ButtonStyle.primary, disabled=(current_page == 1))
        prev_button.callback = self.previous_page
        self.add_item(prev_button)
        
        # Go to page button
        goto_button = Button(label="Go to Page...", style=discord.ButtonStyle.secondary)
        goto_button.callback = self.goto_page
        self.add_item(goto_button)
        
        # Next button
        next_button = Button(label="Next ▶", style=discord.ButtonStyle.primary, disabled=(current_page == total_pages))
        next_button.callback = self.next_page
        self.add_item(next_button)
    
    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page > 1:
            embed, view = create_logs_list_page(self.files, self.current_page - 1, self.total_pages, self.ctx)
            await interaction.response.edit_message(embed=embed, view=view)
    
    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages:
            embed, view = create_logs_list_page(self.files, self.current_page + 1, self.total_pages, self.ctx)
            await interaction.response.edit_message(embed=embed, view=view)
    
    async def goto_page(self, interaction: discord.Interaction):
        modal = PageModal(self.ctx, self.files, self.total_pages)
        await interaction.response.send_modal(modal)

def create_logs_list_page(files, page, total_pages, ctx):
    per_page = 20
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(files))
    page_files = files[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"Available Logs (Page {page}/{total_pages})",
        description=f"Showing {len(page_files)} of {len(files)} total logs",
        color=discord.Color.blurple()
    )
    
    for f in page_files:
        date_str = f.stem.replace("logs_", "").replace("custom_", "")
        size_kb = f.stat().st_size // 1024
        embed.add_field(name=f"🗓️ {date_str}", value=f"{size_kb} KB - Use `!logs download {date_str}`", inline=False)
    
    view = LogsListView(ctx, files, page, total_pages)
    return embed, view

@logs.command(name="list")
async def logs_list(ctx, page: int = 1):
    try:
        files = sorted(BASE_LOG_DIR.glob("logs_*.txt"), reverse=True)
        custom = sorted(BASE_LOG_DIR.glob("custom_*.txt"), reverse=True)
        files = files + custom
        if not files:
            await ctx.send("No logs found yet.")
            return
        
        per_page = 20
        total_pages = (len(files) + per_page - 1) // per_page
        
        if page < 1 or page > total_pages:
            await ctx.send(f"❌ Invalid page number. Please use a page between 1 and {total_pages}.")
            return
        
        embed, view = create_logs_list_page(files, page, total_pages, ctx)
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        print(f"[💥] logs list error: {e}")

@logs.command(name="download")
async def logs_download(ctx, date: str = None):
    if date is None or date.lower() == "today":
        log_file_txt = get_daily_log_path().with_suffix(".txt")
    else:
        # Try as a date first
        try:
            datetime.strptime(date, "%Y-%m-%d")
            log_file_txt = BASE_LOG_DIR / f"logs_{date}.txt"
        except ValueError:
            # Fall back to custom log name
            log_file_txt = BASE_LOG_DIR / f"custom_{date}.txt"
    if not log_file_txt.exists():
        await ctx.send(f"No log file found for `{date or 'today'}`. Use `!logs list` to see available logs.")
        return
    await ctx.send(file=discord.File(log_file_txt, filename=f"{log_file_txt.stem}.txt"))

class SearchResultsView(View):
    def __init__(self, results, term, current_page, total_pages):
        super().__init__(timeout=300)
        self.results = results
        self.term = term
        self.current_page = current_page
        self.total_pages = total_pages

        prev_btn = Button(label="◀ Previous", style=discord.ButtonStyle.primary, disabled=(current_page <= 1))
        prev_btn.callback = self.previous_page
        self.add_item(prev_btn)

        next_btn = Button(label="Next ▶", style=discord.ButtonStyle.primary, disabled=(current_page >= total_pages))
        next_btn.callback = self.next_page
        self.add_item(next_btn)

    def _make_embed(self, page):
        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        embed = discord.Embed(
            title=f"🔍 Results for '{self.term}' (Page {page}/{self.total_pages})",
            description=f"{len(self.results)} results found",
            color=discord.Color.green()
        )
        for r in self.results[start:end]:
            try:
                ts = datetime.fromisoformat(r["created_at"]).strftime("%H:%M:%S")
            except Exception:
                ts = "??:??:??"
            snippet = (r['content'][:180] + "...") if len(r.get('content', '')) > 180 else (r.get('content', '') or '(no text)')
            field_name = f"{r.get('author', '?')} — #{r.get('channel', '?')} ({r.get('type', '')})"[:256]
            embed.add_field(name=field_name, value=f"[{ts}] {snippet}"[:1024], inline=False)
        return embed

    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page > 1:
            self.current_page -= 1
            view = SearchResultsView(self.results, self.term, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=view._make_embed(self.current_page), view=view)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages:
            self.current_page += 1
            view = SearchResultsView(self.results, self.term, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=view._make_embed(self.current_page), view=view)

@logs.command(name="search")
async def logs_search(ctx, *, term: str = None):
    try:
        if not term:
            await ctx.send("❌ Please provide a search term: `!logs search <term>`")
            return
        async with ctx.typing():
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
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        print(f"[💥] logs search error: {e}")
        return
    per_page = 10
    total_pages = max(1, (len(results) + per_page - 1) // per_page)
    view = SearchResultsView(results, term, 1, total_pages)
    await ctx.send(embed=view._make_embed(1), view=view)

# --- CUSTOM LOG CREATION AND PRUNING ---
@bot.command(name="create")
@commands.has_permissions(manage_messages=True)
async def create_custom_log(ctx, subcommand=None, amount: int = None, name: str = None, channel_id: int = None):
    if subcommand != "log" or not amount or not name:
        await ctx.send("Usage: `!create log <amount> <name> [channel_id]`")
        return
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        await ctx.send("❌ Log name must only contain letters, numbers, hyphens, and underscores.")
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
    
    progress_msg = await ctx.send(f"Creating custom log `{name}` with last {amount} messages from #{target_channel.name}... ⏳")
    messages = []
    fetched = 0
    async for msg in target_channel.history(limit=amount):
        fetched += 1
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
        # Update progress every 500 messages
        if fetched % 500 == 0:
            try:
                await progress_msg.edit(content=f"Fetched {fetched}/{amount} messages... ⏳")
            except Exception:
                pass
    
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
async def logs_delete(ctx, *, name: str):
    removed = False
    for ext in [".json", ".txt"]:
        p = BASE_LOG_DIR / f"custom_{name}{ext}"
        if p.exists():
            p.unlink()
            removed = True
    await ctx.send(f"{'🗑️ Deleted' if removed else '❌ No such log found'} `{name}`")

# --- INVITE COMMAND ---
@bot.command(name="inviteme")
async def inviteme(ctx):
    """Create and post an invite link for every server the bot is in."""
    await ctx.send("Generating invite links for all servers... \u23f3")
    embeds = []
    for guild in bot.guilds:
        invite_url = None
        # Try to create an invite from the first text channel we have permission for
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if perms.create_instant_invite:
                try:
                    invite = await channel.create_invite(
                        max_age=0,      # never expires
                        max_uses=0,     # unlimited uses
                        unique=False    # reuse existing invite if possible
                    )
                    invite_url = str(invite)
                    break
                except Exception:
                    continue
        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.green() if invite_url else discord.Color.red()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(
            name="Members",
            value=str(guild.member_count),
            inline=True
        )
        if invite_url:
            embed.add_field(name="Invite", value=invite_url, inline=False)
        else:
            embed.add_field(name="Invite", value="\u274c No permission to create invite", inline=False)
        embeds.append(embed)

    if not embeds:
        await ctx.send("I'm not in any servers!")
        return

    # Discord allows up to 10 embeds per message
    for i in range(0, len(embeds), 10):
        await ctx.send(embeds=embeds[i:i+10])

# --- SNIPE CACHES ---
last_deleted = {}   # channel_id -> {"author": ..., "content": ..., "avatar_url": ..., "timestamp": ..., "attachments": []}
last_edited = {}    # channel_id -> {"author": ..., "before": ..., "after": ..., "avatar_url": ..., "timestamp": ...}

# --- SNIPE COMMAND ---
@bot.command(name="snipe")
async def snipe(ctx):
    """Show the last deleted message in this channel."""
    data = last_deleted.get(ctx.channel.id)
    if not data:
        await ctx.send("Nothing to snipe here.")
        return
    embed = discord.Embed(
        description=data["content"] or "(no text)",
        color=discord.Color.red(),
        timestamp=data["timestamp"]
    )
    embed.set_author(name=data["author"], icon_url=data.get("avatar_url"))
    embed.set_footer(text=f"Deleted in #{ctx.channel.name}")
    if data.get("attachments"):
        embed.add_field(name="📎 Attachments", value="\n".join(data["attachments"]), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="editsnipe")
async def editsnipe(ctx):
    """Show the last edited message's original content in this channel."""
    data = last_edited.get(ctx.channel.id)
    if not data:
        await ctx.send("No recent edits to snipe here.")
        return
    embed = discord.Embed(color=discord.Color.gold(), timestamp=data["timestamp"])
    embed.set_author(name=data["author"], icon_url=data.get("avatar_url"))
    embed.add_field(name="Before", value=(data["before"] or "(no text)")[:1024], inline=False)
    embed.add_field(name="After", value=(data["after"] or "(no text)")[:1024], inline=False)
    embed.set_footer(text=f"Edited in #{ctx.channel.name}")
    await ctx.send(embed=embed)

# --- WHOIS COMMAND ---
@bot.command(name="whois")
async def whois(ctx, member: discord.Member = None):
    """Show info about a user."""
    member = member or ctx.author
    roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
    embed = discord.Embed(color=member.top_role.color if member.top_role.color.value != 0 else discord.Color.blurple())
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="ID", value=str(member.id), inline=True)
    embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
    embed.add_field(name="Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%b %d, %Y") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Top Role", value=member.top_role.mention if member.top_role != ctx.guild.default_role else "None", inline=True)
    if roles:
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:20]) if len(roles) <= 20 else " ".join(roles[:20]) + f" +{len(roles)-20} more", inline=False)
    embed.set_footer(text=f"Requested by {ctx.author}")
    await ctx.send(embed=embed)

# --- AVATAR COMMAND ---
@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """Show a user's avatar in full resolution."""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=member.top_role.color if member.top_role.color.value != 0 else discord.Color.blurple())
    embed.set_image(url=member.display_avatar.with_size(1024).url)
    embed.set_footer(text=f"Requested by {ctx.author}")
    await ctx.send(embed=embed)

# --- SERVERINFO COMMAND ---
@bot.command(name="serverinfo")
async def serverinfo(ctx):
    """Show detailed server information."""
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=discord.Color.blurple(), timestamp=datetime.utcnow())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=str(guild.owner), inline=True)
    embed.add_field(name="Members", value=str(guild.member_count), inline=True)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="Text Channels", value=str(len(guild.text_channels)), inline=True)
    embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)), inline=True)
    embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
    embed.add_field(name="Boosts", value=str(guild.premium_subscription_count or 0), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Verification", value=str(guild.verification_level).title(), inline=True)
    embed.set_footer(text=f"ID: {guild.id}")
    await ctx.send(embed=embed)

# --- TOP / LEADERBOARD COMMAND ---
@bot.command(name="top")
async def top_users(ctx, period: str = "today"):
    """Show most active users. Usage: !top [today|week|all]"""
    from collections import Counter
    counter = Counter()
    if period == "all":
        log_files = sorted(BASE_LOG_DIR.glob("logs_*.json"))
    elif period == "week":
        log_files = sorted(BASE_LOG_DIR.glob("logs_*.json"))[-7:]
    else:
        log_files = [get_daily_log_path()]
    for lf in log_files:
        if lf.exists():
            data = load_log(lf)
            for entry in data:
                if entry.get("type") == "create":
                    counter[entry.get("author_display") or entry.get("author", "Unknown")] += 1
    if not counter:
        await ctx.send(f"No messages found for period: `{period}`")
        return
    top10 = counter.most_common(10)
    embed = discord.Embed(title=f"🏆 Most Active Users ({period.title()})", color=discord.Color.gold())
    desc = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, count) in enumerate(top10):
        prefix = medals[i] if i < 3 else f"**{i+1}.**"
        desc.append(f"{prefix} **{name}** — {count} messages")
    embed.description = "\n".join(desc)
    embed.set_footer(text=f"Requested by {ctx.author}")
    await ctx.send(embed=embed)

# --- STATS COMMAND ---
@bot.command(name="stats")
async def stats_cmd(ctx, target: str = None, *, name: str = None):
    """Show stats. Usage: !stats [@user] or !stats channel [#channel]"""
    from collections import Counter, defaultdict
    if target == "channel":
        channel = ctx.channel
        if name:
            for ch in ctx.guild.text_channels:
                if ch.name == name.strip("#").lower() or str(ch.id) == name.strip("<>#"):
                    channel = ch
                    break
        counter = Counter()
        hourly = Counter()
        total = 0
        for lf in sorted(BASE_LOG_DIR.glob("logs_*.json")):
            data = load_log(lf)
            for entry in data:
                if entry.get("channel") == channel.name and entry.get("type") == "create":
                    total += 1
                    author = entry.get("author_display") or entry.get("author", "Unknown")
                    counter[author] += 1
                    try:
                        ts = datetime.fromisoformat(entry["created_at"])
                        hourly[ts.hour] += 1
                    except:
                        pass
        embed = discord.Embed(title=f"📊 #{channel.name} Stats", color=discord.Color.blurple())
        embed.add_field(name="Total Messages", value=str(total), inline=True)
        if counter:
            top5 = counter.most_common(5)
            embed.add_field(name="Top Users", value="\n".join(f"**{n}** — {c}" for n, c in top5), inline=False)
        if hourly:
            peak = hourly.most_common(1)[0]
            embed.add_field(name="Peak Hour (UTC)", value=f"{peak[0]:02d}:00 ({peak[1]} msgs)", inline=True)
        await ctx.send(embed=embed)
        return

    # User stats
    member = ctx.author
    if target:
        for m in ctx.guild.members:
            if target.lower() in str(m).lower() or target.lower() in m.display_name.lower() or target.strip("<@!>") == str(m.id):
                member = m
                break
    counter = Counter()
    total = 0
    word_count = 0
    channel_counter = Counter()
    hourly = Counter()
    for lf in sorted(BASE_LOG_DIR.glob("logs_*.json")):
        data = load_log(lf)
        for entry in data:
            if str(entry.get("author_id")) == str(member.id) and entry.get("type") == "create":
                total += 1
                content = entry.get("content", "")
                word_count += len(content.split())
                channel_counter[entry.get("channel", "unknown")] += 1
                try:
                    ts = datetime.fromisoformat(entry["created_at"])
                    hourly[ts.hour] += 1
                except:
                    pass
    embed = discord.Embed(title=f"📊 {member.display_name}'s Stats", color=member.top_role.color if member.top_role.color.value != 0 else discord.Color.blurple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Total Messages", value=str(total), inline=True)
    embed.add_field(name="Total Words", value=str(word_count), inline=True)
    embed.add_field(name="Avg Words/Msg", value=str(round(word_count / total, 1) if total else 0), inline=True)
    if channel_counter:
        top3 = channel_counter.most_common(3)
        embed.add_field(name="Top Channels", value="\n".join(f"#{n} — {c}" for n, c in top3), inline=False)
    if hourly:
        peak = hourly.most_common(1)[0]
        embed.add_field(name="Peak Hour (UTC)", value=f"{peak[0]:02d}:00 ({peak[1]} msgs)", inline=True)
    await ctx.send(embed=embed)

# --- START BOT ---
bot.run(TOKEN)
