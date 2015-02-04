#!/bin/bash

# Spawn an ansible image with no playbook
cd ../spawner
./spawner.py -t ami-builder:ansible -e dev -a ansible -s || exit $?

cd ../ansible

# Read out IP of spawned instance
