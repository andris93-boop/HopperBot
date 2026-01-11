import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Lade die Umgebungsvariablen aus der .env Datei
load_dotenv()

# Lese die Werte aus der .env Datei
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
# Kanal- und Rollen-IDs für das On-Join-Verhalten
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
NEWCOMER_ROLE_ID = int(os.getenv('NEWCOMER_ROLE_ID'))

# Erstelle den Bot mit Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Benötigt, um Mitglieder abzurufen
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} ist eingeloggt!')
    
    # Finde den Server (Guild)
    guild = bot.get_guild(GUILD_ID)
    
    if not guild:
        print(f'Server mit ID {GUILD_ID} wurde nicht gefunden.')
        return
    
    # Finde den Kanal
    channel = bot.get_channel(CHANNEL_ID)
    
    if not channel:
        print(f'Kanal mit ID {CHANNEL_ID} wurde nicht gefunden.')
        return
    
    # Erstelle eine Liste aller Nutzer
    member_list = []
    for member in guild.members:
        status_emoji = "🟢" if member.status == discord.Status.online else "⚪"
        member_list.append(f"{status_emoji} {member.name} ({member.display_name})")
    
    # Erstelle die Nachricht
    message = f"**Server: {guild.name}**\n"
    message += f"**Anzahl der Mitglieder: {guild.member_count}**\n\n"
    message += "**Mitgliederliste:**\n"
    message += "\n".join(member_list)
    
    # Sende die Nachricht (aufgeteilt, falls zu lang)
    if len(message) > 2000:
        # Discord hat ein Limit von 2000 Zeichen pro Nachricht
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            await channel.send(chunk)
    else:
        await channel.send(message)
    
    print(f'Mitgliederliste wurde in den Kanal {channel.name} gesendet.')
    print(f'Anzahl der Mitglieder: {guild.member_count}')


@bot.event
async def on_member_join(member):
    """Wenn ein neues Mitglied dem Server beitritt:
    - Rolle `newcommer` zuweisen (erstellt, falls nicht vorhanden)
    - Der Rolle nur Zugriff auf den Welcome-Kanal geben
    - In anderen Kanälen Sichtbarkeit entziehen
    """
    guild = member.guild

    # Hole oder erstelle die Rolle
    role = guild.get_role(NEWCOMER_ROLE_ID)
    if role is None:
            print(f'Konnte Rolle nicht erstellen: {e}')
            return

    # Weise die Rolle dem neuen Mitglied zu
    try:
        await member.add_roles(role, reason='Assign newcomer role')
        print(f'Rolle "{role.name}" an {member} vergeben')
    except Exception as e:
        print(f'Fehler beim Zuweisen der Rolle an {member}: {e}')

    # Setze Kanalberechtigungen: Nur Welcome-Kanal sichtbar
    for channel in guild.channels:
        try:
            if channel.id == WELCOME_CHANNEL_ID:
                # Erlaube Sichtbarkeit und Nachrichten im Welcome-Kanal
                await channel.set_permissions(role, view_channel=True, send_messages=True, read_message_history=True)
                if isinstance(channel, discord.TextChannel):
                    try:
                        await channel.send(f'Willkommen {member.mention}! Du wurdest als Newcomer zugewiesen.')
                    except Exception:
                        pass
            else:
                # Verberge alle anderen Kanäle für diese Rolle
                await channel.set_permissions(role, view_channel=False)
        except Exception as e:
            print(f'Fehler beim Setzen von Berechtigungen für Kanal {getattr(channel, "name", channel.id)}: {e}')

# Starte den Bot
bot.run(TOKEN)
