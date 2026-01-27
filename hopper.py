#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from database import HopperDatabase

# Load environment variables from .env file
load_dotenv()

version = "1.4.1"

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

# Initialize database
db = HopperDatabase(DATABASE_NAME)

# Create bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required to fetch members
intents.reactions = True  # Required to receive reaction events
bot = commands.Bot(command_prefix='!', intents=intents)

default_color = discord.Color.blue()

 # Maximum number of users to mention in a single groundhelp ping
MAX_MENTIONS = 10
# When True the bot will try to create a thread for the groundhelp request (requires permissions)
CREATE_THREAD_ON_PING = False


class ConfirmPingView(discord.ui.View):
    def __init__(self, author, channel, mentions, public_embed, allowed_mentions, matched_query):
        super().__init__(timeout=300)
        self.author = author
        self.channel = channel
        self.mentions = mentions
        self.public_embed = public_embed
        self.allowed_mentions = allowed_mentions
        self.matched_query = matched_query

    @discord.ui.button(label='OK', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message('Nur der ursprüngliche Autor kann bestätigen.', ephemeral=True)
            return
        # send public message
        try:
            content = ' '.join(m.mention for m in self.mentions)
            sent = await self.channel.send(content=content, embed=self.public_embed, allowed_mentions=self.allowed_mentions)
            await interaction.response.send_message('Nachricht wurde gesendet.', ephemeral=True)
            # optionally create thread
            if CREATE_THREAD_ON_PING and self.matched_query:
                try:
                    thread = await sent.create_thread(name=f'Groundhelp: {self.matched_query}', auto_archive_duration=1440)
                    print(f'Groundhelp: created thread id={getattr(thread, "id", None)}')
                except Exception as e:
                    print(f'Could not create thread after confirm: {e}')
        except Exception as e:
            print(f'Error sending confirmed groundhelp mentions: {e}')
            await interaction.response.send_message('Fehler beim Senden der Nachricht.', ephemeral=True)
        # disable buttons
        for child in list(self.children):
            child.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label='Abbrechen', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message('Nur der ursprüngliche Autor kann abbrechen.', ephemeral=True)
            return
        await interaction.response.send_message('Abgebrochen.', ephemeral=True)
        for child in list(self.children):
            child.disabled = True
        await interaction.message.edit(view=self)
def nbsp(text):
    """Replaces all regular spaces with non-breaking spaces."""
    return text.replace(' ', '\u00A0')

def logo2URL(logo_suffix):
    """Converts a logo suffix to a full URL."""
    if not logo_suffix:
        return None
    if logo_suffix.startswith('http://') or logo_suffix.startswith('https://'):
        return logo_suffix
    if LOGO_URL:
        return LOGO_URL + logo_suffix
    return None

def format_club_info(result):
    """Formats raw club info tuple into a dictionary.

    Args:
        result: Tuple from database (name, league_name, country, logo, tier, flag, id, color, league_logo)

    Returns:
        Dictionary with formatted club information or None
    """
    if not result:
        return None

    data = {}
    data["name"] = result[0] if result[0] else 'Unknown'
    data["league"] = result[1] if result[1] else 'Unknown'
    data["country"] = result[2] if result[2] else 'Unknown'
    data["club_logo"] = logo2URL(result[3]) if result[3] else ''
    data["tier"] = result[4] if result[4] else 99
    data["flag"] = result[5] if result[5] else ''
    data["club_id"] = result[6]
    data["color"] = discord.Color(int(result[7], 16)) if result[7] else default_color
    data["league_logo"] = logo2URL(result[8]) if result[8] else ''
    data["no_league"] = not result[1] or not result[2]
    return data

def embed_for_club(club: dict):
    """Creates a Discord embed for a club."""
    embed = discord.Embed(
        color=club['color']
    )
    if club['club_logo'] != "":
        embed.set_thumbnail(url=club['club_logo'])
    return embed

def post_embeds(channel, msg, embeds):
    """Posts a list of embeds to the specified channel, handling Discord's limit of 10 embeds per message."""
    async def _post():
        for i in range(0, len(embeds), 10):
            if len(msg) > 0 and i == 0:
                await channel.send(msg, embeds=embeds[i:i + 10], allowed_mentions=discord.AllowedMentions.none())
            else:
                await channel.send(embeds=embeds[i:i + 10], allowed_mentions=discord.AllowedMentions.none())
    return _post()

def post_member_list(guild):
    """ checks if a member list is already posted and queues it if necessary."""
    async def _post():
        # Check if there's already a posting task running
        if hasattr(bot, 'posting_task') and bot.posting_task and not bot.posting_task.done():
            print('A member list posting is already in progress. Queuing the new request.')
            # Wait for the existing task to finish
            await bot.posting_task
            print('Previous posting task completed. Starting the queued task.')

        # Start a new posting task
        bot.posting_task = asyncio.create_task(_post_member_list(guild))
        await bot.posting_task

    return _post()

default_color = discord.Color.blue()

async def _post_member_list(guild):
    """Posts the member list sorted by country, league (by tier), and club to the specified channel."""
    # Find the channel
    channel = bot.get_channel(LINE_UP_CHANNEL_ID)

    if not channel:
        print(f'Channel with ID {LINE_UP_CHANNEL_ID} not found.')
        return

    # Delete all messages in the channel
    try:
        await channel.purge(limit=100)
        print(f'Messages in channel {channel.name} deleted.')
    except Exception as e:
        print(f'Error deleting messages: {e}')

    # Group members by country, league, and club with league tier information
    clubs = {}  # Cache club info
    no_league_clubs = set()

    def get_club(club_id):
        if club_id not in clubs:
            club = format_club_info(db.get_club_info(club_id))
            if not club:
                return None
            clubs[club_id] = club
            if club["no_league"]:
                no_league_clubs.add(club_id)
            club["members"] = []
            club["experts"] = []
        return clubs[club_id]

    for member in guild.members:
        if member.bot:
            continue  # Skip bots
        club_id, _ = db.get_user_profile(guild.id, member.id)
        club = get_club(club_id)
        if not club:
            continue  # Skip members without a club

        lvl = db.get_user_level(member.id)
        club["members"].append(nbsp(f'{member.mention} 🥇 {lvl}'))

    expert_data = db.get_all_expert_clubs(guild.id)
    for (user_id, club_id) in expert_data:
        member_obj = guild.get_member(user_id)
        if not member_obj:
            continue
        club = get_club(club_id)
        if not club:
            continue

        lvl = db.get_user_level(user_id)
        club["experts"].append(nbsp(f'{member_obj.mention} 🥈 {lvl}'))

    # Send header message
    await channel.send(f"**Server: {guild.name}**\n**Number of members: {guild.member_count}**")

    club_ids = db.get_club_ids_sorted_by_country_and_tier()
    print(f'Total clubs: {len(club_ids)}, Total clubs with members: {len(clubs)}')
    club_ids.extend(no_league_clubs - set(club_ids))
    country = ""
    league = ""
    msg = ""

    embeds = []
    for club_id in club_ids:
        if not club_id in clubs:
            continue
        club = clubs[club_id]

        if club["league"] != league or club["country"] != country:
            if len(embeds) > 0:
                await post_embeds(channel, msg, embeds)
                embeds = []

        if club["country"] != country:
            country = club["country"]
            await channel.send(f'═══ {country} {club["flag"]} ═══\n')

        if club["league"] != league:
            league = club["league"]
            msg = f"\n**{league}**\n"

        # Create embed with club logo
        embed = embed_for_club(club)
        embed.description = ", ".join(club["members"])
        if "experts" in club and len(club["experts"]) > 0:
            embed.add_field(name=f'Experts ({len(club["experts"])})',
                value=", ".join(club["experts"]), inline=False)
        embed.set_author(name=f"{club['name']} ({len(club['members'])})")
        embeds.append(embed)

    if len(embeds) > 0:
        await post_embeds(channel, msg, embeds)
        embeds = []

    await asyncio.sleep(10)  # To avoid hitting rate limits
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

    # Post the member list
    await post_member_list(guild)

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
            f"Please use the `/set-club` command to set your home club. "
            "If it does not exist yet, just enter its name "
            "and it will be created automatically. "
            "Please mute the line-up and bot-command channels "
            "to avoid a notification overload. "
            )

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
        db.increment_activity(message.author.id)
    except Exception as e:
        print(f'Error incrementing activity: {e}')

    # Groundhelp channel: detect $ClubName and notify matching members
    if message.channel.id == GROUNDHELP_CHANNEL_ID:
        try:
            content = message.content
            import re
            # Match $ followed by club name (allow spaces, stop at newline, punctuation or next $). Minimum length 3
            matches = re.findall(r'\$([^\n!?\.,;:\$]{3,})', content)
            if matches:
                guild = message.guild
                print(f'Groundhelp: matches={matches} from={message.author} channel={getattr(message.channel, "name", message.channel.id)}')
                notified = []
                notified_expert_ids = set()
                matched_query = None
                club_display_names = []
                token_to_name = {}
                info = None
                club_logo_url = None
                club_ids = []
                league_names = set()
                league_list = []
                league_logo_map = {}
                league_logo_candidate = None
                for raw in matches:
                    query = raw.strip()
                    if not query:
                        continue
                    matched_query = query

                    # Prefer exact match via DB wrapper
                    club_id = db.get_club_id_by_name(query)
                    print(f'Groundhelp: lookup club "{query}" -> club_id={club_id}')
                    if not club_id:
                        # Try fuzzy search (LIKE)
                        like_matches = db.search_clubs_by_name_like(query, limit=10)
                        print(f'Groundhelp: like search for "{query}" -> {len(like_matches)} matches')
                        if len(like_matches) == 0:
                            # No club found at all
                            await message.channel.send('Club not found')
                            continue
                        if len(like_matches) > 5:
                            await message.channel.send('entry matches too many clubs')
                            continue
                        if len(like_matches) == 1:
                            club_id = like_matches[0][0]
                        else:
                            # Multiple (but <=5) matches: ask user to be more specific
                            names = ', '.join([m[1] for m in like_matches])
                            await message.channel.send(f'Multiple clubs match: {names} — please be more specific')
                            continue

                    members_data = db.get_members_by_club_id(guild.id, club_id)
                    # fetch display name and logo from DB if possible
                    info = db.get_club_info(club_id)
                    if info and info[0]:
                        if info[0] not in club_display_names:
                            club_display_names.append(info[0])
                        token_to_name[query] = info[0]
                        try:
                            club_ids.append(club_id)
                            # league name at index 1, league logo at index 8 (if present)
                            league_name = info[1] if len(info) > 1 else None
                            if league_name:
                                league_names.add(league_name)
                                league_list.append(league_name)
                            # store per-league logo candidate if present
                            if len(info) > 8 and info[8]:
                                try:
                                    if league_name and league_name not in league_logo_map:
                                        league_logo_map[league_name] = info[8]
                                except Exception:
                                    pass
                            # fallback first-seen candidate (kept for compatibility)
                            if len(info) > 8 and info[8] and not league_logo_candidate:
                                league_logo_candidate = info[8]
                        except Exception:
                            pass
                    else:
                        token_to_name[query] = None
                    if info and len(info) > 3 and info[3]:
                        # prefer first club logo if multiple
                        if not club_logo_url:
                            club_logo_url = logo2URL(info[3])
                    for (uid,) in members_data:
                        member = guild.get_member(uid)
                        if member:
                            notified.append(member)
                    print(f'Groundhelp: found {len(members_data)} members, appended {len(notified)} so far')

                    # include experts for this club (exclude duplicates later)
                    try:
                        expert_user_ids = db.get_expert_users_for_club(guild.id, club_id)
                        for uid in expert_user_ids:
                            member = guild.get_member(uid)
                            if member:
                                notified.append(member)
                                notified_expert_ids.add(uid)
                        print(f'Groundhelp: added {len(expert_user_ids)} expert ids, total appended {len(notified)} so far')
                    except Exception as e:
                        print(f'Error fetching expert users for club {club_id}: {e}')

                # Deduplicate
                unique = []
                seen = set()
                for m in notified:
                    if m.id not in seen:
                        unique.append(m)
                        seen.add(m.id)

                if not unique:
                    # No regular members found; check if there are experts to ping
                    try:
                        expert_user_ids = db.get_expert_users_for_club(guild.id, club_id)
                        expert_members = []
                        for uid in expert_user_ids:
                            m = guild.get_member(uid)
                            if m:
                                expert_members.append(m)
                        if expert_members:
                            # use experts as recipients
                            unique = expert_members
                        else:
                            # Club exists but truly no active members in this guild
                            name_to_show = (club_display_names[0] if club_display_names else matched_query)
                            # Build and show club profile embed with 0 members
                            club_dict = format_club_info(info) if info else None
                            if club_dict:
                                try:
                                    club_embed = embed_for_club(club_dict)
                                    club_embed.title = f"⚽ {club_dict['name']}"
                                    club_embed.description = f"**League:** {club_dict['league']} (Tier {club_dict['tier']})\n**Country:** {club_dict['country']} {club_dict['flag']}"
                                    club_embed.add_field(name="Members (0)", value="No members", inline=False)
                                    # experts (should be none here)
                                    expert_user_ids = db.get_expert_users_for_club(guild.id, club_dict['club_id'])
                                    expert_mentions = []
                                    for uid in expert_user_ids:
                                        m = guild.get_member(uid)
                                        if m:
                                            expert_mentions.append(m.mention)
                                    if expert_mentions:
                                        club_embed.add_field(name=f"Experts ({len(expert_mentions)})", value=", ".join(expert_mentions), inline=False)
                                    await message.channel.send('No members', embed=club_embed)
                                except Exception as e:
                                    print(f'Error showing club profile for no-members case: {e}')
                                    await message.channel.send(f'{name_to_show} has no active members')
                            else:
                                await message.channel.send(f'{name_to_show} has no active members')
                    except Exception as e:
                        print(f'Error checking experts for club {club_id}: {e}')
                        await message.channel.send('No members')
                else:
                    limited = unique[:MAX_MENTIONS]
                    mentions = ' '.join(m.mention for m in limited)
                    allowed = discord.AllowedMentions(users=True)
                    # Use the DB club name(s) in the embed title when available
                    combined_club_name = ', '.join(club_display_names) if club_display_names else None
                    embed_title = f'Groundhelp Anfrage — {combined_club_name}' if combined_club_name else 'Groundhelp Anfrage'
                    # Determine embed color from DB if available
                    club_color = discord.Color.orange()
                    try:
                        if info and len(info) > 7 and info[7]:
                            raw = str(info[7]).strip()
                            # remove leading # or 0x if present
                            if raw.startswith('#'):
                                raw = raw[1:]
                            if raw.lower().startswith('0x'):
                                raw = raw[2:]
                            if len(raw) == 6 and all(c in '0123456789abcdefABCDEF' for c in raw):
                                club_color = discord.Color(int(raw, 16))
                    except Exception:
                        club_color = discord.Color.orange()

                    # Build embed description: replace $club tokens inline with DB names when available
                    try:
                        desc = content
                        for raw_token in matches:
                            if raw_token:
                                name = token_to_name.get(raw_token)
                                if name:
                                    # replace only first occurrence
                                    desc = re.sub(r'\$' + re.escape(raw_token), name, desc, count=1)
                                else:
                                    # remove the token if no match
                                    desc = re.sub(r'\$' + re.escape(raw_token), '', desc, count=1)
                        # collapse whitespace and strip
                        desc = re.sub(r'\s+', ' ', desc).strip()
                        if not desc:
                            desc = message.content
                    except Exception:
                        desc = message.content

                    # Decide on thumbnail: prefer a league logo when a majority of referenced clubs share one league
                    try:
                        chosen_league = None
                        if len(club_ids) > 1 and len(league_list) > 0:
                            # count occurrences per league
                            counts = {}
                            for ln in league_list:
                                counts[ln] = counts.get(ln, 0) + 1
                            # find most common league
                            most_common_league = max(counts.items(), key=lambda x: x[1]) if counts else (None, 0)
                            league_name, league_count = most_common_league
                            # require strict majority (> half) or at least 2 clubs
                            if league_name and league_count >= 2 and league_name in league_logo_map and league_logo_map[league_name]:
                                club_logo_url = logo2URL(league_logo_map[league_name])
                                chosen_league = league_name
                            # else, keep first-seen club logo (club_logo_url)
                    except Exception:
                        chosen_league = None

                    # DEBUG: show collected club/league info and the thumbnail chosen
                    try:
                        print(f'Groundhelp DEBUG: club_ids={club_ids} league_names={list(league_names)} league_list={league_list} league_logo_map_keys={list(league_logo_map.keys())} chosen_league={chosen_league} league_logo_candidate={league_logo_candidate} club_logo_url={club_logo_url}')
                    except Exception:
                        pass

                    # Use desc (with inline replacements) as embed description
                    embed = discord.Embed(title=embed_title, description=desc, color=club_color)
                    if club_logo_url:
                        try:
                            embed.set_thumbnail(url=club_logo_url)
                        except Exception:
                            pass

                    # Note: Recipients list removed from public embed to avoid duplicate mentions; mentions will appear in the message content
                    embed.set_author(name=message.author.display_name, icon_url=getattr(message.author.avatar, 'url', None) if hasattr(message.author, 'avatar') else None)
                    # Send a private preview to the author with confirmation button
                    try:
                        # preview embed: include message content (without $ tokens) and a compact list of profiles
                        # Embed title: show combined club name(s) (no 'Vorschau:' prefix)
                        preview_title = combined_club_name if combined_club_name else 'Groundhelp Anfrage'
                        preview = discord.Embed(title=preview_title, description=desc, color=club_color)
                        if club_logo_url:
                            try:
                                preview.set_thumbnail(url=club_logo_url)
                            except Exception:
                                pass

                        # Show users to be pinged (count in parentheses) and list them below with medal+status
                        try:
                            user_lines = []
                            for m in limited:
                                try:
                                    lvl = db.get_user_level(m.id)
                                except Exception:
                                    lvl = ''
                                medal = '🥈' if getattr(m, 'id', None) in notified_expert_ids else '🥇'
                                user_lines.append(f"{m.mention} {medal} {lvl}")
                            preview.add_field(name=f'Users to be pinged ({len(limited)})', value='\n'.join(user_lines) if user_lines else 'None', inline=False)
                        except Exception:
                            preview.add_field(name=f'Users to be pinged ({len(limited)})', value='None', inline=False)

                        # If fewer than 3 users will be pinged, send immediately without confirmation
                        if len(unique) < 3:
                            try:
                                content = ' '.join(m.mention for m in limited)
                                sent = await message.channel.send(content=content, embed=embed, allowed_mentions=allowed)
                                # optionally create thread
                                if CREATE_THREAD_ON_PING and matched_query:
                                    try:
                                        thread = await sent.create_thread(name=f'Groundhelp: {matched_query}', auto_archive_duration=1440)
                                        print(f'Groundhelp: created thread id={getattr(thread, "id", None)}')
                                    except Exception as e:
                                        print(f'Could not create thread after immediate send: {e}')
                            except Exception as e:
                                print(f'Error sending immediate groundhelp mentions: {e}')
                                await message.channel.send('Fehler beim direkten Senden der Groundhelp-Nachricht.')
                        else:
                            view = ConfirmPingView(author=message.author, channel=message.channel, mentions=limited, public_embed=embed, allowed_mentions=allowed, matched_query=matched_query)

                            try:
                                # Send a short DM header and the embed (embed already contains the message preview)
                                dm_text = 'Message Preview:'
                                await message.author.send(content=dm_text, embed=preview, view=view)
                            except Exception as e:
                                # Could not send DM (privacy settings); fallback: send temporary preview in channel (visible) then continue
                                print(f'Could not DM preview: {e}; sending temporary preview in channel')
                                temp_header = f'{message.author.mention} Message Preview:'
                                temp = await message.channel.send(f'{temp_header}', embed=preview)
                                await temp.delete(delay=20)

                    except Exception as e:
                        print(f'Error preparing preview/confirmation: {e}')
                        await message.channel.send('Fehler beim Erstellen der Vorschau.')
                        return

                    # Inform if we truncated the list (still inform the author via DM or fallback)
                    if len(unique) > MAX_MENTIONS:
                        try:
                            await message.author.send(f'Es wurden {len(unique)} Mitglieder gefunden — nur die ersten {MAX_MENTIONS} werden nach Bestätigung erwähnt.')
                        except Exception:
                            await message.channel.send(f'Es wurden {len(unique)} Mitglieder gefunden — nur die ersten {MAX_MENTIONS} werden erwähnt.')

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
        db.increment_activity(user.id)
    except Exception as e:
        print(f'Error incrementing activity on reaction: {e}')

