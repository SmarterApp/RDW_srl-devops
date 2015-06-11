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


totals = OrderedDict()
def fetch_whisper(wsp, app, app_class):
    cmd = ["whisper-fetch", "--pretty", "--from", "%s" % unix_epoch, wsp]
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
    
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
    
            if month not in totals:
                # Initialize the dictionaries & counter
                totals[month] = OrderedDict()
           

            if app_class in app:
                if app_class not in totals[month]:
                    totals[month][app_class] = {}
                if day not in totals[month][app_class]:
                    totals[month][app_class][day] = {}
                    totals[month][app_class][day]['counter'] = 0
                    totals[month][app_class][day]['total'] = 0
            totals[month][app_class][day]['counter'] += 1
            totals[month][app_class][day]['total'] += number
        else:
            break

def make_csv(totals):
    csv = '"Day of month", "Database Servers", "Extract Servers", "Reporting Storage Servers"\n'
    all_days = OrderedDict()
    for month, items in totals.iteritems():
        if month not in all_days:
            all_days[month] = OrderedDict()
        for app, items2 in items.iteritems():
            for day, items3 in items2.iteritems():
                if day not in all_days[month]:
                    all_days[month][day] = OrderedDict()
                total = items3['total']
                counter = items3['counter']
                average = total / counter

                average = locale.format("%d", average, grouping=True)
                average += " MB"

                if 'db' in app:
                    all_days[month][day]['db'] = average
                if 'extract' in app:
                    all_days[month][day]['extract'] = average
                if 'gluster' in app:
                    all_days[month][day]['gluster'] = average

    for month, days in all_days.iteritems():
        for day, items in days.iteritems():
            db = items['db']
            extract = items['extract']
            gluster = items['gluster']
            csv += '"' + month + ' ' + str(day) + '", "' + db + '", "' + extract + '", "' + gluster + '"\n'




    print csv
    file = open("/tmp/data_export.csv", 'w')
    file.write(csv)
    file.close
    
    print '\nWrote /tmp/data_export.csv\n'
    
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
    server_classes = ['db', 'extract', 'gluster']

    for app in os.listdir(path_prefix):
        found = ""
        for server_class in server_classes:
            if server_class not in app:
                continue
            else:
                found = True
                app_class = server_class
                break
        if not found:
            continue

        print 'Processing', app, "..."
        path = path_prefix + app + path_suffix
    
        if metric == "Used MB":
            # Issue: If we use mountpoints for some but / for others - it skews greatly when averaging out e.g. 'all db servers on June 1, avg is 780MB... that's skewed due to some small mountpoints.
            # temp solution: Use / on all servers, for a more proportional average result
            # possible solution: have 2 averages: 1 for servers-with-mountpoints, one for all /
            # loop_mounts(app, path, metric_file)
            wsp = path + "_/" + metric_file
            fetch_whisper(wsp, app, app_class)
            #continue  # testing Web-Response only
        #elif metric == "Web-Response":
        #    wsp = path + metric_file
            #fetch_whisper(wsp)
        else:
            continue
    make_csv(totals)
