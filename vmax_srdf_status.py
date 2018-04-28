#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
"""vmax_srdf_status.py: Reports DELLEMC Vmax SRDF Status from all Symmetrix arrays"""

__author__      = "Sunkishela Govardhan (CORP)"


# Import Python modules
import os
import sys
import json
import time
import smtplib
import requests
from pprint import pprint
from datetime import datetime
from socket import gethostname
from email import Encoders
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email.mime.multipart import MIMEMultipart
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

server_name = gethostname()
dir_path = os.path.dirname(os.path.realpath(__file__))
out_file = os.path.join(dir_path, 'srdf_report.html')
vmax_srdf_out = os.path.join(dir_path, 'vmax_srdf_status.JSON')

# Today"s date
start_time = time.time()
date_time = datetime.now().strftime("%A %b %d %Y %I:%M %p")

# Authentication
user = 'smc'
password = 'smc'

unisphereip_list = ["7.4.7.20", "7.8.7.20", "7.10.254.80", "7.6.254.91", "7.10.250.5","7.6.251.6", "10.3.218.40"]

#Unisphere Rest API Calls
def vmax_restapi_get(unisphereip, rest_uri):
    rest_url  = 'https://{0}:8443/univmax/restapi{1}'.format(unisphereip, rest_uri)
    # set header
    headers = { 'content-type' : 'application/json',
                'accept'       : 'application/json' }

    # Get data
    try:
        response = requests.get(rest_url,
                                auth=(user, password),
                                headers=headers,
                                verify=False)
    except Exception as e:
        pprint("Error to connect to Unisphere Rest API: {0}\nResponse code: {1}".format(e, response.status_code))

    # check response
    if response.status_code != 200:
        pprint("Error to perform POST operation on unisphere.\nrest_path: {0}\nRest API status_code: {1}\nError text: {2}".format(rest_url, response.status_code, response.text))

    # Return json data
    return json.loads(response.text)

# VMAX Calls
def list_vmax(unisphereip):
    vmax_list = list()
    # This call queries for Symmetrix IDs
    rest_uri = "/83/replication/symmetrix"
    response = vmax_restapi_get(unisphereip, rest_uri)
    for sid in response['symmetrixId']:
        symmetrixId = list_vmax_details(unisphereip, sid)
        if not symmetrixId is None:
            vmax_list.append(symmetrixId)
    return vmax_list

def list_vmax_details(unisphereip, sid):
    #This call queries for a specific Authorized Symmetrix Object that is compatible with slo provisioning using its ID
    rest_uri = "/system/symmetrix/{0}".format(sid)
    response = vmax_restapi_get(unisphereip, rest_uri)
    if str(response['symmetrix'][0]['local']).lower() == 'true':
        return str(response['symmetrix'][0]['symmetrixId'])

def list_rdf_group(unisphereip, sid):
    rdfgnumbers_list = list()
    # This call queries for list of SRDF group labels
    rest_uri = "/83/replication/symmetrix/{0}/rdf_group".format(sid)
    response = vmax_restapi_get(unisphereip, rest_uri)
    if len(response['rdfGroupID']) > 0:
        for rdfgnumber in response["rdfGroupID"]:
            rdfgnumbers_list.append(rdfgnumber["rdfgNumber"])

    return rdfgnumbers_list

def list_rdf_group_volume(unisphereip, sid, rdfgnumber):
    # list of volume names in the RDFG
    rest_uri = "/83/replication/symmetrix/{0}/rdf_group/{1}/volume".format(sid, rdfgnumber)
    response = vmax_restapi_get(unisphereip, rest_uri)
    return response

def get_rdf_pair_info(unisphereip, sid, rdfgnumber, tdevname):
    #the pair details for the volume for this RDFG
    rest_uri = "/83/replication/symmetrix/{0}/rdf_group/{1}/volume/{2}".format(sid, rdfgnumber, tdevname)
    response = vmax_restapi_get(unisphereip, rest_uri)
    return response

def get_tdev_sginfo(unisphereip, sid, tdevname):
    #This call queries for a specified Volume on a specified Symmetrix Array
    rest_uri = "/83/sloprovisioning/symmetrix/{0}/volume/{1}".format(sid, tdevname)
    response = vmax_restapi_get(unisphereip, rest_uri)
    try:
        sg_list = response['volume'][0]['storageGroupId']
    except:
        sg_list = list()

    if len(sg_list) > 0:
        for sg in sorted(sg_list, reverse=True):
            if 'srdf' in sg.lower():
                sg_name = sg
                break
            else:
                continue
        else:
            if not 'sg_name' in locals():
                sg_list = [x for x in sg_list if not 'snap' in x]
                sg_name = sorted(sg_list)[0]
    else:
        sg_name = "None"

    return sg_name

