#!/bin/bash

ENVO=$(echo $SBAC_ENV|cut -d/ -f 1)
MIRRORDIR=$HOME/s3-mirrors/smarter-$ENVO-cloudtrail
DATADIR=$HOME/srl-devops/tools/cleanup/data/$ENVO
BINDIR=$HOME/srl-devops/tools/cleanup/bin

DO_CLOUDTRAIL=false
DO_EVENTS=false
DO_INSTANCES=true
DO_VOLUMES=true

. $HOME/srl-devops/tools/aws-env-vars.sh

mkdir -p $MIRRORDIR
mkdir -p $DATADIR

if $DO_CLOUDTRAIL; then 

    echo
    echo Syncing down cloudtrail...
    echo 

    aws s3 sync s3://smarter-$ENVO-cloudtrail $MIRRORDIR
fi

if $DO_EVENTS; then 
    echo
    echo Extracting relevant events...
    echo
    
    cd $DATADIR

    MONTHDAYS=$(find $MIRRORDIR/AWSLogs/*/CloudTrail/us-east-1/2015/ -maxdepth 2 -mindepth 2 -type d | cut -d/ -f 11,12 | sort)
    # MONTHDAYS="06/01"

    for MONTHDAY in $MONTHDAYS; do
        FMONTHDAY=$(echo $MONTHDAY | sed -e 's/\//-/')
        echo "   extracting $MONTHDAY"
        find $MIRRORDIR/AWSLogs/*/CloudTrail/us-east-1/2015/$MONTHDAY -name '*.gz' \
	    | xargs gunzip --stdout \
	    | jq -c '.Records|.[]' \
	    | fgrep -v -f $BINDIR/users.ignore \
	    | fgrep -v -f $BINDIR/events.ignore \
	            > events.all.$FMONTHDAY
    done

    cat events.all.0?-?? > events.all
    rm events.all.0?-??
fi

if $DO_INSTANCES; then
    
    echo
    echo Fetching instance descriptions
    echo

    cd $DATADIR
    
    aws ec2 describe-instances \
        | jq -c -S '.Reservations|.[]|.Instances|.[]' \
             > instances.all
fi

if $DO_VOLUMES; then
    
    echo
    echo Fetching volume descriptions
    echo

    cd $DATADIR
    
    aws ec2 describe-volumes \
        | jq -c -S '.Volumes|.[]' \
             > volumes.all
fi

