#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
from datetime import date, timedelta
from unidecode import unidecode

class HopperDatabase:
    """Database handler for the Hopper Bot."""

    def __init__(self, database_name):
        """Initialize the database connection.

        Args:
            database_name: Path to the SQLite database file
        """
        self.database_name = database_name
        self.init_database()

    def init_database(self):
        """Creates the SQLite database and tables for user profiles and clubs."""
        conn = sqlite3.connect(self.database_name)
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
                color TEXT,
                ticket_notes TEXT,
                ticket_url TEXT,
                FOREIGN KEY (league_id) REFERENCES leagues(id)
            )
        ''')

        # Add color column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(clubs)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'color' not in columns:
            cursor.execute('ALTER TABLE clubs ADD COLUMN color TEXT')
        # Add ticketing columns if missing
        if 'ticket_notes' not in columns:
            cursor.execute('ALTER TABLE clubs ADD COLUMN ticket_notes TEXT')
        if 'ticket_url' not in columns:
            cursor.execute('ALTER TABLE clubs ADD COLUMN ticket_url TEXT')

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

        # Table for expert clubs (users can mark up to 4 clubs as 'expert for')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expert_clubs (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, guild_id, club_id),
                FOREIGN KEY (club_id) REFERENCES clubs(id)
            )
        ''')

        conn.commit()
        conn.close()
        print('Database initialized.')

    def get_or_create_league(self, name, country, tier=99):
        """Finds a league or creates it if it doesn't exist yet."""
        conn = sqlite3.connect(self.database_name)
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

    def get_or_create_club(self, name):
        """Finds a club or creates it if it doesn't exist yet."""
        conn = sqlite3.connect(self.database_name)
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

    def save_user_profile(self, guild_id, user_id, club_id):
        """Saves the user profile to the database."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles
            (user_id, guild_id, club_id)
            VALUES (?, ?, ?)
        ''', (user_id, guild_id, club_id))

        conn.commit()
        conn.close()

    def get_user_profile(self, guild_id, user_id):
        """Loads the user profile from the database."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT club_id, created_at FROM user_profiles
            WHERE user_id = ? AND guild_id = ?
        ''', (user_id, guild_id))

        result = cursor.fetchone()
        conn.close()
        if not result:
            return None, None
        return result[0], result[1]

    def get_leagues_by_country(self, country):
        """Fetches all leagues from a country from the database."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('SELECT name FROM leagues WHERE country = ? ORDER BY tier', (country,))
        results = [row[0] for row in cursor.fetchall()]

        conn.close()
        return results

    def get_clubs_by_country_and_league(self, country, league):
        """Fetches all clubs from a country and league from the database."""
        conn = sqlite3.connect(self.database_name)
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

    def get_clubs_by_country(self, country):
        """Fetches all clubs from a country from the database."""
        conn = sqlite3.connect(self.database_name)
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

    def get_all_countries(self):
        """Fetches all countries from the database."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT country FROM leagues ORDER BY country')
        results = [row[0] for row in cursor.fetchall()]

        conn.close()
        return results

    def get_club_id_by_name(self, club_name):
        """Fetches the club ID by club name."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM clubs WHERE name = ?', (club_name,))
        result = cursor.fetchone()

        conn.close()
        return result[0] if result else None

    def search_clubs_by_name_like(self, query, limit=50):
        """Search clubs by name using case-insensitive LIKE. Returns list of (id, name).

        Args:
            query: substring to search for
            limit: maximum number of results to return
        """
        conn = sqlite3.connect(self.database_name)
        conn.create_function("unidecode", 1, unidecode)

        cursor = conn.cursor()

        pattern = f"%{query}%"
        cursor.execute('SELECT id, name FROM clubs WHERE unidecode(LOWER(name)) LIKE unidecode(LOWER(?)) LIMIT ?', (pattern, limit))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_club_info(self, club_id):
        """Fetches club information including league and country.

        Args:
            club_id: The club ID to fetch

        Returns:
            Tuple: (name, league_name, country, logo, tier, flag, id, color, league_logo, ticket_notes, ticket_url) or None
        """
        if not club_id:
            return None
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT c.name, l.name, l.country, c.logo, l.tier, l.flag, c.id, c.color, l.logo, c.ticket_notes, c.ticket_url
            FROM clubs c
            LEFT JOIN leagues l ON c.league_id = l.id
            WHERE c.id = ?
        ''', (club_id,))

        result = cursor.fetchone()
        conn.close()
        return result

    def get_members_by_club_id(self, guild_id, club_id):
        """Fetches all members of a specific club in a guild."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_id
            FROM user_profiles
            WHERE guild_id = ? AND club_id = ?
            ORDER BY created_at
        ''', (guild_id, club_id))

        results = cursor.fetchall()
        conn.close()
        return results

    def update_club_league(self, club_id, league_id):
        """Updates the league_id of a club."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('UPDATE clubs SET league_id = ? WHERE id = ?', (league_id, club_id))
        conn.commit()
        conn.close()

    def update_club_logo(self, club_id, logo_url):
        """Updates the logo URL of a club."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('UPDATE clubs SET logo = ? WHERE id = ?', (logo_url, club_id))
        conn.commit()
        conn.close()

    def update_club_color(self, club_id, color):
        """Updates the color of a club."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('UPDATE clubs SET color = ? WHERE id = ?', (color, club_id))
        conn.commit()
        conn.close()

    def update_club_ticket_info(self, club_id, ticket_notes, ticket_url):
        """Updates ticketing information for a club.

        Args:
            club_id: ID of the club to update
            ticket_notes: Short free-text notes about ticket purchase
            ticket_url: URL to the official ticketing website
        """
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('UPDATE clubs SET ticket_notes = ?, ticket_url = ? WHERE id = ?', (ticket_notes, ticket_url, club_id))
        conn.commit()
        conn.close()

    def update_league_tier(self, league_id, tier):
        """Updates the tier of a league."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('UPDATE leagues SET tier = ? WHERE id = ?', (tier, league_id))
        conn.commit()
        conn.close()

    def get_user_tags(self, user_id):
        """Fetches all tags for a user."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('SELECT tag FROM tags WHERE user_id = ? ORDER BY created_at', (user_id,))
        results = [row[0] for row in cursor.fetchall()]

        conn.close()
        return results

    def save_user_tags(self, user_id, tags):
        """Saves tags for a user. Replaces existing tags."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        # Delete existing tags
        cursor.execute('DELETE FROM tags WHERE user_id = ?', (user_id,))

        # Insert new tags
        for tag in tags:
            if tag.strip():  # Only save non-empty tags
                cursor.execute('INSERT INTO tags (user_id, tag) VALUES (?, ?)', (user_id, tag.strip()))

        conn.commit()
        conn.close()

    def add_user_tags(self, user_id, tags):
        """Adds tags to a user's existing tags."""
        conn = sqlite3.connect(self.database_name)
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

    def get_all_tags(self):
        """Fetches all unique tags from all users."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT tag FROM tags ORDER BY tag')
        results = [row[0] for row in cursor.fetchall()]

        conn.close()
        return results

    def increment_activity(self, user_id):
        """Increments the activity counter for a user for today."""
        conn = sqlite3.connect(self.database_name)
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

    def get_user_level(self, user_id):
        """Calculates user level based on activity in the last 2 weeks."""
        conn = sqlite3.connect(self.database_name)
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

    def get_club_ids_sorted_by_country_and_tier(self):
        """Returns a list of club IDs sorted by country and league tier."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.id FROM clubs AS c
            LEFT JOIN leagues AS l
            ON c.league_id = l.id
            WHERE l.country IS NOT NULL
            ORDER BY l.country, l.tier
        ''')
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def get_user_activity_days(self, user_id):
        """Returns the total number of distinct active days for a user."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT date) FROM activity WHERE user_id = ?', (user_id,))
        active_days = cursor.fetchone()[0]
        conn.close()
        return active_days

    def add_expert_club(self, guild_id, user_id, club_id):
        """Adds an expert club for a user. Returns (True, None) on success, (False, reason) on failure."""

        home_club, _ = self.get_user_profile(guild_id, user_id)
        if home_club == club_id:
            return False, 'home_club'

        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        # Check if already exists
        cursor.execute('SELECT 1 FROM expert_clubs WHERE guild_id = ? AND user_id = ? AND club_id = ?', (guild_id, user_id, club_id))
        if cursor.fetchone():
            conn.close()
            return False, 'already_exists'

        # Check limit
        cursor.execute('SELECT COUNT(*) FROM expert_clubs WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
        count = cursor.fetchone()[0]
        if count >= 4:
            conn.close()
            return False, 'limit_reached'

        # Insert
        cursor.execute('INSERT INTO expert_clubs (user_id, guild_id, club_id) VALUES (?, ?, ?)', (user_id, guild_id, club_id))
        conn.commit()
        conn.close()
        return True, None

    def remove_expert_club(self, guild_id, user_id, club_id):
        """Removes an expert club for a user. Returns True if removed, False otherwise."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM expert_clubs WHERE guild_id = ? AND user_id = ? AND club_id = ?', (guild_id, user_id, club_id))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted > 0

    def get_expert_users_for_club(self, guild_id, club_id):
        """Returns a list of user_ids who are experts for the given club in the guild."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('SELECT user_id FROM expert_clubs WHERE guild_id = ? AND club_id = ?', (guild_id, club_id))
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def get_expert_clubs(self, guild_id, user_id):
        """Returns a list of club_ids the user is marked as expert for in the guild."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT c.name FROM expert_clubs e
            LEFT JOIN clubs c ON e.club_id = c.id
            WHERE e.guild_id = ? AND e.user_id = ?''', (guild_id, user_id))
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def get_all_expert_clubs(self, guild_id):
        """Returns a list of user_ids and club_ids the user is marked as expert for in the guild."""
        conn = sqlite3.connect(self.database_name)
        cursor = conn.cursor()

        cursor.execute('SELECT user_id, club_id FROM expert_clubs WHERE guild_id = ?', (guild_id,))
        results = cursor.fetchall()
        conn.close()
        return results

