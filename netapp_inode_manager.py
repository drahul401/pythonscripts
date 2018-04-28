#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
__author__      = "Govardhan.Sunkishela@ADP.com "

import os
import re
import json
import time
import shlex
import sqlite3
import smtplib
import datetime
import subprocess
from pprint import pprint
from email import Encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase

inode_threshold = 1000
counter_threshold = 5

dir_path = os.path.dirname(os.path.realpath(__file__))
out_file = os.path.join(dir_path, 'netapp_inode_manager.html')
db_file = os.path.join(dir_path, 'netapp_inode_manager.sqlite')

# Today"s date
start_time = time.time()
today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
exceeded_vol_list = list()

conn = sqlite3.connect(db_file)
cur = conn.cursor()

def run_subcmd(command):
    command = shlex.split(command)
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         universal_newlines=True)
    stdout, stderr = p.communicate()
    return {'stdout': stdout, 'stderr': stderr, 'returncode': p.returncode}

def mount_db():
    # create and connect to database
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS netapp_filer (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        filer_name TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS inode_table (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        filer_id INTEGER,
        volume TEXT,
        itotal INTEGER,
        iused INTEGER,
        ifree INTEGER,
        iused_cap INTEGER,
        counter INTEGER,
        history TEXT
        );
        """)
    return 1

def update_db(filer,volume,itotal,iused,ifree,iused_cap):
    #update DB
    cur.execute('''INSERT OR IGNORE INTO netapp_filer (filer_name)
        VALUES (:filer)''', {'filer': filer} )
    cur.execute('SELECT id FROM netapp_filer WHERE filer_name =:filer ', {'filer': filer})
    filer_id = cur.fetchone()[0]
    cur.execute('SELECT id FROM inode_table WHERE filer_id =:filer_id AND volume =:volume', {'filer_id': filer_id, 'volume': volume})
    row_id = cur.fetchone()

    if row_id == None:
        # update inode_table table with the filesystem info
        cur.execute('''REPLACE INTO inode_table (filer_id, volume, itotal, iused, ifree, iused_cap)
            VALUES (:filer_id, :volume, :itotal, :iused, :ifree, :iused_cap)''',
            {'filer_id': filer_id, 'volume': volume, 'itotal': itotal, 'iused': iused, 'ifree': ifree, 'iused_cap': iused_cap})
        conn.commit()
    else:
        row_id = row_id[0]
        cur.execute('UPDATE inode_table SET itotal =:itotal, iused =:iused, ifree =:ifree, iused_cap =:iused_cap WHERE id =:id AND filer_id =:filer_id AND volume =:volume',
            {'itotal': itotal, 'iused': iused, 'ifree': ifree, 'iused_cap': iused_cap, 'id': row_id, 'filer_id': filer_id, 'volume': volume})
        conn.commit()

    cur.execute('SELECT counter FROM inode_table WHERE filer_id =:filer_id AND volume =:volume', {'filer_id': filer_id, 'volume': volume})
    counter_no = cur.fetchone()[0]
    return counter_no

def dbupdate_counter(filer, volume, new_counter_value, run_timestamp, new_inode_count):
    cur.execute('SELECT id FROM netapp_filer WHERE filer_name =:filer ', {'filer': filer})
    filer_id = cur.fetchone()[0]
    cur.execute('SELECT history FROM inode_table WHERE filer_id =:filer_id AND volume =:volume', {'filer_id': filer_id, 'volume': volume})
    history = cur.fetchone()[0]
    if history == None:
        history = json.loads('{}')
    else:
        history = json.loads(history)

    history[run_timestamp] = new_inode_count
    history = json.dumps(history)
    print new_counter_value
    print history

    cur.execute('UPDATE inode_table SET counter =:new_counter_value, history =:history WHERE filer_id =:filer_id AND volume =:volume',
            {'history': history, 'new_counter_value': new_counter_value, 'filer_id': filer_id, 'volume': volume})
    conn.commit()

def get_db_info():
    cur.execute('''SELECT netapp_filer.filer_name, inode_table.volume,inode_table.itotal,inode_table.iused,inode_table.ifree,inode_table.iused_cap,inode_table.counter,inode_table.history
        FROM inode_table JOIN netapp_filer
        ON inode_table.filer_id = netapp_filer.id
        ORDER BY inode_table.counter, inode_table.ifree''')
    sql_read_data = cur.fetchall()
    return sql_read_data

def get_inode_dfm():
    inode_ussage = dict()
    dfm_command = 'ssh dc1proncom01 dfm report view inode-utilization'
    dfm_output = run_subcmd(dfm_command)
    if not dfm_output['returncode']:
        for line in dfm_output['stdout'].splitlines():
            ind_data = line.split()
            if re.search("online$", ind_data[-1]):
                used_capacity = float(ind_data[-2])
                if used_capacity > 89.99:
                    volume = ind_data[1]
                    if not re.search('_dr', volume):
                        inode_ussage[volume] = {'filer': ind_data[3], 'usage': used_capacity}

    return inode_ussage

def get_maxfiles(filer,volume):

    #command_execution
    maxfile_cmd = "ssh storageops@{0} df -i {1}".format(filer, volume)
    maxfile_out = run_subcmd(maxfile_cmd)
    if not maxfile_out['returncode']:
        for line in maxfile_out['stdout'].splitlines():
            inode_fs = line.split()
            if re.search("^/vol", line) and len(inode_fs) > 2:
                iused = inode_fs[1]
                ifree = inode_fs[2]
                itotal = int(iused) + int(ifree)
                iused_cap = float(inode_fs[3].split('%')[0])

                counter_no = update_db(filer,volume,itotal,iused,ifree,iused_cap)
                if counter_no == None:
                    counter_no = 0

    return {'iused':iused, 'ifree': ifree, 'itotal': itotal, 'iused_cap': iused_cap, 'counter_no': counter_no}

def update_maxfiles(filer, volume, new_inode_count, counter_value):
    maxfiles_increase_command = "ssh storageops@{0} maxfiles {1} {2}".format(filer, volume, new_inode_count)
    run_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    maxfiles_increase_command_out = run_subcmd(maxfiles_increase_command)
    if not maxfiles_increase_command_out['returncode']:
        new_counter_value = counter_value + 1
        dbupdate_counter(filer, volume, new_counter_value, run_timestamp, new_inode_count)
    new_counter_value = counter_value + 1
    dbupdate_counter(filer, volume, new_counter_value, run_timestamp, new_inode_count)

def convert_html():
    html_data = get_db_info()
    print html_data
    fhand = open(out_file, 'w')
    fhand.write("""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        body {background-color: White ;}
        table {
        font-family: Calibri;
        border-collapse: collapse;
        width: 80%;
        font-size: 14px;
        white-space: nowrap
        }
        td, th {
        border: 1px solid Black;
        text-align: left;
        padding: 2px;
        white-space: nowrap
        }
        p.serif {
        font-family: "Times New Roman", Times, serif;
        }
        </style>
        </head>
        <body>""")
    fhand.write('<h3 style="color:blue;font-family:verdana;">NetApp inode management report</h3>')
    fhand.write('<table>\n<thead>\n<tr>\n<th>NetApp Filer</th>\n<th>Volume</th>\n<th>itotal</th>\n<th>iused</th>\n<th>ifree</th>\n<th>iCapacity</th>\n<th>counter</th>\n<th>log</th>\n</tr>\n</thead>\n')
    for html_line in html_data:
        cnt = html_line[-2]
        if cnt == None:
            cnt = 0

        if cnt >= counter_threshold:
            cnt = '<td bgcolor="#FF4136">{0}</td>'.format(cnt) #RED
        elif cnt < counter_threshold and cnt >= 3:
            cnt = '<td bgcolor="#FF851B">{0}</td>'.format(cnt) #ORANGE
        # elif cnt < 3 and cnt >= 0:
        #     cnt = '<td bgcolor="#e0ffff">{0}</td>'.format(cnt) #lightcyan
        else:
            cnt = '<td bgcolor="#01FF70">{0}</td>'.format(cnt) #LIME
        # write data to HTML File
        fhand.write('<tr>\n<td>{0}</td>\n<td>{1}</td>\n<td>{2}</td>\n<td>{3}</td>\n<td>{4}</td>\n<td>{5}</td>\n{6}\n<td>{7}</td></tr>'.format(html_line[0],html_line[1],html_line[2],html_line[3],html_line[4],html_line[5],cnt,html_line[7]))
        fhand.flush()
    else:
        fhand.write("""</table>\n<br><br><br>""")
        if len(exceeded_vol_list) > 0:
            fhand.write("""<p>the following volume inode usage crossed '90%' threshold value and auto incremented by '1%' for last 5 times, please review them</p><br>""")
            for line in exceeded_vol_list:
                fhand.write("""<p>{0}</p><br>""".format(line))

        fhand.write("""<i><p style="color:#111111;font-family:verdana;font-size:80%;">Script runtime: "{0:.2f}" Seconds<br><br>This is an automated report generated from host "dc1prmnnetapp2"<br><br>Thank you,<br><b><a  style="color:#0074D9;" href="mailto:gis.storage.operations@ADP.com">GIS Storage Operations</a></b><br>24/7 Storage Hotline:<b><span style="color:#FF4136;"> +1 844-758-3838 x1 </span></b> </p></i><br><br></body></html>""".format(time.time() - start_time))
        fhand.close()

def send_mail():
    with open(out_file) as myfile:
        myhtml = myfile.read()
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "NetApp inode management Report: {0}".format(today)
    #msg['From'] = "govardhan.sunkishela@adp.com"
    msg['To'] = "govardhan.sunkishela@adp.com"
    msg["Cc"] = "govardhan.sunkishela@adp.com,Ohm.Ramanathan@adp.com"
    msg['From'] = "GIS.Storage.Automation@ADP.com"
    #msg['To'] = "GIS.Storage.Operations.NAS@ADP.com"
    #msg["Cc"] = "Rittick.Mukherjee@ADP.com,Balaji.Vijayabalan@adp.com"
    # Create the body of the message (a plain-text and an HTML version).
    html = "{0}".format(myhtml)
    # mail_file = MIMEBase('application', 'csv')
    # mail_file.set_payload(open('/home/sunkishg/python/isilon/Isilon_exceeded_disk_quotas.csv', 'rb').read())
    # mail_file.add_header('Content-Disposition', 'attachment', filename='Isilon_exceeded_disk_quotas.csv')
    # Encoders.encode_base64(mail_file)
    # msg.attach(mail_file)
    # # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(html, 'html')
    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    # Send the message via local SMTP server.
    s = smtplib.SMTP('localhost')
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(msg["From"], msg["To"].split(",") + msg["Cc"].split(","), msg.as_string())
    s.quit()



def main():
    mount_db()
    inode_dict = get_inode_dfm()
    for volume,volume_info in inode_dict.iteritems():
        filer = volume_info.get('filer')
        maxfiles = get_maxfiles(filer,volume)
        free_inodes = int(maxfiles.get('ifree'))
        counter_val = int(maxfiles.get('counter_no'))
        if free_inodes < inode_threshold and counter_val < counter_threshold:
            print """Netapp filer {0} volume {1} inode usage crossed 90% \usage and available inodes are below 1000. increasing inode count by 1%""".format(filer, volume)
            total_inodes = maxfiles.get('itotal')
            #new_inode_count=int((.01*total_inodes)+total_inodes)
            new_inode_count=int((.02*total_inodes)+total_inodes)
            print "ssh storageops@{0} maxfiles {1}".format(filer, volume)
            print "ssh storageops@{0} maxfiles {1} {2}".format(filer, volume, new_inode_count)
            update_maxfiles(filer, volume, new_inode_count, int(maxfiles.get('counter_no')))
        elif free_inodes < inode_threshold and counter_val >= counter_threshold:
            exceeded_vol_list.append("{0},{1}".format(filer,volume))

    else:
        convert_html()
        send_mail()
        print "Script Complete Time: {0}".format(datetime.datetime.now())



if __name__ == '__main__':
    main()
    cur.close()
    conn.close()
quit()
