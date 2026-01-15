#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import requests
from urllib.parse import quote

# Basis-URL für die Logos
LOGO_URL = "https://cdn.prod.website-files.com/68f550992570ca0322737dc2/"

def fetch_logo_for_club(club_name):
    """
    Fragt die Logo-URL für einen Club ab.
    """
    print(f'\nClub: {club_name}')
    logo_url = input('Bitte Logo-URL eingeben (oder Enter zum Überspringen): ').strip()

    if not logo_url:
        return None

    return logo_url

def update_club_logos():
    """Aktualisiert die Logo-URLs für alle Clubs ohne Logo."""
    conn = sqlite3.connect('hopper_bot.db')
    cursor = conn.cursor()

    # Alle Clubs ohne Logo abrufen
    cursor.execute('SELECT id, name FROM clubs WHERE logo IS NULL OR logo = ""')
    clubs = cursor.fetchall()

    print(f'Gefunden: {len(clubs)} Clubs ohne Logo')

    for club_id, club_name in clubs:
        try:
            # Logo-URL für den Club abfragen
            logo_url = fetch_logo_for_club(club_name)

            if not logo_url:
                print('  → Übersprungen\n')
                continue

            # Prüfen, ob die URL mit LOGO_URL beginnt
            if logo_url.startswith(LOGO_URL):
                # Basis-URL abschneiden und nur den Rest speichern
                logo_suffix = logo_url[len(LOGO_URL):]

                # In Datenbank eintragen
                cursor.execute('UPDATE clubs SET logo = ? WHERE id = ?', (logo_suffix, club_id))
                print(f'  ✓ Logo gespeichert: {logo_suffix}\n')
            else:
                print(f'  ✗ URL beginnt nicht mit der erwarteten Basis-URL {LOGO_URL}\n')

        except Exception as e:
            print(f'  ✗ Fehler bei {club_name}: {e}\n')

    conn.commit()
    conn.close()
    print('Fertig!')

if __name__ == '__main__':
    update_club_logos()
