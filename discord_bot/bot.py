import discord
from discord.ext import commands
import os
import re
from difflib import SequenceMatcher

# --- Configuration ---
TOKEN = os.getenv("TOKEN")

LOG_CHANNEL_ID = 130000000000000000   # Replace with your log channel ID
ALERT_CHANNEL_ID = 130000000000000001 # Replace with your alert channel ID

# --- Alert name patterns ---
NAME_PATTERNS = [
    r"(?i)\bj+o+r+d+a+n+\b",
    r"(?i)\bp+u+d+g+e+\b",
    r"(?i)\bp+u+d+g+y+\b",
]

FUZZY_NAMES = ["jordan", "pudge", "pudgy"]

# --- Intents ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --- Helpers ---
def regex_match(text: str, patterns: list) -> str | None:
    for pattern in patterns:
        if re.search(pattern, text):
            return pattern
    return None


def fuzzy_match(text: str, keywords: list, threshold: float = 0.8) -> str | None:
    text = re.sub(r"[^a-z0-9]", "", text.lower())
    for word in text.split():
        for key in keywords:
            ratio = SequenceMatcher(None, word, key).ratio()
            if ratio >= threshold:
                return key
    return None


async def create_message_embed(message: discord.Message, color: discord.Color | None = None) -> discord.Embed:
    """Create an embed mimicking Discord’s native message appearance."""
    color = color or discord.Color.dark_gray()
    embed = discord.Embed(
        description=message.content or "(no text)",
        timestamp=message.created_at,
        color=color
    )
    embed.set_author(
        name=f"{message.author.display_name} ({message.author.name}#{message.author.discriminator})",
        icon_url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty
    )
    embed.set_footer(text=f"#{message.channel.name}")
    if message.attachments:
        # Show first attachment inline if it's an image
        for attachment in message.attachments:
            if attachment.content_type and "image" in attachment.content_type:
                embed.set_image(url=attachment.url)
                break
        # List all attachments in embed body
        urls = "\n".join(a.url for a in message.attachments)
        embed.add_field(name="📎 Attachments", value=urls, inline=False)
    return embed


async def send_log(message: discord.Message):
    """Send message logs to log channel as embed."""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            color = getattr(message.author.top_role, "color", discord.Color.dark_gray())
            embed = await create_message_embed(message, color=color)
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"[💥] Logging error: {e}")


async def send_alert(message: discord.Message, detected: str):
    """Send alerts to the alert channel."""
    try:
        alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
        if alert_channel:
            embed = await create_message_embed(message, color=discord.Color.red())
            embed.title = "🚨 Name Alert Detected!"
            embed.add_field(name="Detected Term", value=f"`{detected}`", inline=False)
            embed.add_field(name="Jump to Message", value=f"[Click Here]({message.jump_url})", inline=False)
            await alert_channel.send(embed=embed)
    except Exception as e:
        print(f"[💥] Alert error: {e}")


# --- Events ---
@bot.event
async def on_ready():
    print(f"[✅] Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Mirror messages
    await send_log(message)

    # Detect names (regex + fuzzy)
    msg_lower = message.content.lower()
    detected = regex_match(msg_lower, NAME_PATTERNS)
    if not detected:
        detected = fuzzy_match(msg_lower, FUZZY_NAMES)

    if detected:
        await send_alert(message, detected)

    await bot.process_commands(message)


@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return
    embed = discord.Embed(
        title="✏️ Message Edited",
        color=discord.Color.blurple(),
        timestamp=after.edited_at or after.created_at
    )
    embed.set_author(
        name=f"{before.author.display_name} ({before.author.name}#{before.author.discriminator})",
        icon_url=before.author.avatar.url if before.author.avatar else discord.Embed.Empty
    )
    embed.add_field(name="Before", value=before.content or "(no text)", inline=False)
    embed.add_field(name="After", value=after.content or "(no text)", inline=False)
    embed.set_footer(text=f"#{before.channel.name}")
    await log_channel.send(embed=embed)


@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return
    embed = discord.Embed(
        title="🗑️ Message Deleted",
        description=message.content or "(no text)",
        color=discord.Color.orange(),
        timestamp=message.created_at
    )
    embed.set_author(
        name=f"{message.author.display_name} ({message.author.name}#{message.author.discriminator})",
        icon_url=message.author.avatar.url if message.author.avatar else discord.Embed.Empty
    )
    embed.set_footer(text=f"#{message.channel.name}")
    if message.attachments:
        urls = "\n".join(a.url for a in message.attachments)
        embed.add_field(name="📎 Attachments", value=urls, inline=False)
    await log_channel.send(embed=embed)


bot.run(TOKEN)
