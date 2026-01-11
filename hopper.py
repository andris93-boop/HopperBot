import discord
from discord.ext import commands
from discord.ui import Select, View, Button, Modal, TextInput
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
    """Asks the new member questions with dropdown menus and saves the answers."""
    
    user_data = {'country': None, 'club': None, 'trade': None}
    
    # Modal for manual input (country)
    class CountryModal(Modal, title='Enter country'):
        country_input = TextInput(label='Which country is your club from?', placeholder='e.g. Germany')
        
        async def on_submit(self, interaction: discord.Interaction):
            user_data['country'] = self.country_input.value
            await interaction.response.defer()
    
    # Modal for manual input (club)
    class ClubModal(Modal, title='Enter club'):
        club_input = TextInput(label='What is your club called?', placeholder='e.g. FC Bayern Munich')
        
        async def on_submit(self, interaction: discord.Interaction):
            user_data['club'] = self.club_input.value
            await interaction.response.defer()
    
    # Step 1: Select country
    class CountrySelect(Select):
        def __init__(self):
            # Get existing countries from DB
            existing_countries = get_all_countries()
            # Add common countries if not already present
            default_countries = ['Germany', 'Austria', 'Switzerland', 'England', 'Spain', 'Italy', 'France']
            all_countries = list(set(existing_countries + default_countries))
            all_countries.sort()
            
            options = [discord.SelectOption(label=country, value=country) for country in all_countries[:25]]
            super().__init__(placeholder='Choose your club\'s country...', options=options, min_values=1, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != member.id:
                await interaction.response.send_message("This is not for you!", ephemeral=True)
                return
            user_data['country'] = self.values[0]
            await interaction.response.defer()
            self.view.stop()
    
    class CountryView(View):
        def __init__(self):
            super().__init__(timeout=300)
            self.add_item(CountrySelect())
        
        @discord.ui.button(label='✏️ Other country', style=discord.ButtonStyle.secondary)
        async def other_country(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != member.id:
                await interaction.response.send_message("This is not for you!", ephemeral=True)
                return
            await interaction.response.send_modal(CountryModal())
            await asyncio.sleep(1)  # Wait for modal submit
            if user_data['country']:
                self.stop()
    
    # Step 2: Select club
    class ClubSelect(Select):
        def __init__(self, country):
            clubs = get_clubs_by_country(country)
            
            if len(clubs) == 0:
                options = [discord.SelectOption(label='No clubs available', value='none')]
            else:
                options = [discord.SelectOption(label=club, value=club) for club in clubs[:25]]
            
            super().__init__(placeholder='Choose your club...', options=options, min_values=1, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != member.id:
                await interaction.response.send_message("This is not for you!", ephemeral=True)
                return
            if self.values[0] != 'none':
                user_data['club'] = self.values[0]
            await interaction.response.defer()
            self.view.stop()
    
    class ClubView(View):
        def __init__(self, country):
            super().__init__(timeout=300)
            clubs = get_clubs_by_country(country)
            if clubs:
                self.add_item(ClubSelect(country))
        
        @discord.ui.button(label='✏️ Other club', style=discord.ButtonStyle.secondary)
        async def other_club(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != member.id:
                await interaction.response.send_message("This is not for you!", ephemeral=True)
                return
            await interaction.response.send_modal(ClubModal())
            await asyncio.sleep(1)  # Wait for modal submit
            if user_data['club']:
                self.stop()
    
    # Step 3: Willingness to trade
    class TradeSelect(Select):
        def __init__(self):
            options = [
                discord.SelectOption(label='Yes', value='Yes', emoji='✅'),
                discord.SelectOption(label='No', value='No', emoji='❌'),
                discord.SelectOption(label='Maybe', value='Maybe', emoji='🤔')
            ]
            super().__init__(placeholder='Are you willing to trade?', options=options, min_values=1, max_values=1)
        
        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != member.id:
                await interaction.response.send_message("This is not for you!", ephemeral=True)
                return
            user_data['trade'] = self.values[0]
            await interaction.response.defer()
            self.view.stop()
    
    class TradeView(View):
        def __init__(self):
            super().__init__(timeout=300)
            self.add_item(TradeSelect())
    
    try:
        # Welcome message
        await welcome_channel.send(
            f"{member.mention}, welcome to the server **{guild.name}** ⚽\n\n"
            "Please answer a few questions so we can get to know you better."
        )
        
        # Question 1: Country
        country_view = CountryView()
        await welcome_channel.send(f"{member.mention} **Question 1/3:** Which country is your club from?", view=country_view)
        await country_view.wait()
        
        if not user_data['country']:
            await welcome_channel.send(f"{member.mention} ⏱️ Time expired. Please contact an admin.")
            return False
        
        # Question 2: Club
        club_view = ClubView(user_data['country'])
        await welcome_channel.send(f"{member.mention} **Question 2/3:** Which club from {user_data['country']}?", view=club_view)
        await club_view.wait()
        
        if not user_data['club']:
            await welcome_channel.send(f"{member.mention} ⏱️ Time expired. Please contact an admin.")
            return False
        
        # Create or find the club in the database
        club_id = get_or_create_club(user_data['club'], user_data['country'])
        
        # Question 3: Willingness to trade
        trade_view = TradeView()
        await welcome_channel.send(
            f"{member.mention} **Question 3/3:** Are you willing to trade memorabilia (jerseys, scarves, etc.)?",
            view=trade_view
        )
        await trade_view.wait()
        
        if not user_data['trade']:
            await welcome_channel.send(f"{member.mention} ⏱️ Time expired. Please contact an admin.")
            return False
        
        # Save data to database
        save_user_profile(member.id, guild.id, club_id, user_data['trade'])
        
        # Remove newcomer role for automatic unlock
        role = guild.get_role(NEWCOMER_ROLE_ID)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason='Onboarding completed')
                print(f'Newcomer role removed from {member.name} - automatically unlocked')
            except Exception as e:
                print(f'Error removing role: {e}')
        
        await welcome_channel.send(
            f"{member.mention} ✅ Thank you! Your information has been saved.\n\n"
            f"**Home club:** {user_data['club']} ({user_data['country']})\n"
            f"**Willingness to trade:** {user_data['trade']}\n\n"
            "You have been unlocked and now have access to all channels! Have fun! ⚽"
        )
        
        # Update member list in #line-up channel
        lineup_channel = bot.get_channel(CHANNEL_ID)
        if lineup_channel:
            try:
                # Post updated member list (deletion happens in post_member_list)
                await post_member_list(guild, lineup_channel)
            except Exception as e:
                print(f'Error updating member list: {e}')
        
        return True
        
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
