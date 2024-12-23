FROM python:3.10-bullseye

USER root

COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

RUN apt update
RUN apt -y install curl git

RUN cd /tmp && \
    wget https://github.com/waveplate/img2irc/releases/download/v1.1.0/img2irc-1.1.0-linux-x86_64.tar.gz && \
    tar -xvf img2irc-1.1.0-linux-x86_64.tar.gz && \
    cp /tmp/img2irc-1.1.0/img2irc /usr/local/bin/img2irc

RUN pip install irc asyncio requests

ENTRYPOINT ["/bin/bash", "/root/entrypoint.sh"]
