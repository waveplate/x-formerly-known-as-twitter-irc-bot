FROM python:3.10-bullseye

USER root

COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

RUN apt update
RUN apt -y install curl git

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y

RUN cd /root && \
    git clone https://github.com/waveplate/img2irc && \
    cd img2irc && \
    ~/.cargo/bin/cargo build --release

RUN cp /root/img2irc/target/release/img2irc /usr/local/bin/img2irc

RUN pip install irc twikit

ENTRYPOINT ["/bin/bash", "/root/entrypoint.sh"]