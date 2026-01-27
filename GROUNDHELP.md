Groundhelp (Club mentions) — Testing

- Send a message like `$Arminia` in the configured Groundhelp channel.
- The bot will lookup the club and mention up to 10 members (configurable via `MAX_MENTIONS` in `hopper.py`).
- If no members are found the bot replies `Keine Mitglieder mit dem gesuchten Verein gefunden.`
- To enable automatic thread creation for follow-up discussion, set `CREATE_THREAD_ON_PING = True` in `hopper.py` (bot needs thread permissions).
- Logs about lookups and sends are printed to the bot stdout for debugging.
