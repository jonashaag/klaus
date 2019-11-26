#!/bin/sh -e
docker build -t klaus:$TRAVIS_TAG --build-arg KLAUS_VERSION=$TRAVIS_TAG .
echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
docker push jonashaag/klaus:$TRAVIS_TAG
