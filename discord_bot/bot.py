import discord
from discord.ext import commands
import json
import os

# --- Configuration ---
TOKEN = os.getenv("TOKEN")

TRIGGER_PHRASE = 'GUYS STOP FIGHTING!!!'
TRIGGER_USER_IDS = [530402087004143626, 1060424009193377852]
USERS_TO_STRIP = [402289705531736076, 499881568991576064]
ROLE_TO_GIVE = 1376619581660991518

FORGIVENESS_PHRASES = [
    "i'm sorry", "sorry", "my bad", "i apologise", "i apologize",
    "Sorry", "SORRY", "I'm Sorry", "I'm sorry", "im sorry", "Im sorry"
]
UNDO_PHRASES = ['undo', 'never mind']

# Log channel ID (replace with your actual channel)
LOG_CHANNEL_ID = 1430766113721028658  

DATA_DIR = os.path.join(os.getcwd(), "data")
ROLES_FILE = os.path.join(DATA_DIR, "roles.json")

os.makedirs(DATA_DIR, exist_ok=True)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Role persistence helpers ---
def load_roles():
    try:
        if os.path.exists(ROLES_FILE):
            if os.path.isdir(ROLES_FILE):
                print(f"[❌] ERROR: {ROLES_FILE} is a directory, not a file.")
                return {}
        else:
            with open(ROLES_FILE, 'w') as f:
                json.dump({}, f)
                print(f"[📁] Created new roles file at {ROLES_FILE}")

        with open(ROLES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[💥] Failed to load roles file: {e}")
        return {}

def save_roles(data):
    with open(ROLES_FILE, 'w') as f:
        json.dump(data, f)

original_roles = load_roles()

# --- Utility for sending formatted log entries ---
async def send_log(bot, content: str):
    """Safely send logs to the configured channel."""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(content)
    except Exception as e:
        print(f"[💥] Logging error: {e}")

# --- Bot events ---
@bot.event
async def on_ready():
    print(f'[✅] Logged in as {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_message(message):
    if message.author == bot.user or not message.guild:
        return

    msg = message.content.strip().lower()
    author_id = str(message.author.id)
    guild = message.guild

    # --- Mirror all user messages ---
    if not message.author.bot and message.channel.id != LOG_CHANNEL_ID:
        display_name = message.author.display_name
        full_name = f"{message.author.name}#{message.author.discriminator}"
        log_entry = f"[#{message.channel.name}] **{display_name}** ({full_name}): {message.content}"
        if message.attachments:
            attachment_urls = "\n".join([a.url for a in message.attachments])
            log_entry += f"\n📎 Attachments:\n{attachment_urls}"
        await send_log(bot, log_entry)

    # --- Handle punishment trigger ---
    if message.author.id in TRIGGER_USER_IDS and msg == TRIGGER_PHRASE:
        print(f'[⚡] Trigger by {message.author}')
        try:
            async for member in guild.fetch_members(limit=None):
                if member.id in USERS_TO_STRIP:
                    roles_to_remove = [r for r in member.roles if r.name != "@everyone"]
                    original_roles[str(member.id)] = [r.id for r in roles_to_remove]
                    save_roles(original_roles)
                    print(f"[📦] Current stored roles: {json.dumps(original_roles, indent=2)}")

                    if roles_to_remove:
                        await member.remove_roles(*roles_to_remove)
                        print(f'[🧹] Removed roles from {member.display_name}')

                    punishment_role = guild.get_role(ROLE_TO_GIVE)
                    if punishment_role:
                        await member.add_roles(punishment_role)
                        print(f'[➕] Assigned punishment role to {member.display_name}')
        except Exception as e:
            print(f'[💥] Punishment error: {e}')

    # --- Handle forgiveness ---
    elif int(author_id) in USERS_TO_STRIP and msg in FORGIVENESS_PHRASES:
        if author_id not in original_roles:
            print(f'[ℹ️] No saved roles for {message.author}')
        else:
            try:
                role_ids = original_roles[author_id]
                roles = [guild.get_role(rid) for rid in role_ids if guild.get_role(rid)]
                if roles:
                    await message.author.add_roles(*roles)
                    print(f'[🎉] Restored roles to {message.author.display_name}')
                punishment_role = guild.get_role(ROLE_TO_GIVE)
                if punishment_role:
                    await message.author.remove_roles(punishment_role)
                del original_roles[author_id]
                save_roles(original_roles)
            except Exception as e:
                print(f'[💥] Restore error for {message.author}: {e}')

    # --- Handle undo by trusted users ---
    elif message.author.id in TRIGGER_USER_IDS and msg in UNDO_PHRASES:
        try:
            for user_id in USERS_TO_STRIP:
                str_id = str(user_id)
                member = guild.get_member(user_id)
                if not member or str_id not in original_roles:
                    continue

                role_ids = original_roles[str_id]
                roles = [guild.get_role(rid) for rid in role_ids if guild.get_role(rid)]
                if roles:
                    await member.add_roles(*roles)
                    print(f'[↩️] Restored roles to {member.display_name}')
                punishment_role = guild.get_role(ROLE_TO_GIVE)
                if punishment_role:
                    await member.remove_roles(punishment_role)
                del original_roles[str_id]
                save_roles(original_roles)
        except Exception as e:
            print(f'[💥] Undo error: {e}')

    await bot.process_commands(message)

# --- Log message edits ---
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.channel.id == LOG_CHANNEL_ID:
        return

    display_name = before.author.display_name
    full_name = f"{before.author.name}#{before.author.discriminator}"
    log_entry = (
        f"✏️ **Message Edited** by **{display_name}** ({full_name}) in "
        f"[#{before.channel.name}]\n"
        f"**Before:** {before.content}\n"
        f"**After:** {after.content}"
    )
    await send_log(bot, log_entry)

# --- Log message deletions ---
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild or message.channel.id == LOG_CHANNEL_ID:
        return

    display_name = message.author.display_name
    full_name = f"{message.author.name}#{message.author.discriminator}"
    log_entry = (
        f"🗑️ **Message Deleted** by **{display_name}** ({full_name}) in "
        f"[#{message.channel.name}]\n"
        f"**Content:** {message.content or '(no text)'}"
    )
    if message.attachments:
        attachment_urls = "\n".join([a.url for a in message.attachments])
        log_entry += f"\n📎 Attachments:\n{attachment_urls}"
    await send_log(bot, log_entry)

bot.run(TOKEN)
