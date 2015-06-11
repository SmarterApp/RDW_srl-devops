#!/bin/env python

''' This script will display a grand total of
      - disk usage 
      - web-response
      - concurrent sessions
    for all servers monitored on
    this sensu server '''


from collections import OrderedDict
import datetime
import os
import re
import subprocess
import time

#files = ['avail_mb.wsp', 'capacity_pct.wsp', 'used_mb.wsp']
#files = {"Used MB": 'used_mb.wsp', "Capacity": "capacity_pct.wsp"}
#files = {"Used MB": 'used_mb.wsp'}

metrics = {}
metrics["Used MB"] = ['/data/carbon/whisper/sys/', '/disk/by_mount/', 'used_mb.wsp']
metrics["Web-Response"] = ['/data/carbon/whisper/middleware/httpd/', '/response_usec/', 'percentile_90.wsp']

d = datetime.date(2015,5,31)

unix_epoch = int(time.mktime(d.timetuple()))

def fetch_whisper(wsp):
    cmd = ["whisper-fetch", "--pretty", "--from", "%s" % unix_epoch, wsp]
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
                #if title not in grand_total.keys():
                #    grand_total[title] = Day
        if Day not in grand_total.keys():
            grand_total[Day] = 0
                
        grand_total[Day] += int(total)
        print "Grant total so far:", grand_total

def loop_mounts(app, path, metric_file):
    mounts = []
    total_dirs = 0
    for mountpoint in os.listdir(path):
        total_dirs += 1
        mounts.append(mountpoint)
    if len(mounts) > 1:
        mounts.remove("_")
    
    for mountpoint in mounts:
        mountpointS = mountpoint.replace("_","/")
        print '\n\nGetting', app, "mountpoint: ", mountpointS
    wsp = path + mountpoint + "/" + metric_file
    fetch_whisper(wsp)

for metric in metrics:
    grand_total = {}
    path_prefix = metrics[metric][0]
    path_suffix = metrics[metric][1]
    metric_file = metrics[metric][2]
    for app in os.listdir(path_prefix):
        path = path_prefix + app + path_suffix
    
        if metric == "Used MB":
            loop_mounts(app, path, metric_file)
            #continue  # testing Web-Response only
        elif metric == "Web-Response":
            wsp = path + metric_file
            #fetch_whisper(wsp)
    print '[%s] Grand Totals:', grand_total
