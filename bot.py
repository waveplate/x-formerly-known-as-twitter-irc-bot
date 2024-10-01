import html
import json
import re
import ssl
import subprocess
import irc.bot
import irc.connection
from datetime import datetime
from twikit import Client

import asyncio
import threading
from queue import Queue
import signal
import sys

twitter_client = Client('en-US')

with open('config.json', 'r') as f:
    config = json.load(f)

img2irc_path = subprocess.run(['which', 'img2irc'], capture_output=True, text=True)
if img2irc_path.returncode != 0:
    print("img2irc not found, disabling twitpic")
    config['bot']['twitPic'] = False

class AsyncLoopThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.daemon = True

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

async_loop_thread = AsyncLoopThread()
async_loop_thread.start()
loop = async_loop_thread.loop

send_queue = Queue()

async def async_login():
    try:
        huh = await twitter_client.login(
            auth_info_1=config['twitter']['username'],
            auth_info_2=config['twitter']['email'],
            password=config['twitter']['password']
        )
        print("Login successful:", huh)
        return True
    except Exception as e:
        print("Login failed:", e)
        return False

async def async_get_tweet(tweet_id):
    try:
        tweet = await twitter_client.get_tweet_by_id(tweet_id)
        return tweet
    except Exception as e:
        print(f"Error fetching tweet {tweet_id}: {e}")
        return None

class TwitterIRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, config, loop, send_queue):
        self.config = config
        self.loop = loop
        self.send_queue = send_queue
        self.logged_in = False

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

        self.sender_thread = threading.Thread(target=self.process_send_queue, daemon=True)
        self.sender_thread.start()

    def process_send_queue(self):
        while True:
            target, message = self.send_queue.get()
            if message:
                try:
                    self.connection.privmsg(target, message)
                except Exception as e:
                    print(f"Error sending message to {target}: {e}")
            self.send_queue.task_done()

    def on_welcome(self, connection, event):
        for channel in self.config['irc']['channels']:
            print(f"Joining {channel}")
            connection.join(channel)

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]
        args = message.split(' ')
        text = ' '.join(args[1:])

        asyncio.run_coroutine_threadsafe(
            self.handle_pubmsg(connection, event, message, text),
            self.loop
        )

    async def handle_pubmsg(self, connection, event, message, text):
        if not self.logged_in:
            success = await async_login()
            self.logged_in = success
            if not success:
                self.send_queue.put((event.target, "Failed to login to Twitter."))
                return

        if message.startswith('!image '):
            self.config['bot']['twitPic'] = text.lower() == 'on'
            response = f"twitpic {'on' if self.config['bot']['twitPic'] else 'off'}"
            self.send_queue.put((event.target, response))

        elif message.startswith('!width '):
            try:
                self.config['bot']['ansi']['width'] = int(text)
                response = f"twitpic width {self.config['bot']['ansi']['width']}"
                self.send_queue.put((event.target, response))
            except ValueError:
                self.send_queue.put((event.target, "Invalid width value."))

        elif message.startswith('!len '):
            try:
                self.config['bot']['maxTweetLength'] = int(text)
                response = f"maxTweetLength {self.config['bot']['maxTweetLength']}"
                self.send_queue.put((event.target, response))
            except ValueError:
                self.send_queue.put((event.target, "Invalid maxTweetLength value."))

        elif message.startswith('!wrap '):
            try:
                self.config['bot']['wrapLen'] = int(text)
                response = f"wrapLen {self.config['bot']['wrapLen']}"
                self.send_queue.put((event.target, response))
            except ValueError:
                self.send_queue.put((event.target, "Invalid wrapLen value."))

        elif message.startswith('!delay '):
            try:
                self.config['bot']['delay'] = float(text)
                response = f"delay {self.config['bot']['delay']}"
                self.send_queue.put((event.target, response))
            except ValueError:
                self.send_queue.put((event.target, "Invalid delay value."))

        elif re.search(r'(twitter|x)\.com/.+?/status/(\d+)', message):
            match = re.search(r'(twitter|x)\.com/.+?/status/(\d+)', message)
            if match:
                tweet_id = match.group(2)
                tweet = await async_get_tweet(tweet_id)
                if tweet:
                    draw_tweet(tweet, event, connection, self.send_queue, self.config)
                else:
                    self.send_queue.put((event.target, "Failed to retrieve the tweet."))

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

def append_multiline_strings(str1, str2, padding, config):
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

def send_multiline_message(send_queue, target, message):
    for line in message.split('\n'):
        send_queue.put((target, line))

def draw_tweet(tweet, event, connection, send_queue, config):
    try:
        text = getattr(tweet, 'full_text', tweet.text)
        tweet_text = text if len(text) <= config['bot']['maxTweetLength'] else text[:config['bot']['maxTweetLength']] + "..."
        tweet_text = html.unescape(tweet_text)

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

            message = append_multiline_strings(ansi, text, 1, config)
        else:
            text += f"\n{stats}"
            message = text

        send_multiline_message(send_queue, event.target, message)
    except Exception as e:
        print("Error drawing tweet:", e)
        
if __name__ == "__main__":
    try:
        bot = TwitterIRCBot(config, loop, send_queue)
        bot.start()
    except KeyboardInterrupt:
        print("Shutting down bot...")
        async_loop_thread.stop()
        sys.exit(0)
