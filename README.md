> [!WARNING]
> this project uses twikit, as you cannot retrieve tweets using the free tier of the API any longer. **this can get you suspended**, which i found out today

# twitter-irc-bot (0.1.1)
this is an irc bot that previews tweets whenever a link to a tweet is posted in a channel

![twitter-irc-bot](https://i.imgur.com/cI1rIe8.png)

if you have `img2irc` installed, or use the included docker container, it can optionally show the profile picture of the user

# required configuration
edit `config.json.example`, the `irc` and `twitter` sections are self-explanatory

# quickstart with docker
`docker-compose up -d`

# running without docker
### 1) build or install `img2irc` (optional)

to build from source

`git clone https://github.com/waveplate/img2irc`

`cd img2irc && cargo build --release`

`sudo cp target/release/img2irc /usr/local/bin`

or use the statically linked x86_64 musl binary (recommended)


      cd /tmp
      wget https://github.com/waveplate/img2irc/releases/download/v1.1.0/img2irc-1.1.0-linux-x86_64.tar.gz
      sudo tar -xzf img2irc-1.1.0-linux-x86_64.tar.gz -C /usr/local/bin --strip-components=1 img2irc-1.1.0/img2irc
      rm -rf img2irc-1.1.0-linux-x86_64.tar.gz


### 2) install dependencies
`pip install irc twikit asyncio requests`

### 3) start `twitter-irc-bot`
`python bot.py`

# commands
| command | argument | function |
| --- | --- | --- |
| `!image` | `on` or `off`  | toggles whether the profile picture should be displayed |
| `!width` | default is `10` | width of the profile picture |
| `!len` | default is `400` | maximum number of characters for the tweet, after which it will truncate and add an ellipsis |
| `!wrap` | default is `60` | number of characters after which to wrap the text, influences the width of the text box |
| `!delay` | default is `0.1` | number of seconds to sleep after sending each line of text (long tweet may trigger flood limits)

# optional configuration

### img2irc

the `bot.ansi` section controls the arguments which will be sent to `img2irc`, and correspond to the command-line arguments which `img2irc` takes

for information about those arguments, see the usage details [here](https://github.com/waveplate/img2irc#usage)

the default settings are

```
        "ansi": {
            "qb": true,
            "irc"; true,
            "width": 10,
            "scale": "2:1",
            "contrast": 4,
            "nograyscale": true
        },
```

where `width` is the width of the profile picture, and `contrast: 4` increases the contrast by 4%

by default it will use quarterblocks, to use the previous default of halfblocks replace `qb` with `hb` and remove `scale`

for flags which do not take any arguments, simply set the value to `true`, e.g.,

```
        "ansi": {
            "width": 10,
            "contrast": 30,
            "sharpen": true
        },
```

### text colours

you can change the colour of the display name, username, date, tweet text, retweets and likes

```
        "colors": {
            "name": "",
            "user": "",
            "date": "14",
            "text": "",
            "retweets": "09",
            "likes": "04"
        },
```

leaving the field blank means no explicit colour. here are the [mirc colour codes](https://www.mirc.com/colors.html)

if the colour code is a single digit, you should pad it with a leading zero (e.g., `09` instead of `9`)

### symbols

you can modify which symbols to use for the retweets and likes as well

```
        "symbols": {
            "retweets": "↻",
            "likes": "❤"
        }
```