# Autocomplete functions
async def country_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for country selection."""
    countries = db.get_all_countries()
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

    leagues = db.get_leagues_by_country(country)

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
        clubs = db.get_clubs_by_country_and_league(country, league)
    else:
        clubs = db.get_clubs_by_country(country)

    # Filter based on current input
    if current:
        filtered = [c for c in clubs if current.lower() in c.lower()]
    else:
        filtered = clubs

    return [app_commands.Choice(name=club, value=club) for club in filtered[:25]]

# Autocomplete for tags
async def tag_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for tag selection."""
    all_tags = db.get_all_tags()

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
    club_id, league_id = db.get_or_create_club(club)

    # Save profile
    db.save_user_profile(guild.id, member.id, club_id)

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

    await post_member_list(guild)

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
    club_id = db.get_club_id_by_name(club)
    
    if not club_id:
        await interaction.followup.send(
            f"❌ Club '{club}' not found in the database.",
            ephemeral=True
        )
        return

    # Get or create the league with tier
    league_id = db.get_or_create_league(league, country, league_tier)

    # Update league tier
    db.update_league_tier(league_id, league_tier)

    # Update the club's league
    db.update_club_league(club_id, league_id)

    await interaction.followup.send(
        f"✅ Club '{club}' has been updated!\n\n"
        f"**Club:** {club}\n"
        f"**Country:** {country}\n"
        f"**New League:** {league} (Tier {league_tier})",
        ephemeral=True
    )

    # Update member list
    await post_member_list(interaction.guild)

