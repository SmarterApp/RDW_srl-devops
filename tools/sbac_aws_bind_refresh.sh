#!/bin/bash
PYTHONDIR=/usr/bin
NAMEDPIDFILE=/var/run/named/named.pid
(test ! -s $NAMEDPIDFILE) && echo "named lock file not found!" && exit
NAMEDPID=`/bin/cat $NAMEDPIDFILE` 
ZONEFILE=/var/named/zone/INTERNAL.test.sbac2dc.net
REVZONEFILE=/var/named/zone/INTERNAL.170.10.in-addr.arpa
SPORKPATH=/usr/lib/python2.6/site-packages
SERIAL=`/bin/date +%Y%m%d%H%S`

TEMPFILECONTENT=`$PYTHONDIR/python $SPORKPATH/AwsSpork/AwsSpork.py -li` 
(
flock -x -w 60 200 || exit 128

echo "" | /usr/bin/tee $REVZONEFILE > $ZONEFILE
echo ";" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "\$TTL 1h" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "@ IN SOA  ns.test.sbac2dc.net. test.sbac2dc.net (" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "      $SERIAL ;serial (version)" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "          3h  ;refresh period" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "          1h  ;retry refresh this often" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "          1w  ;expiration period" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "          1h  ;Negative caching TTL" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "      )" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "" | /usr/bin/tee -a $REVZONEFILE >> $ZONEFILE
echo "                              IN NS      ns" >> $ZONEFILE
echo "ns                            IN A       10.170.55.18" >> $ZONEFILE
echo "                          IN NS      ns.test.sbac2dc.net." >> $REVZONEFILE
echo "18.55                     IN PTR     ns.test.sbac2dc.net." >> $REVZONEFILE


echo "Creating entries..."
while read i
do
        temp=`echo ${i%%'|'*}`
        NEWADDR="`echo ${i##*':'}`"
    LASTOCT="`echo ${NEWADDR##*'.'}`"
    THIRDOCT="`echo ${NEWADDR%'.'*}`"
    THIRDOCT="`echo ${THIRDOCT##*'.'}`"
        NEWHOSTNAME="`echo ${temp##*':'}`"
    NEWHOSTNAME="`echo ${NEWHOSTNAME%%'.test.sbac2dc.net'*}`"
    if [[ $NEWHOSTNAME != *_* ]] && [[ $NEWHOSTNAME != *.* ]] && [[ $NEWHOSTNAME != "None" ]] && [[ $NEWHOSTNAME != *" "* ]] && [[ $NEWADDR != "None" ]]
    then
        echo "$NEWHOSTNAME              IN A $NEWADDR" >> $ZONEFILE
        echo "$LASTOCT.$THIRDOCT                    IN PTR $NEWHOSTNAME.test.sbac2dc.net." >> $REVZONEFILE
    fi
done <<< "$TEMPFILECONTENT"


chown named:named $ZONEFILE
chown named:named $REVZONEFILE
) 200>$ZONEFILE

echo "Restarting named..."
kill -1 $NAMEDPID
