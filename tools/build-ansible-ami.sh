#!/bin/bash

cd ..


APPLICATION=ansible
BUILD_ENV=test186 # A place with a sane BIND, among other things
TARGET_ENV=prod   # We are not, in fact, in kansas anymore.
TARGET_AWS_ACCOUNT=239158370733 # Account with which to share the image - prod

# Spawn an ansible image with no playbook
# This may challenge the user for their GPG password
echo '-----------'
echo 'Spawning....'
echo '-----------'
cd spawner
./spawner.py -t ami-builder:$APPLICATION -e $BUILD_ENV -a $APPLICATION -s 2>&1 | tee ami-builder.log || exit $?

# Regret
INSTANCE_ID=$(grep 'Tagging instance' ami-builder.log | egrep -o 'i-.{8}') || exit $?

# password store should be unlocked now
export AWS_ACCESS_KEY_ID=$(pass $SBAC_ENV/aws/access_id)
export AWS_SECRET_ACCESS_KEY=$(pass $SBAC_ENV/aws/secret_key)
export AWS_DEFAULT_REGION=us-east-1

echo '-----------'
echo "Waiting for instance to enter running state ..."
echo '-----------'
until [[ $(aws ec2 describe-instances --instance-id $INSTANCE_ID | jq '.Reservations[0].Instances[0].State.Code') -eq 16 ]]; do
    echo -n '.'
    sleep 3
done
echo

cd ../ansible

# Read instance ID
# TODO: fix APPLICATION reference
PRIVATE_IP=$(inventories/srl.py | jq '."tag_ami-builder_ansible"[0]' | sed -e 's/"//g')

# Do terrible things to make up a new version
BASE_VERSION=$(aws ec2 describe-instances --instance-id $INSTANCE_ID | jq '.Reservations[0].Instances[0].Tags|map(select(.Key == "version"))[0].Value' | sed -e 's/"//g')
BUMPED_VERSION=$(python -c "(maj, min) = '$BASE_VERSION'.split('.'); print maj + '.' + str(int(min) + 1)")
GIT_COMMIT=$(git rev-parse --short HEAD)
NEW_VERSION=${BUMPED_VERSION}-${GIT_COMMIT}

# Wait for SSH
echo '-----------'
echo "Waiting for SSH to come up..."
echo '-----------'
ansible-playbook -l $PRIVATE_IP wait-for-ssh.yml || exit $?


# Do a run with the env stuff set to BUILD_ENV.  This will allow it to do things like 
# reach the yum server, but will mis-configure it in some other ways.
# TODO: fix APPLICATION reference
echo '-----------'
echo ' Performing normal app run...'
echo '-----------'
ansible-playbook -l $PRIVATE_IP -e ansible_cred_set=$TARGET_ENV ansible-for-ami.yml || exit $?

# Do the wacky patch-and-reboot play
echo '-----------'
echo ' Patching.... '
echo '-----------'
ansible-playbook -l $PRIVATE_IP patch-and-reboot.yml || exit $? 

# Run again, overriding ec2_tag_environment to make it think it is in the target.
echo '-----------'
echo " Performing $TARGET_ENV-mode run..."
echo '-----------'
ansible-playbook -l $PRIVATE_IP -e ec2_tag_environment=$TARGET_ENV -e ansible_cred_set=$TARGET_ENV/inventory ansible-for-ami.yml || exit $?

# Snapshot AMI
echo "Creating AMI from instance ID $INSTANCE_ID"
AMI_ID=$(aws ec2 create-image --instance-id $INSTANCE_ID --name "${APPLICATION}-${TARGET_ENV}-${NEW_VERSION}" | jq .ImageId | sed -e 's/"//g')  || exit $?


echo "Waiting for AMI to be created before tagging"
until aws ec2 describe-images --image-id $AMI_ID > /dev/null 2>&1; do
    echo -n '.'
    sleep 3
done
echo

# Tag AMI
echo "Tagging AMI ID $AMI_ID"
aws ec2 create-tags --resources $AMI_ID --tags Key=application,Value=$APPLICATION Key=version,Value=$NEW_VERSION || exit $?

# Terminate instance
echo "Terminating instance ID $INSTANCE_ID"
aws ec2 terminate-instances --instance-ids $INSTANCE_ID || exit $?

# Share AMI
echo "Sharing AMI ID $AMI_ID to account $TARGET_AWS_ACCOUNT"
aws ec2 modify-image-attribute --image-id $AMI_ID --launch-permission "{\"Add\":[{\"UserId\":\"${TARGET_AWS_ACCOUNT}\"}]}" || exit $?

# TODO: AMI Tags are account-specific - A shared AMI will not have its tags applied in the target environment!
# You can get app name and version from the AMI name
