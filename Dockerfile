FROM alpine:edge

RUN echo http://dl-cdn.alpinelinux.org/alpine/edge/testing >> /etc/apk/repositories && \
    apk add --no-cache uwsgi-python git ctags  py3-six py3-markupsafe py3-pygments \
                       py3-dulwich py3-humanize py3-flask py3-flask-markdown py3-docutils

RUN apk add --no-cache python3-dev py3-pip gcc musl-dev && \
    pip3 install python-ctags3 && \
    apk del python3-dev gcc musl-dev

ARG KLAUS_VERSION
RUN pip3 install klaus${KLAUS_VERSION:+==}${KLAUS_VERSION}
