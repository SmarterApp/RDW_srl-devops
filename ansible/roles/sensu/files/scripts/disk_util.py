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
files = {"Used MB": 'used_mb.wsp', "Capacity": "capacity_pct.wsp"}
files = {"Used MB": 'used_mb.wsp'}

d = datetime.date(2015,5,31)

unix_epoch = int(time.mktime(d.timetuple()))

grand_total = {}
for app in os.listdir("/data/carbon/whisper/sys"):

    print 'Starting', app

    for title, file in files.iteritems():
        total_dirs = 0
        mounts = []
        for mountpoint in os.listdir("/data/carbon/whisper/sys/" + app + "/disk/by_mount/"):
            total_dirs += 1
            mounts.append(mountpoint)
        if len(mounts) > 1:
            mounts.remove("_")

        for mountpoint in mounts:

            print 'Getting', app, "mountpoint: ", mountpoint

            path = '/data/carbon/whisper/sys/%s/disk/by_mount/%s/' % (app, mountpoint)
            cmd = ["whisper-fetch", "--pretty", "--from", "%s" % unix_epoch, "%s%s" % (path, file)]

            proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
            totals = OrderedDict({})

            while True:
                line = proc.stdout.readline()
                if line != '':
                    s = re.match("\S+ (\S+)\s+[0-9]+ \S+ [0-9]+\s+([0-9]+)", line)
                    if not s:
                        continue
                    month = s.group(1)
                    number = s.group(2)
                    if number == "None":
                        continue

                    totals[month] = number
                else:
                    break

            for item in totals.items():
                Day = item[0]
                total = item[1]
            #print Day, total
            #if title not in grand_total.keys():
            #    grand_total[title] = Day
                if Day not in grand_total.keys():
                    grand_total[Day] = 0
            
                grand_total[Day] += + int(total)
            print '[%s] Grand Totals:' % title, grand_total
