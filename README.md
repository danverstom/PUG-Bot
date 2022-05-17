# About

Winston is a discord bot created for the Brawl Capture the Flag PUG discord server. Offers tools for event creation, brawl related utilities & many more!

## What are PUGs?

PUG stands for "Pick Up Game". The purpose of the CTF PUG server is to provide players with a way to play high level competitive games and keep track of their progress.

## Features

*   MCCTF event related commands (coinflip, rngmap, maps etc)
*   ELO tracking system (leaderboard, etc)
*   User registration system (links discord with minecraft IGN & keeps it updated)
*   User management features for admins
*   Stats-related commands - playerstats (individual stats) and game stats following matches
*   Spreadsheet viewer - view upcoming matches and their times, on the match server spreadsheet
*   Roster Count tracker - sends notifications when teams are made or change in size
*   Event system - designed to be semi-automated & signups are stored, can be easily accessed
*   Priority system & RNG - gives players equal opportunity to play in games
*   Postpone events
*   Role management commands (setroles, removeroles, etc)
*   Rotation map search - allows you to quickly search for maps and get IDs without hassle
*   [Slash commands](https://github.com/eunwoo1104/discord-py-slash-command) - commands which are user-friendly & easy to use
*   Multiplayer discord minigames
*   Web interface

## Collaborators

Many thanks to the following people who have helped out!

*   [Ninsanity](https://github.com/ningeek212)
*   [redboo123](https://github.com/Partition)
*   [mikye](https://github.com/mikeo)

## Running PUG Bot yourself

Installation instructions ([view the project on GitHub here](https://github.com/TomD53/PUG-Bot))

`git clone https://github.com/TomD53/PUG-Bot`  
`pip install -r requirements.txt`  
`cd webserver/static/bulma-css`  

`npm install` (make sure you have [node.js](https://nodejs.org/en/) installed)

In order to update the app theme using sass variables, edit `webserver/static/bulma-css/sass/main.scss` and run `npm start`

Create a new file `utils/app_credentials.json` and fill in the details of [your app](https://discord.com/developers/applications).

Set the callback to `http://localhost:8080/callback`

<pre>{
  "bot_token": "",
  "oauth2_client_id": 12345,
  "oauth2_client_secret": "",
  "oauth2_callback": ""
}</pre>

In order to start the application, run `python init.py`

To use the spreadsheet commands, [get a service account](https://cloud.google.com/iam/docs/creating-managing-service-accounts)
Download the json generated, and place it in `utils/` named as service_account.json 

## Support/Donate

Winston costs money to host every month, and time to develop.

Support the project [here](https://ko-fi.com/tomd53)