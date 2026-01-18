#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
import asyncio

# Load environment variables from .env file
load_dotenv()

version = "1.0.0"

# Read values from .env file
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
LINE_UP_CHANNEL_ID = int(os.getenv('LINE_UP_CHANNEL_ID'))
# Channel and role IDs for on-join behavior
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
NEWCOMER_ROLE_ID = int(os.getenv('NEWCOMER_ROLE_ID'))
LINE_UP_CHANNEL_ID = int(os.getenv('LINE_UP_CHANNEL_ID', 0))
GROUNDHELP_CHANNEL_ID = int(os.getenv('GROUNDHELP_CHANNEL_ID', 0))
GROUNDHOPPER_ROLE_ID = int(os.getenv('GROUNDHOPPER_ROLE_ID'))
LOGO_URL = os.getenv('LOGO_URL')
DATABASE_NAME = os.getenv('DATABASE_NAME')

if not TOKEN or not DATABASE_NAME:
    print("Error: DISCORD_TOKEN and DATABASE_NAME must be set in the .env file.")
    exit(1)

print(f"Starting Hopper Bot... (version {version}) on server ID {GUILD_ID} with database {DATABASE_NAME}")

# Create bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required to fetch members
intents.reactions = True  # Required to receive reaction events
bot = commands.Bot(command_prefix='!', intents=intents)

def logo2URL(logo_suffix):
    """Converts a logo suffix to a full URL."""
    if logo_suffix.startswith('http://') or logo_suffix.startswith('https://'):
        return logo_suffix
    if logo_suffix and LOGO_URL:
        return LOGO_URL + logo_suffix
    return None

# Initialize database
def init_database():
    """Creates the SQLite database and tables for user profiles and clubs."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Table for leagues
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            logo TEXT,
            tier INTEGER DEFAULT 99,
            UNIQUE(name, country)
        )
    ''')

    # Table for clubs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            league_id INTEGER,
            logo TEXT,
            flag TEXT,
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )
    ''')

    # Table for user profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER,
            guild_id INTEGER,
            club_id INTEGER,
            willingness_to_trade TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
    ''')

    # Table for user tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table for user activity
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity (
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            hits INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, date)
        )
    ''')

    conn.commit()
    conn.close()
    print('Database initialized.')

# Initialize database on startup
init_database()

def get_or_create_league(name, country, tier=99):
    """Finds a league or creates it if it doesn't exist yet."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Check if league already exists
    cursor.execute('SELECT id FROM leagues WHERE name = ? AND country = ?', (name, country))
    result = cursor.fetchone()

    if result:
        league_id = result[0]
    else:
        # Create new league
        cursor.execute('INSERT INTO leagues (name, country, tier) VALUES (?, ?, ?)', (name, country, tier))
        league_id = cursor.lastrowid
        conn.commit()

    conn.close()
    return league_id

def get_or_create_club(name):
    """Finds a club or creates it if it doesn't exist yet."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Check if club already exists
    cursor.execute('SELECT id, league_id FROM clubs WHERE name = ?', (name,))
    result = cursor.fetchone()

    if result:
        club_id = result[0]
        league_id = result[1]
    else:
        # Create new club
        cursor.execute('INSERT INTO clubs (name) VALUES (?)', (name,))
        club_id = cursor.lastrowid
        league_id = None
        conn.commit()

    conn.close()
    return club_id, league_id

def save_user_profile(user_id, guild_id, club_id):
    """Saves the user profile to the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO user_profiles
        (user_id, guild_id, club_id)
        VALUES (?, ?, ?)
    ''', (user_id, guild_id, club_id))

    conn.commit()
    conn.close()

def get_user_profile(user_id, guild_id):
    """Loads the user profile from the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.name, l.country, up.created_at, c.logo, l.name, l.logo, l.tier, l.flag
        FROM user_profiles up
        LEFT JOIN clubs c ON up.club_id = c.id
        LEFT JOIN leagues l ON c.league_id = l.id
        WHERE up.user_id = ? AND up.guild_id = ?
    ''', (user_id, guild_id))

    result = cursor.fetchone()
    conn.close()

    return result

