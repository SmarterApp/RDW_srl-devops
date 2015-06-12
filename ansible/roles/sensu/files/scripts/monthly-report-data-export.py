#!/bin/env python

''' This script will create csv files with the average/max of
      - disk usage [average]
      - web-response [average]
      - concurrent sessions [max]
    for servers monitored on this sensu server '''

from collections import OrderedDict
import datetime
import locale
import os
import re
import subprocess
import time

locale.setlocale(locale.LC_ALL, 'en_US')

metrics = {}
metrics["Used MB"] = ['/data/carbon/whisper/sys/', '/disk/by_mount/',
                      'used_mb.wsp']
metrics["Web-Response"] = ['/data/carbon/whisper/middleware/httpd/',
                           '/response_usec/', 'percentile_90.wsp']
metrics["Concurrency"] = ['/data/carbon/whisper/middleware/httpd/',
                          '/concurrency/',
                          'concurrent_sessions_300_sec_window.wsp']


d = datetime.date(2015, 5, 31)
unix_epoch = int(time.mktime(d.timetuple()))


all_csvs = {}
totals = OrderedDict()


def write_csv(csv_filename, csv):
    file = open("/tmp/" + csv_filename, 'w')
    file.write(csv)
    file.close
    
    print '\nWrote /tmp/' + csv_filename + '\n'


def fetch_whisper(wsp, app, app_class):
    # verify .wsp exists or skip
    if not os.path.isfile(wsp):
        print 'missing file!!!', wsp
        return
    cmd = ["whisper-fetch", "--pretty", "--from", "%s" % unix_epoch, wsp]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    
    while True:
        line = proc.stdout.readline()
        if line != '':
            s = re.match("\S+ (\S+)\s+([0-9]+) \S+ [0-9]+\s+([0-9]+)", line)
            if not s:
                continue
            month = s.group(1)
            day = s.group(2)
            day = int(day)
            print '\r', month, day,
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
                    totals[month][app_class][day]['total_or_max'] = 0

            if metric == "Concurrency":
                """ Prepare for Max concurrent sessions per day """
                if number > totals[month][app_class][day]['total_or_max']:
                    totals[month][app_class][day]['total_or_max'] = number
            else:
                """ Prepare for Average """
                totals[month][app_class][day]['counter'] += 1
                totals[month][app_class][day]['total_or_max'] += number
        else:
            break
    

def make_csv(totals, metric):
    print '\n\n=====\nWriting csv\'s...'
    all_days = OrderedDict()
    for month, items in totals.iteritems():
        if month not in all_days:
            all_days[month] = OrderedDict()
        for app, items2 in items.iteritems():
            for day, items3 in items2.iteritems():
                if day not in all_days[month]:
                    all_days[month][day] = OrderedDict()
                counter = items3['counter']
                total_or_max = items3['total_or_max']

                if metric == "Concurrency":
                    """ Max concurrent sessions per day """
                    final_number = total_or_max
                else:
                    """ Average """
                    average = total_or_max / counter
                    final_number = average

                final_number = locale.format("%d", final_number, grouping=True)
                final_number += " MB"

                if 'db' in app:
                    all_days[month][day]['db'] = final_number
                if 'extract' in app:
                    all_days[month][day]['extract'] = final_number
                if 'gluster' in app:
                    all_days[month][day]['gluster'] = final_number
                if 'web' in app:
                    all_days[month][day]['web'] = final_number

        if metric == "Used MB":
            csv = '"Day of month", '
            csv += '"Database Servers", '
            csv += '"Extract Servers", "Reporting Storage Servers"\n'
        elif metric == "Web-Response":
            csv = '"Day of month", "mean 90_percentile"\n'
        elif metric == "Concurrency":
            csv = '"Day of month", "Max Number of Concurrent Sessions"\n'

        for month, days in all_days.iteritems():
            for day, items in days.iteritems():
                if metric == "Used MB":
                    csv_filename = "disk-usage-data.txt"
                    db = items['db']
                    extract = items['extract']
                    gluster = items['gluster']
                    csv += '"' + month + ' ' + str(day) + '", "' + db + '", "'
                    csv += extract + '", "' + gluster + '"\n'
                elif metric == "Web-Response":
                    csv_filename = "web-response-data.txt"
                    web = items['web']
                    csv += '"' + month + ' ' + str(day) + '", "' + web + '"\n'
                elif metric == "Concurrency":
                    csv_filename = "concurrency-data.txt"
                    web = items['web']
                    csv += '"' + month + ' ' + str(day) + '", "' + web + '"\n'
    write_csv(csv_filename, csv)


def amass_csvs(totals, metric):
    """ This function will gather all csv's into a list, to process at
        completion all at once. """

    all_csvs[metric] = totals

    
def loop_mounts(app, path, metric_file):
    mounts = []
    total_dirs = 0
    for mountpoint in os.listdir(path):
        total_dirs += 1
        mounts.append(mountpoint)
    if len(mounts) > 1:
        mounts.remove("_")
    
    for mountpoint in mounts:
        mountpointS = mountpoint.replace("_", "/")
        print '\n\nGetting', app, "mountpoint: ", mountpointS
    wsp = path + mountpoint + "/" + metric_file
    fetch_whisper(wsp, app)


for metric in metrics:
    print '\nStarting', metric, 'metric...'
    grand_total = {}
    path_prefix = metrics[metric][0]
    path_suffix = metrics[metric][1]
    metric_file = metrics[metric][2]
    server_classes = ['db', 'extract', 'gluster']

    for app in os.listdir(path_prefix):
        found = ""
        if metric == "Used MB":
            for server_class in server_classes:
                if server_class not in app:
                    continue
                else:
                    found = True
                    app_class = server_class
                    break
            if not found:
                continue

        print '\n\tProcessing', app, "... ",
        path = path_prefix + app + path_suffix
    
        if metric == "Used MB":
            # Issue: If we use mountpoints for some but / for others - it
            # skews greatly when averaging out e.g. 'all db servers on June 1,
            # avg is 780MB... that's skewed due to some small mountpoints.
            # temp solution: Use / on all servers, for a more proportional
            # average result
            # possible solution: have 2 averages: 1 for servers-with-mountpoints, one for all /
            # loop_mounts(app, path, metric_file)
            wsp = path + "_/" + metric_file
            fetch_whisper(wsp, app, app_class)
        else:
            wsp = path + metric_file
            fetch_whisper(wsp, app, app_class="web")
    amass_csvs(totals, metric)

for metric, totals in all_csvs.iteritems():
    make_csv(totals, metric)
