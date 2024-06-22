import json
import re
import ssl
import subprocess
import irc.bot
import irc.connection
from datetime import datetime
from twikit import Client

with open('config.json', 'r') as f:
    config = json.load(f)

img2irc_path = subprocess.run(['which', 'img2irc'], capture_output=True, text=True)
if img2irc_path.returncode != 0:
    print("img2irc not found, disabling twitpic")
    config['bot']['twitPic'] = False

twitter_client = Client('en-US')
twitter_client.login(
    auth_info_1=config['twitter']['username'],
    auth_info_2=config['twitter']['email'],
    password=config['twitter']['password']
)

class TwitterIRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, config):
        self.config = config
        server = config['irc']['host']
        port = config['irc']['port']
        nickname = config['irc']['nick']
        realname = config['irc']['gecos']
        
        if config['irc'].get('use_ssl', False):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_factory = irc.connection.Factory(wrapper=ssl_context.wrap_socket)
            irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, realname, connect_factory=ssl_factory)
        else:
            irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, realname)
    
    def on_welcome(self, connection, event):
        for channel in self.config['irc']['channels']:
            print(f"Joining {channel}")
            connection.join(channel)

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]
        args = message.split(' ')
        text = ' '.join(args[1:])

        if message.startswith('!image '):
            self.config['bot']['twitPic'] = text == 'on'
            connection.privmsg(event.target, f"twitpic {'on' if self.config['bot']['twitPic'] else 'off'}")

        elif message.startswith('!width '):
            self.config['bot']['ansi']['width'] = int(text)
            connection.privmsg(event.target, f"twitpic width {self.config['bot']['ansi']['width']}")

        elif message.startswith('!len '):
            self.config['bot']['maxTweetLength'] = int(text)
            connection.privmsg(event.target, f"maxTweetLength {self.config['bot']['maxTweetLength']}")

        elif message.startswith('!wrap '):
            self.config['bot']['wrapLen'] = int(text)
            connection.privmsg(event.target, f"wrapLen {self.config['bot']['wrapLen']}")

        elif re.search(r'(twitter|x)\.com/.+?/status/\d+', message):
            tweet_id = re.search(r'(twitter|x)\.com/.+?/status/(\d+)', message).group(2)
            tweet = get_tweet(tweet_id)
            if tweet:
                draw_tweet(tweet, event, connection)

def wrap_text(input_text, line_length):
    paragraphs = input_text.split("\n")
    result = []

    for paragraph in paragraphs:
        words = paragraph.split(' ')
        line = ''

        for word in words:
            if len(line) + len(word) <= line_length:
                line += ' ' + word if line else word
            else:
                result.append(line)
                line = word

        result.append(line)
    return '\n'.join(result)

def get_ansi(url, options):
    opts = [f"--{k}" if v is True else f"--{k}={v}" for k, v in options.items()]
    result = subprocess.run(['img2irc', url] + opts, capture_output=True, text=True)
    ansi_art = result.stdout.replace('\n', '\x0f\n')
    num_lines = len(result.stdout.split('\n'))
    return ansi_art, num_lines

def append_multiline_strings(str1, str2, padding):
    lines1 = str1.split('\n')
    lines2 = str2.split('\n')
    max_length = max(len(lines1), len(lines2))

    result = []
    for i in range(max_length):
        line1 = lines1[i] if i < len(lines1) else ''
        line2 = lines2[i] if i < len(lines2) else ''
        line1padding = config['bot']['ansi']['width'] - len(line1)
        result.append(line1 + ' ' * line1padding + ' ' * padding + line2)

    return '\n'.join(result).strip()

def send_multiline_message(connection, target, message):
    for line in message.split('\n'):
        connection.privmsg(target, line)

def draw_tweet(tweet, event, connection):
    tweet_text = tweet.full_text if len(tweet.full_text) <= config['bot']['maxTweetLength'] else tweet.full_text[:config['bot']['maxTweetLength']] + "..."
    twit_date = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y').strftime('%b %d %Y')
    
    stats = f"\x03{config['bot']['colors']['retweets']}{config['bot']['symbols']['retweets']} {tweet.retweet_count}\x03 "
    stats += f"\x03{config['bot']['colors']['likes']}{config['bot']['symbols']['likes']} {tweet.favorite_count}\x03"

    header = f"\x03{config['bot']['colors']['name']}\x1f\x02{tweet.user.name}\x02\x1f "
    header += f"\x03{config['bot']['colors']['user']}@{tweet.user.screen_name} "
    header += f"\x03{config['bot']['colors']['date']}{twit_date}\n"

    wrapped = wrap_text(tweet_text, config['bot']['wrapLen'])
    if config['bot']['colors']['text']:
        wrapped = '\n'.join([f"\x03{config['bot']['colors']['text']}{line}\x03" for line in wrapped.split('\n')])
    
    text = header + wrapped

    if config['bot']['twitPic']:
        print("Profile Image URL:", tweet.user.profile_image_url)
        ansi, ansi_height = get_ansi(tweet.user.profile_image_url, config['bot']['ansi'])

        num_lines = len(text.split('\n')) + 1

        if num_lines < ansi_height:
            text += '\n' * (ansi_height - num_lines - 1)

        text += f"\n{stats}"

        message = append_multiline_strings(ansi, text, 1)
    else:
        text += f"\n{stats}"
        message = text

    send_multiline_message(connection, event.target, message)

def get_tweet(tweet_id):
    try:
        tweet = twitter_client.get_tweet_by_id(tweet_id)
        return tweet
    except Exception as e:
        print(e)

bot = TwitterIRCBot(config)
bot.start()
