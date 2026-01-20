# General functions


## Welcomming new members

when a new member arrives on a server the bot automatically assigns the role "newcomer" this role can only view the channel "Welcome". It sends a Welcome message and tells the user to use the "/set-club" function to select a club. when that is done the user is automatically given the Role "Fan"

## Writing the line-up

everytime the line-up changes the bot automatically rewrites the line-up Message. it mentions everyone with "@" but is not allowed to ping the users with that message. It also adds the Activity status (see: tracking Activity Status) in the Line-up Message. ATTENTION: The bot will rewrite the line-up message everytime something changes, because of the Club Icons as embed (so it is not dependent on the server limit), every club is an own message so it will be a lot of Messages. Please Mute the Channel line-up yourself as it cant be done from the Server side.

## Tracking Activity Status
everytime a user sends a message the bot counts it. The only data that is stored is: User_id; Date; number of entries. For giving out activity Statuses only the last two weeks are considered. Three different Statuses can be achieved:
"Inactive"; less than 1 message on two different days;
"Fan" at least 1 message on 2 different days;
"Ultra" at least 1 message on 5 different days;
The bot will start counting today so the earliest you can achieve the status "fan" is tomorrow and for "Ultra" it is in four days from now.

# Commands

## /set-club
This command allows you to set or change your club.
You will first be asked to select a country from a drop-down menu. If you cannot find your country, simply start typing to filter the list.
Next, you can select a club from another drop-down menu. Again, you can type to filter the list.
If your club does not exist yet, you can simply type in the club’s name and it will be added automatically.

## /update-league 
If you create a new club, the bot will inform you that the club is not assigned to a league yet and will ask you to run this command.
You will be asked to select:
a country (drop-down),
a club (drop-down),
the league name (drop-down),
and the league tier.
If you enter a league that does not exist yet, this command will also create the new league. Please make sure to check the drop-down menu first to avoid creating duplicate leagues.
This command is also useful when a team changes leagues due to promotion or relegation.

## /profile 
This command displays a user profile. It shows:
the user’s name,
activity status,
club (including icon),
tags,
and the total number of active days on the server
(days on which the user posted at least one message or reaction).
You can press Enter twice to view your own profile, or select member from the drop-down menu to view another member’s profile.

## /club
this function will show the club and give following informations:
- name of the club
- display Logo
- name of the League
- Country
- Members (with activity status)

## /set-clubicon
This command allows you to set or update a club's logo by providing a direct image URL.
- Select the country (drop-down) and the club (drop-down).
- Paste the direct image link (PNG recommended) into the `logo_url` field.

Note: SVG images are not supported and will be rejected. After a successful update the bot will display the club profile so you can verify the logo.

## /set-clubcolor
This command allows to set a club's embed color so the club's messages and embeds use a custom color.
- Select the country (drop-down) and the club (drop-down).
- Provide a hex color value in the form `#RRGGBB` (e.g. `#FF4500`).

## /add-tags and /tags
These commands allow you to manage tags on your profile.
"/tags" deletes all your current tags and replaces them with the newly entered ones.
"/add-tags" adds new tags to your existing ones.
For now, tags can be simple things like “scarf enjoyer”, “beer”, or anything you like.
We plan to use tags in future features, but for now this is their only function.

## !ping 
This command allows you to ping the bot to check if it is online.
If the bot is running, it will respond.

# Disclaimer

By using this bot, you agree that data may be stored on our server located in Germany. This data will not be shared with third parties, sold, or used for any purpose other than operating and improving the functionality of this bot.

The source code of this bot is publicly available on GitHub for transparency. (https://github.com/andris93-boop/HopperBot)

If you have ideas for future features, wish to report bugs, or would like to provide any other feedback, feel free to contact me at any time.