def get_leagues_by_country(country):
    """Fetches all leagues from a country from the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT name FROM leagues WHERE country = ? ORDER BY tier', (country,))
    results = [row[0] for row in cursor.fetchall()]

    conn.close()
    return results

def get_clubs_by_country_and_league(country, league):
    """Fetches all clubs from a country and league from the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.name FROM clubs c
        LEFT JOIN leagues l ON c.league_id = l.id
        WHERE (l.country = ? OR l.country IS NULL)
          AND (l.name = ? OR l.name IS NULL)
        ORDER BY c.name
    ''', (country, league))
    results = [row[0] for row in cursor.fetchall()]

    conn.close()
    return results

def get_clubs_by_country(country):
    """Fetches all clubs from a country from the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.name FROM clubs c
        LEFT JOIN leagues l ON c.league_id = l.id
        WHERE (l.country = ? OR l.country IS NULL)
        ORDER BY c.name
    ''', (country,))
    results = [row[0] for row in cursor.fetchall()]

    conn.close()
    return results

def get_all_countries():
    """Fetches all countries from the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT country FROM leagues ORDER BY country')
    results = [row[0] for row in cursor.fetchall()]

    conn.close()
    return results

def get_club_id_by_name(club_name):
    """Fetches the club ID by club name."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM clubs WHERE name = ?', (club_name,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else None

def update_club_league(club_id, league_id):
    """Updates the league_id of a club."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('UPDATE clubs SET league_id = ? WHERE id = ?', (league_id, club_id))
    conn.commit()
    conn.close()

def update_league_tier(league_id, tier):
    """Updates the tier of a league."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('UPDATE leagues SET tier = ? WHERE id = ?', (tier, league_id))
    conn.commit()
    conn.close()

def get_user_tags(user_id):
    """Fetches all tags for a user."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT tag FROM tags WHERE user_id = ? ORDER BY created_at', (user_id,))
    results = [row[0] for row in cursor.fetchall()]

    conn.close()
    return results

def save_user_tags(user_id, tags):
    """Saves tags for a user. Replaces existing tags."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Delete existing tags
    cursor.execute('DELETE FROM tags WHERE user_id = ?', (user_id,))

    # Insert new tags
    for tag in tags:
        if tag.strip():  # Only save non-empty tags
            cursor.execute('INSERT INTO tags (user_id, tag) VALUES (?, ?)', (user_id, tag.strip()))

    conn.commit()
    conn.close()

def add_user_tags(user_id, tags):
    """Adds tags to a user's existing tags."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Get existing tags to avoid duplicates
    cursor.execute('SELECT tag FROM tags WHERE user_id = ?', (user_id,))
    existing_tags = set(row[0] for row in cursor.fetchall())

    # Insert new tags if they don't exist
    for tag in tags:
        if tag.strip() and tag.strip() not in existing_tags:
            cursor.execute('INSERT INTO tags (user_id, tag) VALUES (?, ?)', (user_id, tag.strip()))

    conn.commit()
    conn.close()

def get_all_tags():
    """Fetches all unique tags from all users."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT tag FROM tags ORDER BY tag')
    results = [row[0] for row in cursor.fetchall()]

    conn.close()
    return results

def increment_activity(user_id):
    """Increments the activity counter for a user for today."""
    from datetime import date
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    today = date.today()
    
    # Try to increment existing record, or insert new one
    cursor.execute('''
        INSERT INTO activity (user_id, date, hits)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, date) 
        DO UPDATE SET hits = hits + 1
    ''', (user_id, today))
    
    conn.commit()
    conn.close()

def get_user_level(user_id):
    """Calculates user level based on activity in the last 2 weeks."""
    from datetime import date, timedelta
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    today = date.today()
    two_weeks_ago = today - timedelta(days=14)
    
    # Count distinct days with activity in the last 2 weeks
    cursor.execute('''
        SELECT COUNT(DISTINCT date)
        FROM activity
        WHERE user_id = ? AND date >= ?
    ''', (user_id, two_weeks_ago))
    
    result = cursor.fetchone()
    conn.close()
    
    active_days = result[0] if result else 0
    
    # Determine level based on active days
    if active_days >= 5:
        return "Ultra"
    elif active_days >= 2:
        return "Fan"
    else:
        return "Casual"

def get_user_activity_days(user_id):
    """Returns the total number of distinct active days for a user."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(DISTINCT date) FROM activity WHERE user_id = ?', (user_id,))
    active_days = cursor.fetchone()[0]
    conn.close()
    return active_days

def post_embeds(channel, msg, embeds):
    """Posts a list of embeds to the specified channel, handling Discord's limit of 10 embeds per message."""
    async def _post():
        for i in range(0, len(embeds), 10):
            if len(msg) > 0 and i == 0:
                await channel.send(msg, embeds=embeds[i:i + 10], allowed_mentions=discord.AllowedMentions.none())
            else:
                await channel.send(embeds=embeds[i:i + 10], allowed_mentions=discord.AllowedMentions.none())
    return _post()

