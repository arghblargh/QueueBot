import socket, signal, datetime
import xml.etree.ElementTree as ET

HOST="irc.twitch.tv"
PORT=6667
NICK=""
PASS=""
IDENT=""
REALNAME=""
INIT_CHANNEL="#"
ADMIN=""
SAVE_FILE='data.xml'
MIN_DELAY=datetime.timedelta(0,2,500000) # 2.5 second delay between sent messages

# channel_info = {channel : Info()}
channel_info = dict()
time_last_sent = datetime.datetime.now()

class Info():

	users = set()
	queue = []
	players = set()

	def __init__(self, trusted = set(), size = 1, toggle = True, connect = True):
		self.trusted = trusted
		self.size = size
		self.toggle = toggle
		self.connect = connect

	def __str__(self):
		return 'Trusted: ' + str(self.trusted) + ' | Size: ' + str(self.size) + ' | Toggle: ' + str(self.toggle) + ' | Connect: ' + str(self.connect)

	def join(self):
		self.connect = True

	def part(self):
		self.users.clear()
		self.queue_clear()
		self.connect = False

	def is_trusted(self, user):
		return user in self.trusted

	def trust(self, user, flag):
		if flag:
			self.trusted.add(user)
		elif user in self.trusted:
			self.trusted.remove(user)

	def new_group(self):
		# Add old group back into queue if still in room
		for name in self.players:
			if name in self.users and name not in self.queue:
				self.queue.append(name)

		self.players.clear()

		temp = 0
		while len(self.queue) > 0 and temp < self.size:
			self.players.add(self.queue.pop(0))
			temp += 1

	def add(self, user):
		self.users.add(user)

	def remove(self, user):
		if user in self.users:
			self.users.remove(user)
		self.queue_remove(user)

	def queue_add(self, user):
		if user not in self.queue and user not in self.players:
			self.queue.append(user)
			return True
		else:
			return False

	def queue_remove(self, user):
		if user in self.queue:
			self.queue.remove(user)
			return 'Q'

		if user in self.players:
			self.players.remove(user)
			if len(self.queue) > 0:
				new_player = self.queue.pop(0)
				self.players.add(new_player)
				return 'R' + new_player
			else:
				return 'D'
				
		return 'N'

	def queue_size(self):
		return len(self.queue)

	def queue_position(self, user):
		return self.queue.index(user) + 1 if user in self.queue else -1

	def queue_clear(self):
		self.queue.clear()
		self.players.clear()

def connect():
	global s
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((HOST, PORT))
	s.send(("PASS %s\r\n" % PASS).encode())
	s.send(("NICK %s\r\n" % NICK).encode())
	s.send(("USER %s %s bla :%s\r\n" % (IDENT, HOST, REALNAME)).encode())

	for channel in channel_info:
		if channel_info[channel].connect:
			join(channel)

def join(channel):
	if channel not in channel_info:
		channel_info[channel] = Info()
	else:
		channel_info[channel].join()
	s.send(("JOIN %s\r\n" % channel).encode())

def part(channel):
	s.send(("PART %s\r\n" % channel).encode())

	try:
		channel_info[channel].part()
		save_data()
	except KeyError:
		print("   > part: No channel_info for %s" % channel)

# Save channel_info to an XML file
# TODO clear data from old channels
def save_data():
	tree = ET.ElementTree(ET.Element('data'))
	root = tree.getroot()

	for channel in channel_info:
		chan = ET.SubElement(root, 'channel', {'name' : channel})
		ET.SubElement(chan, 'size').text = str(channel_info[channel].size)
		ET.SubElement(chan, 'toggle').text = '1' if channel_info[channel].toggle else '0'
		ET.SubElement(chan, 'connect').text = '1' if channel_info[channel].connect else '0'

		for name in channel_info[channel].trusted:
			ET.SubElement(chan, 'trusted', {'name':name})

	tree.write(SAVE_FILE)
	print("   > Data saved to %s" % SAVE_FILE)

# Load channel_info from an XML file
def load_data():
	try:
		tree = ET.ElementTree(None, SAVE_FILE)

		root = tree.getroot()
		for channel in root.findall('channel'):
			channel_name = channel.get('name')
			
			trust = set()
			for trusted in channel.findall('trusted'):
				trust.add(trusted.get('name'))

			size = int(channel.find('size').text)
			toggle = True if int(channel.find('toggle').text) == 1 else False
			connect = True if int(channel.find('connect').text) == 1 else False

			channel_info[channel_name] = Info(trust, size, toggle, connect)
			print("   > Data loaded from %s" % SAVE_FILE)
	except (OSError, IOError) as e:
		print("   > %s not found. Creating new %s" % (SAVE_FILE, SAVE_FILE))
		save_data()

