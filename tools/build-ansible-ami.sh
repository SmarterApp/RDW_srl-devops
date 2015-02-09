#!/bin/bash

cd ..

BUILD_ENV=test182 # A place with a sane BIND, among other things
TARGET_ENV=prod   # We are not, in fact, in kansas anymore.

# Spawn an ansible image with no playbook
cd spawner
./spawner.py -t ami-builder:ansible -e $BUILD_ENV -a ansible -s || exit $?

# Wait
echo "Waiting 60 sec for instance to come up..."
sleep 60

cd ../ansible

# Read instance ID
PRIVATE_IP=$(inventories/srl.py | /usr/local/bin/jq '."tag_ami-builder_ansible"[0]' | sed -e 's/"//g')
INSTANCE_ID=$(inventories/srl.py | grep -B 1 $PRIVATE_IP | grep -P '  "i-.+": \[' | cut -c 4-13)


# Do a run with the env stuff set to BUILD_ENV.  This will allow it to do things like 
# reach the yum server, but will mis-configure it in some other ways.

ansible-playbook -l $BUILD_ENV -e ansible_cred_set=$TARGET_ENV ansible-for-ami.yml || exit $?

# Do the wacky patch-and-reboot play # TODO - RICK THIS IS YOUR BIT
ansible-playbook -l $BUILD_ENV patch-and-reboot.yml || exit $? 

# Run again, overriding ec2_tag_environment to make it think it is in the target.
ansible-playbook -l $BUILD_ENV -e ec2_tag_environment=$TARGET_ENV -e ansible_cred_set=$TARGET_ENV/inventory ansible-for-ami.yml || exit $?

# Shutdown - aws CLI?

# Snapshot AMI - aws CLI?

# Tag AMI - aws CLI?

# Terminate instance - aws CLI?

# Share AMI - aws CLI?
