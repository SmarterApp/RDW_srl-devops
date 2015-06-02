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

d = datetime.date(2015,5,31)

unix_epoch = int(time.mktime(d.timetuple()))


mounts = {}
mounts['bind'] = '_'
mounts['file-trigger'] = '_'
mounts['gluster-server'] = '_'
mounts['lz'] = '_'
mounts['migrate-db'] = '_mnt_data'
mounts['reporting-generator-pdf'] = '_'
mounts['reporting-db-pgpool'] = '_'
mounts['reporting-db-slave'] = '_mnt_pgsql'
mounts['reporting-rabbit-extract'] = '_'
mounts['reporting-rabbit-services'] = '_'
mounts['reporting-web'] = '_'
mounts['reporting-worker-extract'] = '_'
mounts['reporting-worker-pdf'] = '_'
mounts['sensu'] = '_data'
mounts['sensu-rabbit'] = '_'
mounts['tsb-rabbit'] = '_'
mounts['tsb-worker'] = '_'
mounts['udl'] = '_'
mounts['udl-db'] = '_mnt_data'
mounts['udl-rabbit'] = '_'

grand_total = {}
for dir in os.listdir("/data/carbon/whisper/sys"):

    print 'Starting', dir

    for title, file in files.iteritems():
        found = False
        for server_class in mounts:
            if server_class + "-0" in dir:
                mountpoint = mounts[server_class]
                found = True
                break
        if not found:
            raise SystemExit("define mountpoint for %s" % dir)
        print 'Getting', dir, "mountpoint: ", mountpoint

        path = '/data/carbon/whisper/sys/%s/disk/by_mount/%s/' % (dir, mountpoint)
        cmd = ["whisper-fetch", "--pretty", "--from", "%s" % unix_epoch, "%s%s" % (path, file)]
        print cmd

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
            if title not in grand_total.keys():
                grand_total[title] = Day
            
            if title == "Used MB":
                grand_total[title][Day] += int(total)
            if title == "Capacity":
                grand_total[title][Day] = (grand_total[title][Day] + int(total)) / 2
        print '[%s] Grand Totals:' % title, grand_total
