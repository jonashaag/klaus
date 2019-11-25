FROM alpine:edge

RUN echo http://dl-cdn.alpinelinux.org/alpine/edge/testing >> /etc/apk/repositories && \
    apk add --no-cache uwsgi-python python3-dev git ctags gcc musl-dev \
                       py3-six py3-markupsafe py3-pygments py3-dulwich py3-humanize \
                       py3-flask py3-flask-httpauth py3-flask-markdown
RUN pip3 install klaus python-ctags3

EXPOSE 5000
ENTRYPOINT ["uwsgi", "--plugin", "python", "--http11-socket", "0.0.0.0:5000"]
CMD ["-w", "klaus.contrib.wsgi_autoreload"]