async def post_member_list(guild, channel):
    """Posts the member list sorted by country, league (by tier), and club to the specified channel."""
    # Delete all messages in the channel
    try:
        await channel.purge(limit=100)
        print(f'Messages in channel {channel.name} deleted.')
    except Exception as e:
        print(f'Error deleting messages: {e}')

    # Group members by country, league, and club with league tier information
    countries = {}  # Format: {country: {league_name: {'tier': int, 'clubs': {club_name: [members]}}}}
    logos = {}  # Format: {club_name: logo_url}
    league_tiers = {}  # Format: {(country, league_name): tier}
    flags = {}  # Format: {country: flag}
    levels = {}  # Format: {member_id: level}

    for member in guild.members:
        if member.bot:
            continue  # Skip bots
        data = get_user_profile(member.id, guild.id)

        club_name = None
        country = None
        league_name = None
        tier = None

        if data and data[0]:
            club_name = data[0]
            country = data[1]
            if len(data) > 7:
                league_name = data[4]
                if data[3]:
                    logos[club_name] = data[3]
                if data[5]:
                    logos[league_name] = data[5]
                if data[7]:
                    flags[country] = data[7]
                tier = data[6]
        
        club_name = club_name or 'Unknown'
        country = country or 'Unknown'
        league_name = league_name or 'Unknown'
        flags[country] = flags.get(country, '')
        tier = tier or 99

        entry = f'{member.mention} {get_user_level(member.id)}'

        league_tiers[(country, league_name)] = tier

        # Group by country, league, and club
        if country not in countries:
            countries[country] = {}
        if league_name not in countries[country]:
            countries[country][league_name] = {'tier': tier, 'clubs': {}}
        if club_name not in countries[country][league_name]['clubs']:
            countries[country][league_name]['clubs'][club_name] = []
        countries[country][league_name]['clubs'][club_name].append(entry)

    # Send header message
    await channel.send(f"**Server: {guild.name}**\n**Number of members: {guild.member_count}**")

    # Sort countries ('Unknown' last)
    sorted_countries = sorted(countries.keys(), key=lambda s: (s == 'Unknown', s.lower()))

    for country in sorted_countries:
        await channel.send(f"═══ {country} {flags.get(country, '')} ═══\n")

        # Sort leagues within the country by tier, then alphabetically ('Unknown' last)
        sorted_leagues = sorted(
            countries[country].items(),
            key=lambda x: (x[0] == 'Unknown', x[1]['tier'], x[0].lower())
        )

        for league_name, league_data in sorted_leagues:
            embeds = []
            # Suche nach Name
            msg = f"\n**{league_name}**\n"

            # Sort clubs within the league ('Unknown' last)
            sorted_clubs = sorted(league_data['clubs'].keys(), key=lambda s: (s == 'Unknown', s.lower()))

            for club in sorted_clubs:
                members = league_data['clubs'][club]

                # Create embed with club logo
                embed = discord.Embed(
                    description=", ".join(members),
                    color=discord.Color.green()
                )
                url = logo2URL(logos.get(club, ''))
                if url:
                    embed.set_author(name=f"{club} ({len(members)})", icon_url=url)
                else:
                    embed.set_author(name=f"{club} ({len(members)})")

                embeds.append(embed)

            if len(embeds) > 0:
                await post_embeds(channel, msg, embeds)

    print(f'Member list sent to channel {channel.name}.')

@bot.command()
async def ping(ctx):
    await ctx.send(f'Yes, {ctx.author.mention}, I\'m here ! :robot: :saluting_face: ({version})')

@bot.event
async def on_ready():
    print(f'{bot.user} is logged in!')

    # Sync slash commands
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f'Synced {len(synced)} command(s) to guild {GUILD_ID}')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

    # Find the server (guild)
    guild = bot.get_guild(GUILD_ID)

    if not guild:
        print(f'Server with ID {GUILD_ID} not found.')
        return

    # Find the channel
    channel = bot.get_channel(LINE_UP_CHANNEL_ID)

    if not channel:
        print(f'Channel with ID {LINE_UP_CHANNEL_ID} not found.')
        return

    # Post the member list
    await post_member_list(guild, channel)

