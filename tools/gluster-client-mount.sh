#!/bin/bash

if [[ "$#" -ne 1 ]]; then
	echo usage: $0 application.yml
	exit 1
fi 

if [[ -z $SBAC_DEVOPS ]]; then
	echo "You must set SBAC_DEVOPS first"
	exit 1
fi

if [[ ! -f $SBAC_DEVOPS/ansible/$1 ]]; then
	echo "Could not app yaml at $SBAC_DEVOPS/ansible/$1 "
	exit
fi

pushd .
cd $SBAC_DEVOPS/ansible
/usr/bin/ansible-playbook -i inventories/srl.py --tags gluster-client $1
popd