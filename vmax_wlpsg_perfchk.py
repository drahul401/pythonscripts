#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
"""vmax_wlpsg_perfchk.py: list storage groups that exceeded bw_limit threshold (Host MB/s) """
__author__      = "Sunkishela Govardhan (CORP)"
__email__ = "Govardhan.Sunkishela@ADP.com"

# python modules
import sys
import json
import time
from pprint import pprint
import requests
import datetime
import operator
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

days_ago = 7
threshold_mbs = 1300

user = 'smc'
password = 'smc'

unisphere_dict = {
    "000196701605" : "7.10.254.80",
    "000196701606" : "7.10.254.80",
    "000196701609" : "7.6.254.91",
    "000196701610" : "7.10.254.80",
    "000196701611" : "7.10.254.80",
    "000196701612" : "7.6.254.91",
    "000196701613" : "7.6.254.91",
    "000196702080" : "7.6.254.91",
    "000197801053" : "7.10.250.5",
    "000197801059" : "7.6.251.6",
    "000197801060" : "7.6.251.6",
    "000197801066" : "7.6.251.6",
    "000197801067" : "7.10.250.5",
    "000197801068" : "7.10.250.5",
    "000197801069" : "7.10.250.5",
    "000197801071" : "7.6.251.6",
    "000196701608": "10.3.218.40"
}

# get timestamps
def epoch_time_ms_now():
    return int(time.time() * 1000)

def epoch_time_days_ago(days=1):
    return int(epoch_time_ms_now() - (days * 24 * 3600 * 1000))

def epoch_time_to_human(timestamp):
    return datetime.datetime.fromtimestamp(timestamp/1000).strftime('%c')

#Unisphere Rest API Calls
def vmax_rest_post(unisphere_ip, rest_uri, request_obj):
    # config the rest URL
    rest_url  = 'https://{0}:8443/univmax/restapi{1}'.format(unisphere_ip, rest_uri)
    # set header
    header = { 'content-type' : 'application/json',
               'accept'       : 'application/json' }

    # Post data
    try:
        response = requests.post(rest_url,
                                 data=json.dumps(request_obj),
                                 auth=(user, password),
                                 headers=header,
                                 verify=False)
    except Exception as e:
        pprint("Error to connect to Unisphere Rest API: {0}\nResponse code: {1}".format(e, response.status_code))

    # check response
    if response.status_code != 200:
        pprint("Error to perform POST operation on unisphere.\nrest_path: {0}\nRest API status_code: {1}\nError text: {2}".format(rest_url, response.status_code, response.text))

    # Return json data
    return json.loads(response.text)

def vmax_restapi_get(unisphere_ip, rest_uri):
    rest_url  = 'https://{0}:8443/univmax/restapi{1}'.format(unisphere_ip, rest_uri)
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
def list_vmax(unisphere_ip):
    vmax_list = list()
    # This call queries for a list of Authorized Symmetrix Ids compatible with SLO provisioning
    rest_uri = "/sloprovisioning/symmetrix"
    response = vmax_restapi_get(unisphere_ip, rest_uri)
    for sid in response['symmetrixId']:
        symmetrixId = list_vmax_details(unisphere_ip, sid)
        if not symmetrixId is None:
            vmax_list.append(symmetrixId)
    return vmax_list

def list_vmax_details(unisphere_ip, sid):
    #This call queries for a specific Authorized Symmetrix Object that is compatible with slo provisioning using its ID
    rest_uri = "/sloprovisioning/symmetrix/{0}".format(sid)
    response = vmax_restapi_get(unisphere_ip, rest_uri)
    if str(response['symmetrix'][0]['local']).lower() == 'true':
        return str(response['symmetrix'][0]['symmetrixId'])

def list_wlpsg(unisphere_ip, sid):
    #This call returns all WLP-eligible storage groups on an array.
    wlpsg_list = list()
    rest_uri = "/wlp/symmetrix/{0}/storagegroup".format(sid)
    response = vmax_restapi_get(unisphere_ip, rest_uri)
    for wlpsg_info in response['symWorkloadSummary']:
        wlpsg_list.append(wlpsg_info['workloadName'])
    return wlpsg_list

def wlpsg_performance(unisphere_ip, sid, wlpsg):
    # The call queries a list of performance data for a specific storage groups and specific metrics at a specific time ranges.
    rest_uri = "/performance/StorageGroup/metrics"
    start_time = epoch_time_days_ago(days_ago)
    # Performance payload
    request_obj = {'symmetrixId': sid, "endDate": epoch_time_ms_now(), "startDate": start_time, "storageGroupId": wlpsg, "metrics": ["HostMBs"], "dataFormat": "Average" }

    response = vmax_rest_post(unisphere_ip, rest_uri, request_obj)
    metrics = response["resultList"]["result"]
    return metrics

def main():
    unisphere_info_dict = dict()
    for sid,unisphere_ip in unisphere_dict.items():
        unisphere_info_dict.setdefault(unisphere_ip,list()).append(sid)
    perf_results = dict()
    for unisphere_ip,sid_list in unisphere_info_dict.items():
        vmax_list = list_vmax(unisphere_ip)
        print vmax_list
        for sid in sid_list:
            if sid in vmax_list:
                perf_results[sid] = dict()
                wlpsg_list = list_wlpsg(unisphere_ip, sid)
                for wlpsg in wlpsg_list:
                    wlpsg_perf_data = wlpsg_performance(unisphere_ip, sid, wlpsg)
                    threshold_hostmbs = [data['HostMBs'] for data in wlpsg_perf_data if data['HostMBs'] >= threshold_mbs]
                    threshold_hostmbs_count = len(threshold_hostmbs)
                    if threshold_hostmbs_count > 0:
                        threshold_list = [data for data in wlpsg_perf_data if data['HostMBs'] >= threshold_mbs]
                        max_index, max_value = max(enumerate(threshold_hostmbs), key=operator.itemgetter(1))
                        wlpsg_perf_metric = threshold_list[max_index]
                        wlpsg_perf_metric['timestamp'] = epoch_time_to_human(wlpsg_perf_metric['timestamp'])
                        perf_results[sid][wlpsg] = {'exceeded_count': threshold_hostmbs_count, 'highest_threshold': wlpsg_perf_metric}
                        print "SID: {0}, SG: {1}, exceeded_count: {2}, highest_threshold:{3}".format(sid, wlpsg, threshold_hostmbs_count, wlpsg_perf_metric)

    pprint(perf_results)
    fhand = open("perf_results.JSON", 'w')
    perf_results_dump = json.dumps(perf_results)
    fhand.write(perf_results_dump)
    fhand.close()

if __name__ == '__main__':
    main()