@bot.event
async def on_member_join(member):
    """When a new member joins the server:
    - Assign `newcomer` role (create if not exists)
    - Give the role access only to the welcome channel
    - Remove visibility in other channels
    - Ask questions and save answers
    """
    guild = member.guild

    # Get or create the role
    role = guild.get_role(NEWCOMER_ROLE_ID)
    if role is None:
            print(f'Could not create role: {e}')
            return

    # Assign the role to the new member
    try:
        await member.add_roles(role, reason='Assign newcomer role')
        print(f'Role "{role.name}" assigned to {member}')
    except Exception as e:
        print(f'Error assigning role to {member}: {e}')

    # Set channel permissions: Only welcome channel visible
    welcome_channel = None
    for channel in guild.channels:
        try:
            if channel.id == WELCOME_CHANNEL_ID:
                welcome_channel = channel
                # Allow visibility and messages in welcome channel
                await channel.set_permissions(role, view_channel=True, send_messages=True, read_message_history=True)
            else:
                # Hide all other channels for this role
                await channel.set_permissions(role, view_channel=False)
        except Exception as e:
            print(f'Error setting permissions for channel {getattr(channel, "name", channel.id)}: {e}')

    # Ask questions in the welcome channel
    if welcome_channel:
        await welcome_channel.send(
            f"👋 Welcome {member.mention} to **{guild.name}**! "
            f"Please use the `/set-club` command to set your home club."
            "If it does not exist yet, just enter its name "
            "and it will be created automatically.")

    else:
        print(f'Welcome channel with ID {WELCOME_CHANNEL_ID} not found.')

@bot.event
async def on_message(message):
    """Handle messages in the set-club channel."""
    # Ignore bot messages
    if message.author.bot:
        return

    # Increment activity counter for the user
    try:
        increment_activity(message.author.id)
    except Exception as e:
        print(f'Error incrementing activity: {e}')

    # Groundhelp channel: detect !ClubName and notify matching members
    if message.channel.id == GROUNDHELP_CHANNEL_ID:
        try:
            content = message.content
            import re
            matches = re.findall(r'$([^!\n?.!,;:]{5,})', content)
            if matches:
                guild = message.guild
                notified = []
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                for raw in matches:
                    query = raw.strip()
                    if not query:
                        continue

                    # exact match (case-insensitive)
                    cursor.execute('SELECT id, name FROM clubs WHERE LOWER(name) = LOWER(?)', (query,))
                    rows = cursor.fetchall()
                    if not rows:
                        cursor.execute('SELECT id, name FROM clubs WHERE LOWER(name) LIKE LOWER(?)', (f'%{query}%',))
                        rows = cursor.fetchall()

                    if not rows:
                        continue

                    club_ids = [r[0] for r in rows]
                    # fetch user_ids for these clubs in this guild
                    placeholders = ','.join('?' for _ in club_ids)
                    params = (*club_ids, guild.id)
                    cursor.execute(f'SELECT user_id FROM user_profiles WHERE club_id IN ({placeholders}) AND guild_id = ?', params)
                    for (uid,) in cursor.fetchall():
                        member = guild.get_member(uid)
                        if member:
                            notified.append(member)

                conn.close()

                # uniq
                unique = []
                seen = set()
                for m in notified:
                    if m.id not in seen:
                        unique.append(m)
                        seen.add(m.id)

                if not unique:
                    await message.channel.send('Keine Mitglieder mit dem gesuchten Verein gefunden.')
                else:
                    mentions = ' '.join(m.mention for m in unique)
                    allowed = discord.AllowedMentions(users=True)
                    embed = discord.Embed(title='Groundhelp Anfrage', description=message.content, color=discord.Color.orange())
                    embed.set_author(name=message.author.display_name, icon_url=getattr(message.author.avatar, 'url', None) if hasattr(message.author, 'avatar') else None)
                    await message.channel.send(content=mentions, embed=embed, allowed_mentions=allowed)

                return
        except Exception as e:
            print(f'Error in groundhelp handler: {e}')

    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    """Handle reactions to messages."""
    # Ignore bot reactions
    if user.bot:
        return
    
    print(f'Reaction added by {user} to message ID {reaction.message.id}')
    # Increment activity counter for the user
    try:
        increment_activity(user.id)
    except Exception as e:
        print(f'Error incrementing activity on reaction: {e}')

