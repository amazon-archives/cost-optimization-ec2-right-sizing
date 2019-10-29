#!/bin/bash

# This script should be run from the repo's deployment directory
# cd deployment
# ./run-unit-tests.sh

# Run unit tests
ORIGPWD=`pwd`
echo "Running unit tests"
echo "cd ../source"
cd ../source
echo "No unit tests to run, so sad ..."
echo "Completed unit tests"
# Return to where we came from
cd $ORIGPWD