def list_to_str(list):
	return ', '.join(list)

def parse_msg(msg):
	user = msg[0].split('!')[0][1:].strip()
	channel = msg[2].strip()
	content = ' '.join(msg[3:])[1:].strip()
	return user, channel, content

def admin_auth(user):
	return user==ADMIN

def broadcaster_auth(channel, user):
	return user==channel[1:]

def trusted_auth(channel, user):
	return channel_info[channel].is_trusted(user)

# Due to the delay, some messages may be dropped
def send_msg(channel, msg):
	global time_last_sent
	time_delta = datetime.datetime.now() - time_last_sent
	if time_delta > MIN_DELAY:
		print("   > send: %s" % msg)
		s.send(("PRIVMSG %s :%s\r\n" % (channel, msg)).encode())
		time_last_sent = datetime.datetime.now()
	else:
		print("   > MIN_DELAY: %s" % msg)

def main():
	load_data()
	connect()
	join(INIT_CHANNEL)
	readbuffer = ""

	while True:
		# Receive data from IRC and spitting it into lines.
		readbuffer += s.recv(1024).decode()

		if len(readbuffer) == 0:
			print("   > Disconnected! Attempting to reconnect...")
			connect()

		temp = readbuffer.split("\n")
		readbuffer = temp.pop()

		for line in temp:
			print(line)
			message = line.split(" ")
		
			if (message[1]=='353'):
				temp = message[5:]
				temp[0] = temp[0][1:].strip()
			
				for name in temp:
					user = name.strip()
					try:
						channel_info[message[4]].add(user)
					except KeyError:
						print("   > 353: No channel_info for %s" % channel)

			elif (message[1]=='JOIN'):
				user, channel, content = parse_msg(message)

				try:
					channel_info[channel].add(user)
				except KeyError:
					print("   > JOIN: No channel_info for %s" % channel)

			elif (message[1]=='PART'):
				user, channel, content = parse_msg(message)

				try:
					channel_info[channel].remove(user)
				except KeyError:
					print("   > PART: No channel_info for %s" % channel)

			elif (message[1]=='PRIVMSG'):
				user, channel, content = parse_msg(message)

				try:
					channel_info[channel].add(user)
				except KeyError:
					print("   > PRIVMSG: No channel_info for %s" % channel)

				# Checks if the first character is a !, for commands.
				if (content[0]=='!'):
					split_content = content.split(' ')
					command = split_content[0]
					arg = split_content[1] if len(split_content) > 1 else None

					# Checks what command was queried.

					# BEGIN Debug commands

					if (command=='!hello' and admin_auth(user)):
						send_msg(channel, "Kappa /")

					elif (command=='!echo' and admin_auth(user)):
						send_msg(channel, content[6:])

					elif (command=='!users' and admin_auth(user)):
						send_msg(channel, "Users: %s" % list_to_str(channel_info[channel].users))

					elif (command=='!data' and admin_auth(user)):
						send_msg(channel, "DEBUG: %s" % channel_info[channel])

					elif (command=='!quit' and admin_auth(user)):
						send_msg(INIT_CHANNEL, "ResidentSleeper /")
						s.send(('QUIT\r\n').encode())
						s.shutdown(socket.SHUT_RDWR)
						print("disconnected")

					# END Debug commands

					elif (command=='!trust' and (admin_auth(user) or broadcaster_auth(channel, user))):
						if (arg != None):
							channel_info[channel].trust(arg, True)
							send_msg(channel, "%s is now a trusted user" % arg)
							save_data()

					elif (command=='!untrust' and (admin_auth(user) or broadcaster_auth(channel, user))):
						if (arg != None):
							channel_info[channel].trust(arg, False)
							send_msg(channel, "%s is no longer a trusted user" % arg)
							save_data()

					elif (command=='!join' and channel == INIT_CHANNEL):
						if arg == None:
							send_msg(channel, "Joining channel: %s" % user)
							join('#'+user)
						elif admin_auth(user):
							send_msg(channel, "Joining channel: %s" % arg)
							join('#'+arg)

					elif (command=='!remove'):
						if channel == INIT_CHANNEL:
							send_msg(channel, "Leaving: %s" % user)
							part('#'+user)
						elif admin_auth(user) or broadcaster_auth(channel, user):
							send_msg(channel, "Leaving channel ResidentSleeper /")
							part(channel)

					#BEGIN queue commands

					# !queue command arg
					# Commands: !queue size/players/add/remove/position/setsize/new
					# TODO? add at index, shuffle, autoreplace options
					elif (command=='!queue'):
						queue_command = arg
						queue_arg = split_content[2] if len(split_content) > 2 else None

						if (queue_command=='on' and (admin_auth(user) or broadcaster_auth(channel, user) or trusted_auth(channel, user))):
							try:
								channel_info[channel].toggle = True
								send_msg(channel, "Queue enabled")
								save_data()
							except KeyError:
								print("   > !queue on: No channel_info for %s" % channel)

						elif (queue_command=='off' and (admin_auth(user) or broadcaster_auth(channel, user) or trusted_auth(channel, user))):
							try:
								channel_info[channel].toggle = False
								channel_info[channel].queue_clear()
								send_msg(channel, "Queue disabled")
								save_data()
							except KeyError:
								print("   > !queue off: No channel_info for %s" % channel)

						elif channel_info[channel].toggle:
							# Size of queue
							if (queue_command=='size'):
								try:
									send_msg(channel, "Size: %d" % channel_info[channel].queue_size())
								except KeyError:
									print("   > !queue size: No channel_info for %s" % channel)

							# Show entire queue
							elif (queue_command=='show' and (admin_auth(user) or broadcaster_auth(channel, user) or trusted_auth(channel, user))):
								try:
									if channel_info[channel].queue_size() > 0:
										send_msg(channel, "Queue: %s" % list_to_str(channel_info[channel].queue))
									else:
										send_msg(channel, "Queue is empty")
								except KeyError:
									print("   > !queue show: No channel_info for %s" % channel)

							# Show current player group
							elif (queue_command=='players'):
								try:
									if len(channel_info[channel].players) > 0:
										send_msg(channel, "Current Player(s): %s" % list_to_str(channel_info[channel].players))
									else:
										send_msg(channel, "No current group")
								except KeyError:
									print("   > !queue players: No channel_info for %s" % channel)

							# Add user to queue
							elif (queue_command=='add'):
								try:
									if channel_info[channel].queue_add(user):
										send_msg(channel, "%s added to queue" % user)
									else:
										send_msg(channel, "%s is #%d in the queue" % (user, channel_info[channel].queue_position(user)))
								except KeyError:
									print("   > !queue add: No channel_info for %s" % channel)

							# Remove user from queue or group. Admin can remove queue_arg
							elif (queue_command=='remove'):
								try:
									remove_name = queue_arg if queue_arg != None and (admin_auth(user) or broadcaster_auth(channel, user) or trusted_auth(channel, user)) else user
									result = channel_info[channel].queue_remove(remove_name)

									if result == 'Q':
										send_msg(channel, "%s removed from queue" % remove_name)
									elif result == 'D':
										send_msg(channel, "Dropped: %s" % remove_name)
									elif result[0] == 'R':
										send_msg(channel, "Replaced %s with %s" % (remove_name, result[1:]))
									elif result = 'N':
										send_msg(channel, "%s not in queue or group" % remove_name)
								except KeyError:
									print("   > !queue remove: No channel_info for %s" % channel)

							# Show user's position in queue
							elif (queue_command=='position'):
								try:
									name = queue_arg if queue_arg != None else user
									pos = channel_info[channel].queue_position(name)
									if pos > 0:
										send_msg(channel, "%s: #%d of %d" % (name, pos, channel_info[channel].queue_size()))
									else:
										send_msg(channel, "%s is not in the queue" % name)
								except KeyError:
									print("   > !queue position: No channel_info for %s" % channel)

							# Set size of player group
							elif (queue_command=='setsize') and (admin_auth(user) or broadcaster_auth(channel, user) or trusted_auth(channel, user)):
								if queue_arg != None:
									channel_info[channel].size = int(queue_arg)
									send_msg(channel, "Group size set to %d" % int(queue_arg))
									save_data()

							# Create new player group from the queue
							elif (queue_command=='new') and (admin_auth(user) or broadcaster_auth(channel, user) or trusted_auth(channel, user)):
								channel_info[channel].new_group()
								send_msg(channel, "New group: %s" % list_to_str(channel_info[channel].players))

							# Clear the queue and current group
							elif (queue_command=='clear') and (admin_auth(user) or broadcaster_auth(channel, user) or trusted_auth(channel, user)):
								channel_info[channel].queue_clear()
								send_msg(channel, "Queue cleared")

					#END queue commands

			# Reply to PING with a PONG
			elif (message[0]=='PING'):
				print('PONG')
				s.send(('PONG %s\r\n' % line[1]).encode())

if __name__ == '__main__':
	main()