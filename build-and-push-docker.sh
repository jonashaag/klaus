#!/bin/sh -eu

log() {
  echo "$@" >&2
}

R=jonashaag/klaus

log "Building klaus==$TRAVIS_TAG"
docker build -t $R:$TRAVIS_TAG --build-arg KLAUS_VERSION=$TRAVIS_TAG .

log "Logging in to Docker Hub"
echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin

log "Pushing to :$TRAVIS_TAG"
docker push $R:$TRAVIS_TAG
if test "$(git tag | grep '^[0-9]' | sort -V | tail -n1)" = "$TRAVIS_TAG"; then
  log "Pushing to :latest"
  docker tag $R:$TRAVIS_TAG $R:latest
  docker push $R:latest
fi
