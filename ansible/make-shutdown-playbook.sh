#!/bin/bash

rm -f stop-all-services.yml
for APP in $(cat roles/orchestration/files/shutdown-sequence.txt | fgrep -v '#'); do
    sed stop-all-services.yml.template -e "s/APPNAME/$APP/g" >> stop-all-services.yml
done
