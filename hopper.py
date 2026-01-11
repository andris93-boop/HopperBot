import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
import asyncio

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

# Datenbank initialisieren
def init_database():
    """Erstellt die SQLite-Datenbank und die Tabellen für Nutzerprofile und Vereine."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    # Tabelle für Vereine
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL
        )
    ''')
    
    # Tabelle für Nutzerprofile
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER,
            guild_id INTEGER,
            club_id INTEGER,
            tausch_bereitschaft TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print('Datenbank initialisiert.')

# Datenbank beim Start initialisieren
init_database()

def get_or_create_club(name, country):
    """Findet einen Verein oder erstellt ihn, falls er noch nicht existiert."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    # Prüfe, ob der Verein bereits existiert
    cursor.execute('SELECT id FROM clubs WHERE name = ?', (name,))
    result = cursor.fetchone()
    
    if result:
        club_id = result[0]
    else:
        # Erstelle neuen Verein
        cursor.execute('INSERT INTO clubs (name, country) VALUES (?, ?)', (name, country))
        club_id = cursor.lastrowid
        conn.commit()
    
    conn.close()
    return club_id

def save_user_profile(user_id, guild_id, club_id, tausch_bereitschaft):
    """Speichert das Nutzerprofil in der Datenbank."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_profiles 
        (user_id, guild_id, club_id, tausch_bereitschaft)
        VALUES (?, ?, ?, ?)
    ''', (user_id, guild_id, club_id, tausch_bereitschaft))
    
    conn.commit()
    conn.close()

def get_user_profile(user_id, guild_id):
    """Lädt das Nutzerprofil aus der Datenbank."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.name, c.country, up.tausch_bereitschaft, up.created_at
        FROM user_profiles up
        LEFT JOIN clubs c ON up.club_id = c.id
        WHERE up.user_id = ? AND up.guild_id = ?
    ''', (user_id, guild_id))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

async def post_member_list(guild, channel):
    """Postet die Mitgliederliste nach Land und Heimatverein sortiert in den angegebenen Kanal."""
    # Gruppiere Mitglieder nach Land und Verein
    countries = {}  # Format: {land: {club_name: [members]}}
    
    for member in guild.members:
        if member.bot:
            continue  # Überspringe Bots
        data = get_user_profile(member.id, guild.id)
        
        if data and data[0]:
            club_name = data[0].strip()
            country = data[1].strip() if data[1] else 'Unbekannt'
        else:
            club_name = 'Unbekannt'
            country = 'Unbekannt'

        entry = member.name
        
        # Gruppiere nach Land und Club
        if country not in countries:
            countries[country] = {}
        if club_name not in countries[country]:
            countries[country][club_name] = []
        countries[country][club_name].append(entry)

    # Erstelle die Nachricht gruppiert nach Land und Heimatverein
    message = f"**Server: {guild.name}**\n"
    message += f"**Anzahl der Mitglieder: {guild.member_count}**\n\n"
    
    # Sortiere Länder ('Unbekannt' zuletzt)
    sorted_countries = sorted(countries.keys(), key=lambda s: (s == 'Unbekannt', s.lower()))
    
    for country in sorted_countries:
        message += f"═══ **{country}** ═══\n\n"
        
        # Sortiere Clubs innerhalb des Landes
        sorted_clubs = sorted(countries[country].keys(), key=lambda s: (s == 'Unbekannt', s.lower()))
        
        for club in sorted_clubs:
            members = countries[country][club]
            message += f"**{club}** ({len(members)})\n"
            message += "\n".join(members) + "\n\n"
    
    # Sende die Nachricht (aufgeteilt, falls zu lang)
    if len(message) > 2000:
        # Discord hat ein Limit von 2000 Zeichen pro Nachricht
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            await channel.send(chunk)
    else:
        await channel.send(message)
    
    print(f'Mitgliederliste wurde in den Kanal {channel.name} gesendet.')

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
    
    # Poste die Mitgliederliste
    await post_member_list(guild, channel)


async def ask_user_questions(member, guild, welcome_channel):
    """Stellt dem neuen Mitglied Fragen im Welcome-Kanal und speichert die Antworten."""
    
    def check(message):
        return message.author == member and message.channel.id == WELCOME_CHANNEL_ID
    
    try:
        # Sende die erste Frage im Welcome-Kanal
        await welcome_channel.send(
            f"{member.mention}, willkommen auf dem Server **{guild.name}** ⚽\n\n"
            "Bitte beantworte ein paar Fragen, damit wir dich besser kennenlernen können.\n\n"
            "**Frage 1/3:** Was ist dein Heimatfußballverein?"
        )
        
        # Warte auf Antwort 1
        try:
            msg1 = await bot.wait_for('message', check=check, timeout=300.0)
            heimatverein = msg1.content
        except asyncio.TimeoutError:
            await welcome_channel.send(f"{member.mention} ⏱️ Zeit abgelaufen. Bitte kontaktiere einen Admin.")
            return False
        
        # Frage 2
        await welcome_channel.send(f"{member.mention} **Frage 2/4:** Aus welchem Land kommt dein Verein?")
        try:
            msg2 = await bot.wait_for('message', check=check, timeout=300.0)
            land = msg2.content
        except asyncio.TimeoutError:
            await welcome_channel.send(f"{member.mention} ⏱️ Zeit abgelaufen. Bitte kontaktiere einen Admin.")
            return False
        
        # Erstelle oder finde den Verein in der Datenbank
        club_id = get_or_create_club(heimatverein, land)
        
        # Frage 3
        await welcome_channel.send(
            f"{member.mention} **Frage 3/3:** Bist du bereit, Devotionalien (Trikots, Schals, etc.) zu tauschen?\n"
            "Antworte mit: **Ja**, **Nein** oder **Vielleicht**"
        )
        try:
            msg3 = await bot.wait_for('message', check=check, timeout=300.0)
            tausch_bereitschaft = msg3.content
        except asyncio.TimeoutError:
            await welcome_channel.send(f"{member.mention} ⏱️ Zeit abgelaufen. Bitte kontaktiere einen Admin.")
            return False
        
        # Speichere die Daten in der Datenbank
        save_user_profile(member.id, guild.id, club_id, tausch_bereitschaft)
        
        # Entferne die Newcomer-Rolle für automatische Freischaltung
        role = guild.get_role(NEWCOMER_ROLE_ID)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason='Onboarding abgeschlossen')
                print(f'Newcomer-Rolle von {member.name} entfernt - automatisch freigeschaltet')
            except Exception as e:
                print(f'Fehler beim Entfernen der Rolle: {e}')
        
        await welcome_channel.send(
            f"{member.mention} ✅ Vielen Dank! Deine Angaben wurden gespeichert.\n\n"
            f"**Heimatverein:** {heimatverein} ({land})\n"
            f"**Tauschbereitschaft:** {tausch_bereitschaft}\n\n"
            "Du wurdest freigeschaltet und hast jetzt Zugriff auf alle Kanäle! Viel Spaß! ⚽"
        )
        
        # Aktualisiere die Mitgliederliste im #line-up Kanal
        lineup_channel = bot.get_channel(CHANNEL_ID)
        if lineup_channel:
            try:
                # Lösche alle Nachrichten im Kanal
                await lineup_channel.purge(limit=100)
                print(f'Nachrichten im Kanal {lineup_channel.name} gelöscht.')
                
                # Poste die aktualisierte Mitgliederliste
                await post_member_list(guild, lineup_channel)
            except Exception as e:
                print(f'Fehler beim Aktualisieren der Mitgliederliste: {e}')
        
        return True
        
    except Exception as e:
        print(f"Fehler beim Stellen der Fragen: {e}")
        await welcome_channel.send(f"{member.mention} Es gab einen Fehler. Bitte kontaktiere einen Admin.")
        return False

@bot.event
async def on_member_join(member):
    """Wenn ein neues Mitglied dem Server beitritt:
    - Rolle `newcommer` zuweisen (erstellt, falls nicht vorhanden)
    - Der Rolle nur Zugriff auf den Welcome-Kanal geben
    - In anderen Kanälen Sichtbarkeit entziehen
    - Fragen stellen und Antworten speichern
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
    welcome_channel = None
    for channel in guild.channels:
        try:
            if channel.id == WELCOME_CHANNEL_ID:
                welcome_channel = channel
                # Erlaube Sichtbarkeit und Nachrichten im Welcome-Kanal
                await channel.set_permissions(role, view_channel=True, send_messages=True, read_message_history=True)
            else:
                # Verberge alle anderen Kanäle für diese Rolle
                await channel.set_permissions(role, view_channel=False)
        except Exception as e:
            print(f'Fehler beim Setzen von Berechtigungen für Kanal {getattr(channel, "name", channel.id)}: {e}')
    
    # Stelle die Fragen im Welcome-Kanal
    if welcome_channel:
        success = await ask_user_questions(member, guild, welcome_channel)
        if success:
            print(f'Profil für {member.name} erfolgreich gespeichert.')
    else:
        print(f'Welcome-Kanal mit ID {WELCOME_CHANNEL_ID} nicht gefunden.')

@bot.command(name='profil')
async def show_profile(ctx, member: discord.Member = None):
    """Zeigt das Profil eines Nutzers an."""
    if member is None:
        member = ctx.author
    
    profile = get_user_profile(member.id, ctx.guild.id)
    
    if profile:
        club_name, club_country, tausch_bereitschaft, created_at = profile
        embed = discord.Embed(title=f"Profil von {member.display_name}", color=discord.Color.blue())
        embed.add_field(name="⚽ Heimatverein", value=f"{club_name} ({club_country})", inline=False)
        embed.add_field(name=" Tauschbereitschaft", value=tausch_bereitschaft, inline=False)
        embed.set_footer(text=f"Erstellt am: {created_at}")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"Für {member.display_name} wurde kein Profil gefunden.")

# Starte den Bot
bot.run(TOKEN)
