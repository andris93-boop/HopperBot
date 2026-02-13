# General functions

## Welcoming new members

When a new member arrives on a server, the bot automatically assigns the role "newcomer". This role can only view the channel "Welcome". It sends a welcome message and asks the user to use the "/set-club" command to select a club.

## Writing the line-up

Every time the line-up changes, the bot automatically rewrites the line-up message. It mentions everyone with "@" but does not ping users with that message. It also adds the activity status (see: [Tracking Activity Status](#tracking-activity-status)) in the line-up message.

ATTENTION: The bot will rewrite the line-up message every time something changes. Because of the club icons being added as embeds (so it is not dependent on the server message limit), every club gets its own message, which can result in many messages. Please mute the "line-up" channel yourself, as this cannot be done from the server side.

Clubs that appear only because at least one user marked them as an expert (no regular members) will still be shown in the lineup and will display their club logo if available. The bot appends a medal emoji after a user's mention to indicate their relation to the club: gold (🥇) for home club members, silver (🥈) for experts.

## Social media link fixer

If a message contains supported social media links with poor embeds, the bot automatically rewrites these links to embed-friendly versions and reposts the message.

The repost keeps the relevant context:
- it includes a "Posted by @user" hint,
- it keeps the original message text,
- and it keeps attachment links.

After reposting, the bot removes the original message (if it has permission), so the channel does not contain duplicate unfixed/fixed links.

## Tracking Activity Status

Every time a user sends a message, the bot counts it. The only data that is stored is: user ID, date, and number of entries. For assigning activity statuses, only the last two weeks are considered. Three different statuses can be achieved:

- **Casual:** messages on fewer than 2 different days
- **Fan:** at least 1 message on 2 different days
- **Ultra:** at least 1 message on 5 different days

The bot will automatically assign roles accordingly.

# Commands

## /set-club
This command allows you to set or change your club.
You will first be asked to select a country from a drop-down menu. If you cannot find your country, simply start typing to filter the list.
Next, you can select a club from another drop-down menu. Again, you can type to filter the list.
If your club is not in our database yet, you can simply type the club’s name and it will be added automatically.

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
- Experts for the club,
- Apprentice members,
- Ticketing information (if available),
- Stadium information (if available),
- Stadium plan details (if available).

## /add-stadiuminfo
This command allows you to add or update stadium information for a club.
Because Discord modals are limited to 5 fields, the input is split into two modals:

1) Stadium basics
- Stadium name,
- Stadium image URL,
- Capacity,
- Built year.

2) Stadium plan details
- Stadium plan image URL,
- Block description,
- How to get there.

Rules:
- Empty fields do not overwrite existing values.
- New values for previously empty fields are applied directly (no confirmation needed).
- If you change a field that already has a value, the bot opens a per-field review and asks if you want to **Confirm** (apply new value) or **Discard** (keep old value).
- Stadiums are stored separately and can be shared by multiple clubs.

## /set-clubicon
This command allows you to set or update a club's logo by providing a direct image URL.
- Select the country (drop-down) and the club (drop-down).
- Paste the direct image link (PNG recommended) into the `logo_url` field.

Note: SVG images are not supported and will be rejected. After a successful update the bot will display the club profile so you can verify the logo.

## /set-clubcolor
This command allows to set a club's embed color so the club's messages and embeds use a custom color.
- Select the country (drop-down) and the club (drop-down).
- Provide a hex color value in the form `#RRGGBB` (e.g. `#FF4500`).

## Expert clubs (/add-expert-club, /remove-expert-club)
These commands let users mark clubs they are an expert for (up to 10 clubs per user).
- `/add-expert-club`: Select a country and a club to mark it as one you are an expert for.
- `/remove-expert-club`: Remove a previously added expert club.

Notes:
- Expert clubs are limited to 10 entries per user. Expert clubs and expert users are already visible in user profiles, the server-wide lineup, and in the `/club` view under the "Experts" field.

## /add-tags and /tags
These commands allow you to manage tags on your profile.
`/tags` deletes all your current tags and replaces them with the newly entered ones.
`/add-tags` adds new tags to your existing ones.
For now, tags can be simple things like “scarf enjoyer”, “beer”, or anything you like.
We plan to use tags in future features, but for now this is their only function.

## !ping
This command allows you to ping the bot to check if it is online.
If the bot is running, it will respond.

## "$Club" 
with this funktion you are able to trigger a message that pings the users that are members of the according club. You can ping as much clubs as you want, but it is limited to send out a maximum of 10 pings. up to two pings works insant. if it are 3 or more, the bot will send a dm that you have to confirm, it shows how many people and who exactl you are about to ping 

# Disclaimer

By using this bot, you agree that data may be stored on our server located in Germany. This data will not be shared with third parties, sold, or used for any purpose other than operating and improving the functionality of this bot.

The source code of this bot is publicly available on GitHub for transparency: [HopperBot on Github](https://github.com/andris93-boop/HopperBot)

If you have ideas for future features, wish to report bugs, or would like to provide any other feedback, feel free to contact me at any time.
