import discord
from discord.ext import commands

# Configuration
TOKEN = 'MTM3NjA5NTQyOTA5OTI1Nzg1Ng.GiHnr3.ycpIIs3Nh4jyROeAzdqrZgAIoW3OHO0hdnt3tU'  # Replace with your bot token
TRIGGER_PHRASE = 'stop arguing in general'
TRIGGER_USER_ID = [
    530402087004143626,
    1060424009193377852
]

# Users to strip/give back roles
USERS_TO_STRIP = [
    402289705531736076,
    963477332914479104,
    799762393545965568
]

ROLE_TO_GIVE = 1157604959492251679  # Role to assign after stripping
FORGIVENESS_PHRASES = [
    "i'm sorry",
    "I'm sorry",
    "im sorry",
    "Im sorry",
    "sorry",
    "my bad",
    "i apologise",
    "i apologize"
]

# Store removed roles per user
original_roles = {}

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'[✅] Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'[ℹ️] Bot is ready and listening for trigger phrase.')

@bot.event
async def on_message(message):
    print(f'[📨] Received: "{message.content}" from {message.author} (ID: {message.author.id})')

    if message.author == bot.user:
        return

    guild = message.guild
    if not guild:
        await bot.process_commands(message)
        return

    # If authorized user says the trigger phrase, strip roles
    if message.author.id in TRIGGER_USER_ID and message.content.strip().lower() == TRIGGER_PHRASE.lower():
        print(f'[⚡] Trigger phrase received from authorized user.')
        try:
            async for member in guild.fetch_members(limit=None):
                if member.id in USERS_TO_STRIP:
                    print(f'[👤] Processing target member: {member.display_name} (ID: {member.id})')

                    try:
                        # Remove all roles except @everyone and store the originals
                        roles_to_remove = [role for role in member.roles if role.name != "@everyone"]
                        original_roles[member.id] = roles_to_remove.copy()

                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove)
                            print(f'  [🧹] Removed roles: {[role.name for role in roles_to_remove]}')

                        # Add punishment role
                        new_role = guild.get_role(ROLE_TO_GIVE)
                        if new_role:
                            await member.add_roles(new_role)
                            print(f'  [➕] Assigned punishment role: {new_role.name}')

                    except discord.Forbidden:
                        print(f'[🚫] Missing permission to modify {member.display_name}')
                    except Exception as e:
                        print(f'[💥] Unexpected error with {member.display_name}: {e}')
        except Exception as e:
            print(f'[💥] Error fetching members: {e}')

    # If punished user says "I'm sorry", restore roles
    elif message.content.strip().lower() in FORGIVENESS_PHRASES and message.author.id in USERS_TO_STRIP:
        member = message.author
        print(f'[🙏] Forgiveness detected from {member.display_name} (ID: {member.id})')

        try:
            # Remove punishment role
            punish_role = guild.get_role(ROLE_TO_GIVE)
            if punish_role in member.roles:
                await member.remove_roles(punish_role)
                print(f'  [🗑️] Removed punishment role: {punish_role.name}')

            # Restore original roles
            if member.id in original_roles:
                roles_to_restore = original_roles[member.id]
                await member.add_roles(*roles_to_restore)
                print(f'  [🎁] Restored roles: {[role.name for role in roles_to_restore]}')
                del original_roles[member.id]  # Clear record after restoring
            else:
                print(f'  [❗] No stored roles to restore for {member.display_name}')

        except Exception as e:
            print(f'[💥] Error restoring roles for {member.display_name}: {e}')

    await bot.process_commands(message)

bot.run(TOKEN)