# Slash command: /profile
@bot.tree.command(name="profile", description="Show a user's profile", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="The member to show profile for (leave empty for yourself)")
async def profile_command(interaction: discord.Interaction, member: discord.Member = None):
    """Shows a user's profile."""
    if member is None:
        member = interaction.user

    active_days = db.get_user_activity_days(member.id)

    club_id, created_at = db.get_user_profile(interaction.guild.id, member.id)
    if not club_id:
        await interaction.response.send_message(f"No profile found for {member.display_name}.", ephemeral=True)
        return

    club = format_club_info(db.get_club_info(club_id))
    if club:
        club_text = " - ".join([club["name"], club["league"], club["flag"]])
        
        # Get user tags
        tags = db.get_user_tags(member.id)
        tags_str = ', '.join(tags) if tags else 'No tags set'
        level = db.get_user_level(member.id)

        embed = embed_for_club(club)
        embed.title=f"{member.display_name} ({level})"
        embed.add_field(name="⚽ Home club", value=club_text , inline=False)
        embed.add_field(name="🏷️ Tags", value=tags_str, inline=False)
        # Expert clubs
        expert_names = db.get_expert_clubs(interaction.guild.id, member.id)
        expert_list = ', '.join(expert_names) if len(expert_names) > 0 else 'No experts known'
        embed.add_field(name="Expert for", value=expert_list, inline=False)
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
    db.save_user_tags(member.id, tag_list)
    
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
    existing_tags = db.get_user_tags(member.id)
    
    # Add tags
    db.add_user_tags(member.id, tag_list)
    
    # Get updated tags
    updated_tags = db.get_user_tags(member.id)
    
    await interaction.response.send_message(
        f"✅ Tags added successfully!\n\n"
        f"**Your tags:** {', '.join(updated_tags)}",
        ephemeral=True
    )

