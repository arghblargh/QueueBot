QueueBot
========

Queue management bot for Twitch.tv chat

Set NICK, IDENT, and REALNAME to the Twitch.tv username of the bot.

PASS is the oauth token for the bot (generated from http://www.twitchapps.com/tmi/).

INIT_CHANNEL is #bot_name.

ADMIN is the Twitch.tv username of the designated bot admin.

Additional information at https://github.com/justintv/Twitch-API/blob/master/IRC.md

###Commands

######Debug Commands

!hello - Returns a message

!echo _msg_ - Echos _msg_

!users - Returns the bot's list of users

!data - Returns all data for the current channel

!quit - Kills bot

######Broadcaster Commands

!join - Tells the bot to join your chatroom

!remove - Removes the bot from your chatroom

!trust _user_ - Adds _user_ to your trusted list

!untrust _user_ - Removes _user_ from your trusted list

!queue on/off - Enables or Disables queue functions in your chatroom

######Queue Commands (Broadcaster/Trusted User)

!queue show - Shows the entire queue

!queue setsize _n_ - Sets the player group size to _n_

!queue new - Generates a new group from the queue

!queue remove _user_ - Removes _user_ from the queue. If _user_ is in the current group, removes _user_ from the group and adds another from the queue

!queue clear - Clears the queue and current group

######Queue Commands (Viewers)

!queue add - Add yourself to the end of the queue

!queue remove - Remove yourself from the queue or current group

!queue players - Lists the players in the current group

!queue size - Show current size of queue

!queue position - Check your position in the queue
