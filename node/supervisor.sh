#!/bin/bash
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

nodemon -w $SCRIPTPATH/dist/ $SCRIPTPATH/dist/server.js
