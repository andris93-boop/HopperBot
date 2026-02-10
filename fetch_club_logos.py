#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import requests
from urllib.parse import quote

# Base URL for logos
LOGO_URL = "https://cdn.prod.website-files.com/68f550992570ca0322737dc2/"

def fetch_logo_for_club(club_name):
    """
    Asks for the logo URL for a club.
    """
    print(f'\nClub: {club_name}')
    logo_url = input('Please enter logo URL (or press Enter to skip): ').strip()

    if not logo_url:
        return None

    return logo_url

def update_club_logos():
    """Updates logo URLs for all clubs without a logo."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()

    # Alle Clubs ohne Logo abrufen
    cursor.execute('SELECT id, name FROM clubs WHERE logo IS NULL OR logo = ""')
    clubs = cursor.fetchall()

    print(f'Found: {len(clubs)} clubs without a logo')

    for club_id, club_name in clubs:
        try:
            # Logo-URL für den Club abfragen
            logo_url = fetch_logo_for_club(club_name)

            if not logo_url:
                print('  → Skipped\n')
                continue

            # Prüfen, ob die URL mit LOGO_URL beginnt
            if logo_url.startswith(LOGO_URL):
                # Basis-URL abschneiden und nur den Rest speichern
                logo_suffix = logo_url[len(LOGO_URL):]

                # In Datenbank eintragen
                cursor.execute('UPDATE clubs SET logo = ? WHERE id = ?', (logo_suffix, club_id))
                print(f'  ✓ Logo saved: {logo_suffix}\n')
            else:
                print(f'  ✗ URL does not start with expected base URL {LOGO_URL}\n')

        except Exception as e:
            print(f'  ✗ Error for {club_name}: {e}\n')

    conn.commit()
    conn.close()
    print('Done!')

if __name__ == '__main__':
    update_club_logos()