# Autocomplete functions
async def country_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for country selection."""
    countries = get_all_countries()
    # Add common countries
    default_countries = ['Germany', 'Austria', 'Switzerland', 'England', 'Spain', 'Italy', 'France', 'Netherlands', 'Portugal', 'Belgium']
    all_countries = list(set(countries + default_countries))
    all_countries.sort()

    # Filter based on current input
    if current:
        filtered = [c for c in all_countries if current.lower() in c.lower()]
    else:
        filtered = all_countries

    return [app_commands.Choice(name=country, value=country) for country in filtered[:25]]

async def league_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for league selection."""
    # Get country from namespace (already selected parameter)
    country = interaction.namespace.country if hasattr(interaction.namespace, 'country') else None

    if not country:
        return []

    leagues = get_leagues_by_country(country)

    # Filter based on current input
    if current:
        filtered = [l for l in leagues if current.lower() in l.lower()]
    else:
        filtered = leagues

    return [app_commands.Choice(name=league, value=league) for league in filtered[:25]]

async def club_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for club selection."""
    # Get country and league from namespace (already selected parameters)
    country = interaction.namespace.country if hasattr(interaction.namespace, 'country') else None
    league = interaction.namespace.league if hasattr(interaction.namespace, 'league') else None

    if not country:
        return []

    if league:
        clubs = get_clubs_by_country_and_league(country, league)
    else:
        clubs = get_clubs_by_country(country)

    # Filter based on current input
    if current:
        filtered = [c for c in clubs if current.lower() in c.lower()]
    else:
        filtered = clubs

    return [app_commands.Choice(name=club, value=club) for club in filtered[:25]]

# Autocomplete for tags
async def tag_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for tag selection."""
    all_tags = get_all_tags()

    # Filter based on current input
    if current:
        filtered = [t for t in all_tags if current.lower() in t.lower()]
    else:
        filtered = all_tags

    return [app_commands.Choice(name=tag, value=tag) for tag in filtered[:25]]

# Slash command: /set-club
@bot.tree.command(name="set-club", description="Set or update your home club", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    country="The country your club is from",
    club="Your home club name"
)
@app_commands.autocomplete(country=country_autocomplete, club=club_autocomplete)
async def set_club_command(
    interaction: discord.Interaction,
    country: str,
    club: str
):
    """Slash command to set or update user's club."""
    await interaction.response.defer(ephemeral=True)

    member = interaction.user
    guild = interaction.guild

    # Create or find the club in the database
    club_id, league_id = get_or_create_club(club)

    # Save profile
    save_user_profile(member.id, guild.id, club_id)

    await interaction.followup.send(
        f"✅ Your club has been updated!\n\n"
        f"**Country:** {country}\n"
        f"**Club:** {club}",
        ephemeral=True
    )

    # Remove user from newcomer role if they have it
    role = guild.get_role(NEWCOMER_ROLE_ID)
    groundhopper_role = guild.get_role(GROUNDHOPPER_ROLE_ID)
    if role in member.roles:
        try:
            await member.remove_roles(role, reason='User set club, removing newcomer role')
            print(f'Removed newcomer role from {member}')
            await member.add_roles(groundhopper_role, reason='User set club, removing newcomer role')
        except Exception as e:
            print(f'Error removing newcomer role from {member}: {e}')

    # Update member list
    lineup_channel = bot.get_channel(LINE_UP_CHANNEL_ID)
    if lineup_channel:
        try:
            await post_member_list(guild, lineup_channel)
        except Exception as e:
            print(f'Error updating member list: {e}')

    if league_id is None:
        await interaction.followup.send(
            f"⚠️ Note: The club '{club}' is not yet assigned to a league. "
            f"Please contact an admin or update the league information yourself "
            f"with the /update-league command.",
            ephemeral=True
        )
