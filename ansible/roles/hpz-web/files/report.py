#!/bin/env python

""" This script creates a .csv file stating whether Downloadable Reports were
    available within 24 hours at least 90% of the time. """

import datetime
import os
import re
import subprocess
import time

# Ensure sudo/root is being used

user = os.getenv("SUDO_USER")
if user is None:
    print "This script requires sudo"
    raise SystemExit

""" List all files from gluster /opt/edware/hpz/uploads/ """

all_uploaded_files = {}

path = "/opt/edware/hpz/uploads/"
for file in os.listdir(path):
    filepath = path + file
    if 'heartbeat' in file:
        continue  # skip - don't process the heartbeat file
    file_created = time.ctime(os.path.getctime(filepath))
    regex = "^(\S+)\s+(\S+)\s+([0-9]+)\s+([0-9]+):([0-9]+):([0-9]+)\s+([0-9]+)"
    m = re.match(regex, file_created)
    day_of_week = m.group(1)
    month = m.group(2)
    day_of_month = m.group(3)
    day_of_month = day_of_month.zfill(2)
    hour = m.group(4)
    minute = m.group(5)
    second = m.group(6)
    year = m.group(7)

    file_created_time = month + " " + day_of_month + " " + year + " "
    file_created_time += hour + ":" + minute + ":" + second

    pattern = "%b %d %Y %H:%M:%S"
    unixtime_done = int(time.mktime(time.strptime(file_created_time, pattern)))
    all_uploaded_files[file] = {unixtime_done: file_created}

""" Get all files from access_log* """

all_POST_files = {}
total_requests = 0
took_less_than_24_hours = 0
took_more_than_24_hours = 0
data = subprocess.Popen(['grep "POST /files/" /var/log/httpd/access_log*'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        shell=True)
while True:
    line = data.stdout.readline()
    if line != '':
        regex = "\[([0-9]{2}/[A-z]{3}/[0-9]{4}):(\S+).*?POST /files/(\S+)"
        s = re.search(regex, line)
        pdate = s.group(1)
        ptime = s.group(2)
        pdf_filename = s.group(3)
        dtext = "%d/%b/%Y %H:%M:%S"
        POSTtime = int(time.mktime(time.strptime(pdate + " " + ptime, dtext)))

        # skip anything older than X days
        days_to_follow = 60  # change this to # of days to check
        now_timestamp = time.time()
        if POSTtime < (now_timestamp - (86400 * days_to_follow)):
            continue

        all_POST_files[pdf_filename] = {POSTtime: pdate + " " + ptime}

        # check if file is in uploads
        print 'Checking', pdf_filename, "from", pdate, ptime
        time.sleep(1)
        total_requests += 1
        if pdf_filename in all_uploaded_files:
            uploaded_times = all_uploaded_files[pdf_filename]
            for uploaded_unix_timestamp, b in uploaded_times.iteritems():
                total_time_elapsed = uploaded_unix_timestamp - POSTtime
                print '\tTotal time elapsed, from click to complete:', total_time_elapsed, "seconds"
                if (POSTtime + 86400) < uploaded_unix_timestamp:
                    print "Took more than 24 hours!"
                    took_more_than_24_hours += 1
                else:
                    took_less_than_24_hours += 1
        else:
            print 'not found!!'
    else:
        break

print '\n\n\n'
print "Total Downloadable Reports clicks in the past",
print days_to_follow, "days:", total_requests

print "Total Downloadable Reports succeessful (less than 24 hours):",
print took_less_than_24_hours

print "Total Downloadable Reports failed (more than 24 hours):",
print took_more_than_24_hours

# Final SLA 90% calculation
percent_successful = (took_less_than_24_hours * 100) / total_requests
if percent_successful >= 90:
    SLA_commitment_met = "Yes!"
else:
    raise SystemExit

print '\n\n'
print "Percent successful downloads in the past",
print days_to_follow, "days:", percent_successful

print '\n\n'
print "SLA 90% success rate commitment met:", SLA_commitment_met

csv = '"SLA commitment met", '
csv += '"Percent successful", '
csv += '"Calculated over the past __ days", '
csv += '"Total Report Downloads", '
csv += '"Reports completed in less than 24h", '
csv += '"More than 24h"\n'

csv += '"' + SLA_commitment_met + '", '
csv += '"' + str(percent_successful) + '", '
csv += '"' + str(days_to_follow) + '", '
csv += '"' + str(total_requests) + '", '
csv += '"' + str(took_less_than_24_hours) + '", '
csv += '"' + str(took_more_than_24_hours) + '"'
csv += '\n'

file = open("/tmp/report.csv", 'w')
file.write(csv)
file.close

print '\nWrote /tmp/report.csv\n'