# Slash command: /club
@bot.tree.command(name="club", description="Show club information and all members", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(club="The club name to display")
@app_commands.autocomplete(country=country_autocomplete, club=club_autocomplete)
async def club_command(interaction: discord.Interaction, 
    country: str,
    club: str):
    """Shows club information and all members."""
    await interaction.response.defer()
    
    await show_club_info(interaction, club)

async def show_club_info(interaction: discord.Interaction, club: str):
    # Get club information
    info = format_club_info(db.get_club_info(db.get_club_id_by_name(club)))
    
    if not info:
        await interaction.followup.send(f"❌ Club '{club}' not found in database.", ephemeral=True)
        return
    
    print(f"Showing info for club '{info['name']}' (ID: {info['club_id']}) with color {info['color']} and logo {info['club_logo']}")
    # Get members of this club
    guild = interaction.guild
    members_data = db.get_members_by_club_id(guild.id, info['club_id'])
    member_ids = set(user_id for (user_id,) in members_data)

    # Build member list with levels
    member_mentions = []
    for (user_id,) in members_data:
        member = guild.get_member(user_id)
        if member:
            level = db.get_user_level(user_id)
            member_mentions.append(f"{member.mention} {level}")
    
    # Create embed
    embed = embed_for_club(info)
    embed.title = f"⚽ {info['name']}"
    embed.description = f"**League:** {info['league']} (Tier {info['tier']})\n**Country:** {info['country']} {info['flag']}"
    
    embed.add_field(
        name=f"Members ({len(member_mentions)})",
        value=", ".join(member_mentions) if member_mentions else "No members yet",
        inline=False
    )

    # Add experts (without medal emojis). Exclude users already listed as members.
    expert_user_ids = set(db.get_expert_users_for_club(guild.id, info['club_id'])) - member_ids
    expert_mentions = []
    for uid in expert_user_ids:
        m = guild.get_member(uid)
        if m:
            expert_mentions.append(m.mention)
    if len(expert_mentions) > 0:
        embed.add_field(
            name=f"Experts ({len(expert_mentions)})",
            value=", ".join(expert_mentions),
            inline=False
        )
    
    await interaction.followup.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

# Slash command: /set-clubicon
@bot.tree.command(name="set-clubicon", description="Set or update a club's logo (PNG recommended)", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    country="The country of the club",
    club="The club to update",
    logo_url="The URL to the club logo (direct image link, PNG recommended)"
)
@app_commands.autocomplete(country=country_autocomplete, club=club_autocomplete)
async def set_clubicon_command(
    interaction: discord.Interaction,
    country: str,
    club: str,
    logo_url: str
):
    """Set or update a club's logo URL.

    The command will update the `logo` column for the selected club and then
    display the club profile so you can verify the change.
    """
    await interaction.response.defer(ephemeral=True)

    # Validate club exists
    club_id = db.get_club_id_by_name(club)
    if not club_id:
        await interaction.followup.send(f"❌ Club '{club}' not found in the database.", ephemeral=True)
        return

    # Reject SVG files (not supported)
    if logo_url.strip().lower().endswith('.svg'):
        await interaction.followup.send("❌ .svg images are not supported. Please provide a PNG or JPG image URL.", ephemeral=True)
        return

    # Update the database
    try:
        db.update_club_logo(club_id, logo_url)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to update logo: {e}", ephemeral=True)
        return

    await show_club_info(interaction, club)

# Slash command: /set-clubcolor
@bot.tree.command(name="set-clubcolor", description="Set or update a club's color (hex format)", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    country="The country of the club",
    club="The club to update",
    color="The color in hex format (e.g. FF0000 for red, without #)"
)
@app_commands.autocomplete(country=country_autocomplete, club=club_autocomplete)
async def set_clubcolor_command(
    interaction: discord.Interaction,
    country: str,
    club: str,
    color: str
):
    """Set or update a club's color.

    The command will update the `color` column for the selected club and then
    display the club profile so you can verify the change.
    """
    await interaction.response.defer(ephemeral=True)

    # Validate club exists
    club_id = db.get_club_id_by_name(club)
    if not club_id:
        await interaction.followup.send(f"❌ Club '{club}' not found in the database.", ephemeral=True)
        return

    # Validate hex color format
    color = color.strip().lstrip('#').upper()
    if len(color) != 6 or not all(c in '0123456789ABCDEF' for c in color):
        await interaction.followup.send("❌ Invalid color format. Please provide a 6-digit hex color (e.g. FF0000 for red).", ephemeral=True)
        return

    # Update the database
    try:
        db.update_club_color(club_id, color)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to update color: {e}", ephemeral=True)
        return

    await show_club_info(interaction, club)

# Slash command: /add-expert-club
@bot.tree.command(name="add-expert-club", description="Mark a club as one you are an expert for (max 4)", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    country="The country your expert club is from",
    club="The club name"
)
@app_commands.autocomplete(country=country_autocomplete, club=club_autocomplete)
async def add_expert_club_command(interaction: discord.Interaction, country: str, club: str):
    await interaction.response.defer(ephemeral=True)

    member = interaction.user
    guild = interaction.guild

    club_id, _ = db.get_or_create_club(club)

    ok, reason = db.add_expert_club(guild.id, member.id, club_id)
    if not ok:
        if reason == 'already_exists':
            await interaction.followup.send(f"ℹ️ You already marked '{club}' as an expert club.", ephemeral=True)
            return
        if reason == 'limit_reached':
            await interaction.followup.send("❌ You can mark up to 4 expert clubs. Remove one first.", ephemeral=True)
            return
        if reason == 'home_club':
            await interaction.followup.send("❌ You are implicitly an expert for your home club and cannot add it as an expert club.", ephemeral=True)
            return
        await interaction.followup.send("❌ Could not add expert club.", ephemeral=True)
        return

    await interaction.followup.send(f"✅ Added '{club}' to your expert clubs.", ephemeral=True)

    # Update member list
    await post_member_list(interaction.guild)

# Slash command: /remove-expert-club
@bot.tree.command(name="remove-expert-club", description="Remove a club from your expert list", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    country="The country of the club",
    club="The club name to remove"
)
@app_commands.autocomplete(country=country_autocomplete, club=club_autocomplete)
async def remove_expert_club_command(interaction: discord.Interaction, country: str, club: str):
    await interaction.response.defer(ephemeral=True)

    member = interaction.user
    guild = interaction.guild

    club_id = db.get_club_id_by_name(club)
    if not club_id:
        await interaction.followup.send(f"❌ Club '{club}' not found.", ephemeral=True)
        return

    removed = db.remove_expert_club(guild.id, member.id, club_id)
    if removed:
        await interaction.followup.send(f"✅ Removed '{club}' from your expert clubs.", ephemeral=True)
    else:
        await interaction.followup.send(f"ℹ️ '{club}' was not in your expert clubs.", ephemeral=True)

    # Update member list
    await post_member_list(interaction.guild)

# Start the bot
bot.run(TOKEN)