# Slash command: /update-league
@bot.tree.command(name="update-league", description="Update a club's league and tier", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    country="The country of the league",
    club="The club to update",
    league="The new league for the club",
    league_tier="The league tier/level (1=top tier, 2=second tier, etc.)"
)
@app_commands.autocomplete( club=club_autocomplete, league=league_autocomplete, country=country_autocomplete)
async def update_league_command(
    interaction: discord.Interaction,
    country: str,
    club: str,
    league: str,
    league_tier: int
):
    """Update a club's league assignment and tier."""
    await interaction.response.defer(ephemeral=True)

    # Get club information
    club_id = get_club_id_by_name(club)
    
    if not club_id:
        await interaction.followup.send(
            f"❌ Club '{club}' not found in the database.",
            ephemeral=True
        )
        return

    # Get or create the league with tier
    league_id = get_or_create_league(league, country, league_tier)

    # Update league tier
    update_league_tier(league_id, league_tier)

    # Update the club's league
    update_club_league(club_id, league_id)

    await interaction.followup.send(
        f"✅ Club '{club}' has been updated!\n\n"
        f"**Club:** {club}\n"
        f"**Country:** {country}\n"
        f"**New League:** {league} (Tier {league_tier})",
        ephemeral=True
    )

    # Update member list
    guild = interaction.guild
    lineup_channel = bot.get_channel(LINE_UP_CHANNEL_ID)
    if lineup_channel:
        try:
            await post_member_list(guild, lineup_channel)
        except Exception as e:
            print(f'Error updating member list: {e}')

# Slash command: /profile
@bot.tree.command(name="profile", description="Show a user's profile", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="The member to show profile for (leave empty for yourself)")
async def profile_command(interaction: discord.Interaction, member: discord.Member = None):
    """Shows a user's profile."""
    if member is None:
        member = interaction.user

    active_days = get_user_activity_days(member.id)

    profile = get_user_profile(member.id, interaction.guild.id)

    club = ["", "", ""]
    if profile:
        club[0] = profile[0] if profile[0] else 'Unknown'
        club[1] = profile[4] if len(profile) > 4 and profile[4] else 'Unknown'
        club[2] = profile[7] if len(profile) > 7 and profile[7] else profile[1]
        created_at = profile[2]
        club_logo = profile[3] if len(profile) > 3 and profile[3] else None
        
        club_text = " - ".join(club)
        # Get user tags
        tags = get_user_tags(member.id)
        tags_str = ', '.join(tags) if tags else 'No tags set'
        
        level = get_user_level(member.id)

        embed = discord.Embed(title=f"Profile of {member.display_name} ({level})", color=discord.Color.blue())
        url = logo2URL(club_logo)
        if url:
            embed.set_thumbnail(url=url)
        embed.add_field(name="⚽ Home club", value=club_text , inline=False)
        embed.add_field(name="🏷️ Tags", value=tags_str, inline=False)
        embed.add_field(name="📅 Active days", value=str(active_days), inline=False)
        embed.set_footer(text=f"Created on: {created_at}")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"No profile found for {member.display_name}.", ephemeral=True)

# Slash command: /tags
@bot.tree.command(name="tags", description="Set or update your tags (replaces all existing tags)", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(tags="Enter your tags separated by commas (e.g., 'Scarves, Pins, Programs')")
@app_commands.autocomplete(tags=tag_autocomplete)
async def tags_command(interaction: discord.Interaction, tags: str):
    """Slash command to set or update user's tags."""
    member = interaction.user
    guild = interaction.guild
    
    # Split tags by comma and clean up
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    if not tag_list:
        await interaction.response.send_message("❌ Please provide at least one tag.", ephemeral=True)
        return
    
    # Save tags
    save_user_tags(member.id, tag_list)
    
    await interaction.response.send_message(
        f"✅ Your tags have been updated!\n\n"
        f"**Tags:** {', '.join(tag_list)}",
        ephemeral=True
    )

# Slash command: /add-tag
@bot.tree.command(name="add-tag", description="Add new tags to your existing tags", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(tags="Enter new tags separated by commas (e.g., 'Scarves, Pins')")
@app_commands.autocomplete(tags=tag_autocomplete)
async def add_tag_command(interaction: discord.Interaction, tags: str):
    """Slash command to add tags to user's existing tags."""
    member = interaction.user
    
    # Split tags by comma and clean up
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    if not tag_list:
        await interaction.response.send_message("❌ Please provide at least one tag.", ephemeral=True)
        return
    
    # Get existing tags
    existing_tags = get_user_tags(member.id)
    
    # Add tags
    add_user_tags(member.id, tag_list)
    
    # Get updated tags
    updated_tags = get_user_tags(member.id)
    
    await interaction.response.send_message(
        f"✅ Tags added successfully!\n\n"
        f"**Your tags:** {', '.join(updated_tags)}",
        ephemeral=True
    )

# Start the bot
bot.run(TOKEN)
