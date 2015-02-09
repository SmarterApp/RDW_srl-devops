#!/bin/bash

cd ..

BUILD_ENV=test182 # A place with a sane BIND, among other things
TARGET_ENV=prod   # We are not, in fact, in kansas anymore.

# Spawn an ansible image with no playbook
cd spawner
./spawner.py -t ami-builder:ansible -e $BUILD_ENV -a ansible -s || exit $?


# Do a run with the env stuff set to BUILD_ENV.  This will allow it to do things like 
# reach the yum server, but will mis-configure it in some other ways.
cd ../ansible
ansible-playbook -l $BUILD_ENV -e ansible_cred_set=$TARGET_ENV ansible-for-ami.yml || exit $?

# Run again, overrideing ec2_tag_environment to make it think it is in the target.
# TODO


# Shutdown

# Snapshot AMI

# Tag AMI

# Terminate instance

# Share AMI
