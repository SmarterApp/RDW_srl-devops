#!/bin/env python
""" remember to ansible : chmod 705 (or chmod o+rx) /var/log/httpd/
    Add ansible to apache group to read /opt/edware/hpz/uploads, is safer than chmod o+rx /opt/edware/hpz/uploads """

import re
import subprocess

data = subprocess.Popen(['grep "POST /files/" /var/log/httpd/access_log*'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
while True:
    line = data.stdout.readline()
    if line != '':
        s = re.search("\[([0-9]{2}/[A-z]{3}/[0-9]{4}):(\S+).*?POST /files/(\S+)", line)
        pdf_date = s.group(1)
        pdf_time = s.group(2)
        pdf_filename = s.group(3)
        print pdf_filename, pdf_date, pdf_time
    else:
        break


