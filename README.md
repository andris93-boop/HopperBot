# Discord Groundhopping Bot

Manage a database of Leagues and Clubs and discord memebers

## Usage with systemd

The bot uses a systemd template service that allows running multiple instances.

```bash
# Copy template to user systemd directory
mkdir -p ~/.config/systemd/user
cp hopper-bot@.service ~/.config/systemd/user/

# Reload systemd user daemon
systemctl --user daemon-reload

# Start with instance name (e.g., hopper-bot-productive)
# The instance name becomes the directory name under ~/ where the bot files are located
systemctl --user start hopper-bot@hopper-bot-productive.service
systemctl --user enable hopper-bot@hopper-bot-productive.service

# For testing environment
systemctl --user start hopper-bot@hopper-bot.service
systemctl --user enable hopper-bot@hopper-bot.service

# Check status
systemctl --user status hopper-bot@hopper-bot-productive.service

# View logs
journalctl --user -u hopper-bot@hopper-bot-productive.service -f

# Stop service
systemctl --user stop hopper-bot@hopper-bot-productive.service

# Enable lingering (bot runs even when not logged in)
sudo loginctl enable-linger $USER
```
