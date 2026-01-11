"""
Module for club selection UI components
"""
import discord
from discord.ui import Select, View, Button, Modal, TextInput
import asyncio


def get_country_and_club_ui(member, user_data, get_all_countries_func, get_clubs_by_country_func, get_or_create_club_func):
    """
    Returns UI components for country and club selection.
    
    Args:
        member: Discord member object
        user_data: Dictionary to store selected values {'country': None, 'club': None}
        get_all_countries_func: Function to get all countries from database
        get_clubs_by_country_func: Function to get clubs by country
        get_or_create_club_func: Function to create or get club ID
    
    Returns:
        Tuple of (CountryView, ClubView generator function)
    """
    
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
            existing_countries = get_all_countries_func()
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
            print(f"Selected country1: {user_data['country']}")
            await interaction.response.defer()
            print(f"Selected country2: {user_data['country']}")
            self.view.stop()
            print(f"Selected country3: {user_data['country']}")
    
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
            clubs = get_clubs_by_country_func(country)
            
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
            clubs = get_clubs_by_country_func(country)
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
    
    return CountryView, ClubView


def get_trade_willingness_ui(member, user_data):
    """
    Returns UI component for trade willingness selection.
    
    Args:
        member: Discord member object
        user_data: Dictionary to store selected value {'trade': None}
    
    Returns:
        TradeView class
    """
    
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
    
    return TradeView
