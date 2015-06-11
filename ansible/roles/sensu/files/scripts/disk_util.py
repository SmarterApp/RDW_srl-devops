#!/bin/env python

''' This script will display a grand total of
      - disk usage 
      - web-response
      - concurrent sessions
    for all servers monitored on
    this sensu server '''




from collections import OrderedDict
import datetime
import locale
import os
import re
import subprocess
import time

#files = ['avail_mb.wsp', 'capacity_pct.wsp', 'used_mb.wsp']
#files = {"Used MB": 'used_mb.wsp', "Capacity": "capacity_pct.wsp"}
#files = {"Used MB": 'used_mb.wsp'}

locale.setlocale(locale.LC_ALL, 'en_US')

metrics = {}
metrics["Used MB"] = ['/data/carbon/whisper/sys/', '/disk/by_mount/', 'used_mb.wsp']
metrics["Web-Response"] = ['/data/carbon/whisper/middleware/httpd/', '/response_usec/', 'percentile_90.wsp']

d = datetime.date(2015,5,31)

unix_epoch = int(time.mktime(d.timetuple()))

def fetch_whisper(wsp, app):
    cmd = ["whisper-fetch", "--pretty", "--from", "%s" % unix_epoch, wsp]
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
    totals = OrderedDict()
    
    while True:
        line = proc.stdout.readline()
        if line != '':
            s = re.match("\S+ (\S+)\s+([0-9]+) \S+ [0-9]+\s+([0-9]+)", line)
            if not s:
                continue
            month = s.group(1)
            day = s.group(2)
            day = int(day)
            number = s.group(3)
            if number == "None":
                continue
            number = int(number)
            # format at the last step
            #number = locale.format("%d", number, grouping=True)
    
            if month not in totals:
                # Initialize the dictionaries & counter
                totals[month] = OrderedDict()
                totals[month]['db'] = {}
           

            if 'db' in app:
                if day not in totals[month]['db']:
                    totals[month]['db'][day] = {}
                    totals[month]['db'][day]['counter'] = 0
                    totals[month]['db'][day]['total'] = 0
            totals[month]['db'][day]['counter'] += 1
            totals[month]['db'][day]['total'] += number
        else:
            break
    for month, items in totals.iteritems():
        for app, items2 in items.iteritems():
            for day, items3 in items2.iteritems():
                total = items3['total']
                counter = items3['counter']
                average = total / counter
                csv_text = '"' + month + ' ' + str(day) + '", "' + str(average) + '"'
                print csv_text

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
    fetch_whisper(wsp, app)

for metric in metrics:
    grand_total = {}
    path_prefix = metrics[metric][0]
    path_suffix = metrics[metric][1]
    metric_file = metrics[metric][2]
    for app in os.listdir(path_prefix):
        if 'db' not in app:
            continue
        path = path_prefix + app + path_suffix
    
        if metric == "Used MB":
            loop_mounts(app, path, metric_file)
            #continue  # testing Web-Response only
        elif metric == "Web-Response":
            wsp = path + metric_file
            #fetch_whisper(wsp)
    print '[%s] Grand Totals:', grand_total
