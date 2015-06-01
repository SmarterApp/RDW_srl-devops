#!/bin/env python

''' This script will display a grand total of
    disk usage for all servers monitored on
    this sensu server '''


from collections import OrderedDict
import datetime
import os
import re
import subprocess
import time

#files = ['avail_mb.wsp', 'capacity_pct.wsp', 'used_mb.wsp']
files = ['used_mb.wsp']

d = datetime.date(2015,5,3)

unix_epoch_may_1 = int(time.mktime(d.timetuple()))


grand_total = {}
for dir in os.listdir("/data/carbon/whisper/sys"):
    print 'Getting', dir

    path = '/data/carbon/whisper/sys/%s/disk/by_mount/_/' % dir

    for file in files:
        proc = subprocess.Popen(["whisper-fetch --pretty --from %s %s%s | grep -v None" % (unix_epoch_may_1, path, file)], stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        print "program output:", out


    s = re.findall("\S+ (\S+\s+[0-9]+) \S+ [0-9]+\s+([0-9]+)", out)

    totals = OrderedDict({})

    for i in s:
        month = i[0]
        number = i[1]
        totals[month] = number

    print totals
    for item in totals.items():
        Day = item[0]
        total = item[1]
        print Day, total
        if Day not in grand_total.keys():
            grand_total[Day] = 0

        grand_total[Day] += int(total)
    print 'Grand Totals:', grand_total
