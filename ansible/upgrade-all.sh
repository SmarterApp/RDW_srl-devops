#!/bin/bash

for GROUP in $(cat roles/orchestration/files/startup-groups.txt); do
    echo Running group.....
    echo '          ' $GROUP
    ansible-playbook upgrade-os.yml -l $GROUP --check
done
