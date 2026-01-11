import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
import asyncio

# Load environment variables from .env file
load_dotenv()

# Read values from .env file
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
# Channel and role IDs for on-join behavior
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
NEWCOMER_ROLE_ID = int(os.getenv('NEWCOMER_ROLE_ID'))
SET_CLUB_CHANNEL_ID = int(os.getenv('SET_CLUB_CHANNEL_ID'))

# Create bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required to fetch members
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database
def init_database():
    """Creates the SQLite database and tables for user profiles and clubs."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    # Table for clubs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL
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
    
    conn.commit()
    conn.close()
    print('Database initialized.')

# Initialize database on startup
init_database()

def get_or_create_club(name, country):
    """Finds a club or creates it if it doesn't exist yet."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    # Check if club already exists
    cursor.execute('SELECT id FROM clubs WHERE name = ?', (name,))
    result = cursor.fetchone()
    
    if result:
        club_id = result[0]
    else:
        # Create new club
        cursor.execute('INSERT INTO clubs (name, country) VALUES (?, ?)', (name, country))
        club_id = cursor.lastrowid
        conn.commit()
    
    conn.close()
    return club_id

def save_user_profile(user_id, guild_id, club_id, willingness_to_trade):
    """Saves the user profile to the database."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_profiles 
        (user_id, guild_id, club_id, willingness_to_trade)
        VALUES (?, ?, ?, ?)
    ''', (user_id, guild_id, club_id, willingness_to_trade))
    
    conn.commit()
    conn.close()

def get_user_profile(user_id, guild_id):
    """Loads the user profile from the database."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.name, c.country, up.willingness_to_trade, up.created_at
        FROM user_profiles up
        LEFT JOIN clubs c ON up.club_id = c.id
        WHERE up.user_id = ? AND up.guild_id = ?
    ''', (user_id, guild_id))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def get_clubs_by_country(country):
    """Fetches all clubs from a country from the database."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM clubs WHERE country = ? ORDER BY name', (country,))
    results = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return results

def get_all_countries():
    """Fetches all countries from the database."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT country FROM clubs ORDER BY country')
    results = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return results

async def post_member_list(guild, channel):
    """Posts the member list sorted by country and club to the specified channel."""
    # Delete all messages in the channel
    try:
        await channel.purge(limit=100)
        print(f'Messages in channel {channel.name} deleted.')
    except Exception as e:
        print(f'Error deleting messages: {e}')
    
    # Group members by country and club
    countries = {}  # Format: {country: {club_name: [members]}}
    
    for member in guild.members:
        if member.bot:
            continue  # Skip bots
        data = get_user_profile(member.id, guild.id)
        
        if data and data[0]:
            club_name = data[0].strip()
            country = data[1].strip() if data[1] else 'Unknown'
        else:
            club_name = 'Unknown'
            country = 'Unknown'

        entry = member.name
        
        # Group by country and club
        if country not in countries:
            countries[country] = {}
        if club_name not in countries[country]:
            countries[country][club_name] = []
        countries[country][club_name].append(entry)

    # Create message grouped by country and club
    message = f"**Server: {guild.name}**\n"
    message += f"**Number of members: {guild.member_count}**\n\n"
    
    # Sort countries ('Unknown' last)
    sorted_countries = sorted(countries.keys(), key=lambda s: (s == 'Unknown', s.lower()))
    
    for country in sorted_countries:
        message += f"═══ **{country}** ═══\n\n"
        
        # Sort clubs within the country
        sorted_clubs = sorted(countries[country].keys(), key=lambda s: (s == 'Unknown', s.lower()))
        
        for club in sorted_clubs:
            members = countries[country][club]
            message += f"**{club}** ({len(members)})\n"
            message += "\n".join(members) + "\n\n"
    
    # Send message (split if too long)
    if len(message) > 2000:
        # Discord has a limit of 2000 characters per message
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            await channel.send(chunk)
    else:
        await channel.send(message)
    
    print(f'Member list sent to channel {channel.name}.')

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
    channel = bot.get_channel(CHANNEL_ID)
    
    if not channel:
        print(f'Channel with ID {CHANNEL_ID} not found.')
        return
    
    # Post the member list
    await post_member_list(guild, channel)


async def ask_user_questions(member, guild, welcome_channel):
    """Asks the new member to use /set-club command."""
    
    try:
        # Welcome message with instructions to use slash command
        await welcome_channel.send(
            f"{member.mention}, welcome to the server **{guild.name}** ⚽\n\n"
            f"Please use the `/set-club` command to set up your profile!\n\n"
            f"Type `/set-club` and fill in:\n"
            f"• **country** - Your club's country (with autocomplete)\n"
            f"• **club** - Your home club name (with autocomplete)\n"
            f"• **willingness_to_trade** - Whether you want to trade memorabilia\n\n"
            f"After completing your profile, you'll get access to all channels!"
        )
        
        # Wait for profile creation (check every 5 seconds for up to 5 minutes)
        for _ in range(60):
            await asyncio.sleep(5)
            profile = get_user_profile(member.id, guild.id)
            if profile:
                # Profile created, remove newcomer role
                role = guild.get_role(NEWCOMER_ROLE_ID)
                if role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason='Profile completed')
                        print(f'Newcomer role removed from {member.name} - profile completed')
                    except Exception as e:
                        print(f'Error removing role: {e}')
                
                club_name, club_country = profile[0], profile[1]
                await welcome_channel.send(
                    f"{member.mention} ✅ Welcome! Your profile is complete.\n\n"
                    f"**Home club:** {club_name} ({club_country})\n\n"
                    "You now have access to all channels! Have fun! ⚽"
                )
                
                # Update member list
                lineup_channel = bot.get_channel(CHANNEL_ID)
                if lineup_channel:
                    try:
                        await post_member_list(guild, lineup_channel)
                    except Exception as e:
                        print(f'Error updating member list: {e}')
                
                return True
        
        # Timeout - remind user
        await welcome_channel.send(
            f"{member.mention} ⏱️ Don't forget to complete your profile with `/set-club`!"
        )
        
    except Exception as e:
        print(f"Error asking questions: {e}")
        await welcome_channel.send(f"{member.mention} There was an error. Please contact an admin.")
        return False

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
        success = await ask_user_questions(member, guild, welcome_channel)
        if success:
            print(f'Profile for {member.name} successfully saved.')
    else:
        print(f'Welcome channel with ID {WELCOME_CHANNEL_ID} not found.')

@bot.event
async def on_message(message):
    """Handle messages in the set-club channel."""
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Check if message is in set-club channel
    if message.channel.id == SET_CLUB_CHANNEL_ID:
        # Delete user message to keep channel clean
        try:
            await message.delete()
        except:
            pass
        
        # Remind user to use slash command
        reminder = await message.channel.send(
            f"{message.author.mention} Please use the `/set-club` command to update your profile!"
        )
        
        # Delete reminder after 10 seconds
        await asyncio.sleep(10)
        try:
            await reminder.delete()
        except:
            pass
        
        return
    
    # Process commands
    await bot.process_commands(message)

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

async def club_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for club selection."""
    # Get country from namespace (already selected parameter)
    country = interaction.namespace.country if hasattr(interaction.namespace, 'country') else None
    
    if not country:
        return []
    
    clubs = get_clubs_by_country(country)
    
    # Filter based on current input
    if current:
        filtered = [c for c in clubs if current.lower() in c.lower()]
    else:
        filtered = clubs
    
    return [app_commands.Choice(name=club, value=club) for club in filtered[:25]]

# Slash command: /set-club
@bot.tree.command(name="set-club", description="Set or update your home club", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    country="The country your club is from",
    club="Your home club name",
    willingness_to_trade="Are you willing to trade memorabilia?"
)
@app_commands.autocomplete(country=country_autocomplete, club=club_autocomplete)
@app_commands.choices(willingness_to_trade=[
    app_commands.Choice(name="Yes", value="Yes"),
    app_commands.Choice(name="No", value="No"),
    app_commands.Choice(name="Maybe", value="Maybe")
])
async def set_club_command(
    interaction: discord.Interaction,
    country: str,
    club: str,
    willingness_to_trade: app_commands.Choice[str] = None
):
    """Slash command to set or update user's club."""
    await interaction.response.defer(ephemeral=True)
    
    member = interaction.user
    guild = interaction.guild
    
    # Create or find the club in the database
    club_id = get_or_create_club(club, country)
    
    # Get current profile to check if updating or creating
    current_profile = get_user_profile(member.id, guild.id)
    
    # Determine willingness to trade
    if willingness_to_trade:
        trade_value = willingness_to_trade.value
    elif current_profile:
        trade_value = current_profile[2]  # Keep existing value
    else:
        trade_value = 'Unknown'
    
    # Save profile
    save_user_profile(member.id, guild.id, club_id, trade_value)
    
    await interaction.followup.send(
        f"✅ Your club has been updated!\n\n"
        f"**Home club:** {club} ({country})\n"
        f"**Willingness to trade:** {trade_value}",
        ephemeral=True
    )
    
    # Update member list
    lineup_channel = bot.get_channel(CHANNEL_ID)
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
    
    profile = get_user_profile(member.id, interaction.guild.id)
    
    if profile:
        club_name, club_country, willingness_to_trade, created_at = profile
        embed = discord.Embed(title=f"Profile of {member.display_name}", color=discord.Color.blue())
        embed.add_field(name="⚽ Home club", value=f"{club_name} ({club_country})", inline=False)
        embed.add_field(name="🔄 Willingness to trade", value=willingness_to_trade, inline=False)
        embed.set_footer(text=f"Created on: {created_at}")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"No profile found for {member.display_name}.", ephemeral=True)

@bot.command(name='profile')
async def show_profile(ctx, member: discord.Member = None):
    """Shows a user's profile."""
    if member is None:
        member = ctx.author
    
    profile = get_user_profile(member.id, ctx.guild.id)
    
    if profile:
        club_name, club_country, willingness_to_trade, created_at = profile
        embed = discord.Embed(title=f"Profile of {member.display_name}", color=discord.Color.blue())
        embed.add_field(name="⚽ Home club", value=f"{club_name} ({club_country})", inline=False)
        embed.add_field(name="🔄 Willingness to trade", value=willingness_to_trade, inline=False)
        embed.set_footer(text=f"Created on: {created_at}")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"No profile found for {member.display_name}.")

# Start the bot
bot.run(TOKEN)
