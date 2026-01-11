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

# Erstelle den Bot mit Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} ist eingeloggt!')
    
    # Finde den Kanal
    channel = bot.get_channel(CHANNEL_ID)
    
    if channel:
        # Sende eine Nachricht in den Kanal
        await channel.send('Hallo! Ich bin der Hopper-Bot und bin jetzt online! 🤖')
        print(f'Nachricht wurde in den Kanal {channel.name} gesendet.')
    else:
        print(f'Kanal mit ID {CHANNEL_ID} wurde nicht gefunden.')

# Starte den Bot
bot.run(TOKEN)
