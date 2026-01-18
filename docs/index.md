# General functions

## Welcoming new members

When a new member arrives on a server, the bot automatically assigns the role "newcomer". This role can only view the channel "Welcome". It sends a welcome message and asks the user to use the "/set-club" command to select a club. When that is done, the user is automatically given the role "Fan".

## Writing the line-up

Every time the line-up changes, the bot automatically rewrites the line-up message. It mentions everyone with "@" but does not ping users with that message. It also adds the activity status (see: Tracking Activity Status) in the line-up message.

ATTENTION: The bot will rewrite the line-up message every time something changes. Because of the club icons being added as embeds (so it is not dependent on the server message limit), every club gets its own message, which can result in many messages. Please mute the "line-up" channel yourself, as this cannot be done from the server side.

## Tracking Activity Status

Every time a user sends a message, the bot counts it. The only data that is stored is: user ID, date, and number of entries. For assigning activity statuses, only the last two weeks are considered. Three different statuses can be achieved:

- **Inactive:** messages on fewer than 2 different days
- **Fan:** at least 1 message on 2 different days
- **Ultra:** at least 1 message on 5 different days

The bot starts counting today, so the earliest you can achieve the "Fan" status is tomorrow; the "Ultra" status can be achieved earliest in four days.

# Commands

## /set-club
This command allows you to set or change your club.
You will first be asked to select a country from a drop-down menu. If you cannot find your country, simply start typing to filter the list.
Next, you can select a club from another drop-down menu. Again, you can type to filter the list.
If your club does not exist yet, you can simply type the club’s name and it will be added automatically.

## /update-league
If you create a new club, the bot will inform you that the club is not yet assigned to a league and will ask you to run this command.
You will be asked to select:
- a country (drop-down),
- a club (drop-down),
- the league name (drop-down),
- and the league tier.

If you enter a league that does not exist yet, this command will also create the new league. Please make sure to check the drop-down menu first to avoid creating duplicate leagues.
This command is also useful when a team changes leagues due to promotion or relegation.

## /profile
This command displays a user profile. It shows:
- the user’s name,
- activity status,
- club (including icon),
- tags,
- and the total number of active days on the server (days on which the user posted at least one message or reaction).

You can press Enter twice to view your own profile, or press Space and enter a member's name (drop-down) to view another member’s profile.

## /club
This command shows the club and provides the following information:
- name of the club,
- display logo,
- name of the league,
- country,
- members (with activity status).

## /add-tags and /tags
These commands allow you to manage tags on your profile.
`/tags` deletes all your current tags and replaces them with the newly entered ones.
`/add-tags` adds new tags to your existing ones.
For now, tags can be simple things like “scarf enjoyer”, “beer”, or anything you like.
We plan to use tags in future features, but for now this is their only function.

## !ping
This command allows you to ping the bot to check if it is online.
If the bot is running, it will respond.

# Disclaimer

By using this bot, you agree that data may be stored on our server located in Germany. This data will not be shared with third parties, sold, or used for any purpose other than operating and improving the functionality of this bot.

The source code of this bot is publicly available on GitHub for transparency: [HopperBot on Github](https://github.com/andris93-boop/HopperBot)

If you have ideas for future features, wish to report bugs, or would like to provide any other feedback, feel free to contact me at any time.