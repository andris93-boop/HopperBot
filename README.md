# Discord Groundhopping Bot

Manage a database of Leagues and Clubs and discord memebers

## Usage with systemd
```
# Copy service file to user systemd directory
mkdir -p ~/.config/systemd/user
cp hopper-bot.service ~/.config/systemd/user/

# Reload systemd user daemon
systemctl --user daemon-reload

# Enable service (automatic start on login)
systemctl --user enable hopper-bot.service

# Start service
systemctl --user start hopper-bot.service

# Check status
systemctl --user status hopper-bot.service

# View logs
journalctl --user -u hopper-bot.service -f
```
