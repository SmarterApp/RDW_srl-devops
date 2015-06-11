#!/bin/bash
. $HOME/srl-devops/tools/aws-env-vars.sh

ENVO=$(echo $SBAC_ENV|cut -d/ -f 1)
MIRRORDIR=$HOME/s3-mirrors/smarter-$ENVO-cloudtrail
DATADIR=$HOME/srl-devops/tools/cleanup/data/$ENVO
BINDIR=$HOME/srl-devops/tools/cleanup/bin

echo
echo Syncing down cloudtrail...
echo 

mkdir -p $MIRRORDIR
aws s3 sync s3://smarter-$ENVO-cloudtrail $MIRRORDIR

echo
echo Extracting relevant events...
echo 

mkdir -p $DATADIR
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