def create_html(srdf_dict, out_file):
    fhand = open(out_file, 'w')
    fhand.write("""
<!DOCTYPE html>
<html>
<head>
<style>
body {background-color: #FFFFFF ;}
table {
        font-family: Calibri;
        border-collapse: collapse;
        width: 50%;
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
<body>
<h3 style="color:#0074D9;font-family:verdana;">Vmax3 SRDF Report</h3>
<table>
<thead>
<tr>
<th>Symmetrix ID</th>
<th>RDF Group</th>
<th>RDF Mode</th>
<th>RDF Pair State</th>
<th>Storage Group</th>
</tr>
</thead>
        """)

    for symmetrix in sorted(list(srdf_dict.keys())):
        rdf_data = srdf_dict.get(symmetrix)
        if len(rdf_data) > 0:
            for rdfg in sorted(list(rdf_data.keys())):
                rdf_info = rdf_data.get(rdfg, dict())
                rdfMode = rdf_info.get('rdfMode', 'None')
                rdfpairState = rdf_info.get('rdfpairState', 'None')
                storagegroup = rdf_info.get('storagegroup', 'None')

                if rdfMode == 'Asynchronous':
                    rdfMode = '<td bgcolor="#FFFFFF">{0}</td>'.format(rdfMode)  # WHITE
                else:
                    rdfMode = '<td bgcolor="#FFDC00">{0}</td>'.format(rdfMode) #YELLOW

                if rdfpairState == 'Consistent':
                    rdfpairState = '<td bgcolor="#FFFFFF">{0}</td>'.format(rdfpairState)  # WHITE
                else:
                    rdfpairState = '<td bgcolor="#FFDC00">{0}</td>'.format(rdfpairState)  # YELLOW

                fhand.write('<tr>\n<td>{0}</td>\n<td>{1}</td>\n{2}\n{3}\n<td>{4}</td>\n</tr>'.format(symmetrix, rdfg, rdfMode, rdfpairState, storagegroup))
            else:
                fhand.flush()
    else:
        fhand.write("""</table>\n<br><br><br><p><strong>Various Pair Status:</strong><br><br><b>Synchronized.  </b>  R1 and R2s are in synchronized state, and both have same content with no invalid tracks between R1/R2.<br><b>SyncInProg.  </b>  Synchronization is under way between R1 and R2 because there are invalid tracks between R1/R2.<br><b>Consistent.  </b>  Same as Synchronized but for SRDF/A devices.<br><b>Transmit Idle.  </b>  SRDF/A can not push the data in the transmit cycle because the link is down.<br><b>Split.  </b>  Both R1 and R2 are RW available to their respective hosts, but the link is not ready and no data is being transferred between R1/R2.<br><b>R1 Updated.  </b>  R1s are WD, and have no invalid tracks. The link is RW.<br><b>R1 UpdInProg.  </b>  R1s are WD, and have invalid tracks, data is being copied from R2 to R1, and the link is RW.<br><b>Failed Over.  </b>  R1 is WD and R2 is RW. No data is being transferred between R1/R2.<br><b>Partitioned.  </b> SYMAPI can not communicate with the remote Symmetrix to show correct status.<br><b>Suspended.  </b>  No data is being transferred between R1/R2. IOs on R1 will accumulate as invalid tracks and will be transmitted to R2 upon resumption of the link.<br><b>Mixed.  </b>  A SRDF group has devices with more than one pair status.<br><b>Invalid.  </b>  Default state when no other SRDF state applies.</p>""")
        diffrence_time = time.time() - start_time
        fhand.write("""<i><p style="color:#111111;font-family:verdana;font-size:80%;">Script runtime: "{0:.2f}" Seconds<br><br>This is an automated report generated from host "{1}"<br><br></p></i><br><br></body></html>""".format(diffrence_time, server_name))
        fhand.flush()
    fhand.close()

def send_mail(out_file):
    with open(out_file) as myfile:
        myhtml = myfile.read()
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Vmax3 SRDF Report: {0}".format(date_time)
    #msg['From'] = "govardhan.sunkishela@adp.com"
    msg['To'] = "govardhan.sunkishela@adp.com"
    msg["Cc"] = "govardhan.sunkishela@adp.com"
    msg['From'] = "GIS.Storage.Automation@ADP.com"
    # msg['To'] = "GIS.Storage.Operations@ADP.com"
    # msg["Cc"] = "Rittick.Mukherjee@ADP.com,Balaji.Vijayabalan@adp.com"
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
    s = smtplib.SMTP('dc1prrelay1.ga.adp.com')
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(msg["From"], msg["To"].split(",") + msg["Cc"].split(","), msg.as_string())
    s.quit()

def main():
    srdf_summary = dict()
    for unisphereip in set(unisphereip_list):
        symmetrix_arrays = list_vmax(unisphereip)
        for sid in set(symmetrix_arrays):
            srdf_summary[sid] = dict()
            rdf_group_list = list_rdf_group(unisphereip, sid)
            if len(rdf_group_list) > 0:
                for rdf_group in rdf_group_list:
                    rdf_group_tdevs = list_rdf_group_volume(unisphereip, sid, rdf_group)
                    if rdf_group_tdevs["numVolumes"] > 0:
                        for tdevname in rdf_group_tdevs["name"]:
                            tdevinfo = get_rdf_pair_info(unisphereip, sid, rdf_group, tdevname)
                            if tdevinfo["volumeConfig"] == 'RDF1+TDEV':
                                srdf_sg_name= get_tdev_sginfo(unisphereip, sid, tdevname)
                                srdf_summary[sid][rdf_group] = {'rdfMode': tdevinfo["rdfMode"],  'rdfpairState': tdevinfo["rdfpairState"], 'storagegroup': srdf_sg_name}
                                print "{0}, {1}, {2}, {3}, {4}".format(sid, rdf_group, tdevinfo["rdfMode"], tdevinfo["rdfpairState"], srdf_sg_name)
                                break
                            else:
                                break
    else:
        create_html(srdf_summary, out_file)
        send_mail(out_file)

    fhand = open(vmax_srdf_out, 'w')
    vmax_srdf_dump = json.dumps(srdf_summary)
    fhand.write(vmax_srdf_dump)
    fhand.close()

if __name__ == '__main__':
    main()
