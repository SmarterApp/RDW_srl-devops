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

d = datetime.date(2015,5,31)

unix_epoch_may_1 = int(time.mktime(d.timetuple()))


grand_total = {}
for dir in os.listdir("/data/carbon/whisper/sys"):
    print 'Getting', dir


    for file in files:
        path = '/data/carbon/whisper/sys/%s/disk/by_mount/_/' % dir
        cmd = ["whisper-fetch", "--pretty", "--from", "%s" % unix_epoch_may_1, "%s%s" % (path, file)]

        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
        while True:
            line = proc.stdout.readline()
            if line != '':
            #the real code does filtering here
                s = re.match("\S+ (\S+\s+[0-9]+) \S+ [0-9]+\s+([0-9]+)", line)
                if not s:
                    continue
                totals = OrderedDict({})
                month = s.group(1)
                number = s.group(2)
                #print month, number

                totals[month] = number
            else:
                break

        print totals
        for item in totals.items():
            Day = item[0]
            total = item[1]
            print Day, total
            if Day not in grand_total.keys():
                grand_total[Day] = 0

            grand_total[Day] += int(total)
    print 'Grand Totals:', grand_total
