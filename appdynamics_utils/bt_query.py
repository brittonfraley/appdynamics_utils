#!/usr/bin/env python

"""
This script retrieves business transaction metrics from AppDynamics via the metric and snapshot API. 
Query is coded to return 'BEFORE_NOW' with a 'duration_in_mins' as a parameter. 

Output is delimited text and can be sent to a file via:
    bt_query.py 10080 > output.txt
    
Edit configuration in appdynamics_config.py and place in the same directory as this script.
"""

from datetime import datetime
import json
import sys
import time
import traceback
import urllib2

import appdynamics_config as config

__author__ = 'Britton Fraley'
__email__ = 'brittonfraley@gmail.com'

APPD_CONTROLLER_PATH = '/controller/rest/applications/'
APPD_API_PATH = '/metric-data?metric-path=Business%20Transaction%20Performance%7CBusiness%20Transactions%7C'
APPD_METRIC_NAME_CALLS_PER_MINUTE = 'Calls per Minute'
APPD_METRIC_NAME_AVERAGE_RESPONSE_TIME = 'Average Response Time (ms)'
APPD_METRIC_NAME_NORMAL_AVERAGE_RESPONSE_TIME = 'Normal Average Response Time (ms)'
APPD_METRIC_NAME_SLOW_CALLS = 'Number of Slow Calls'
APPD_METRIC_NAME_VERY_SLOW_CALLS = 'Number of Very Slow Calls'
APPD_METRIC_NAME_ERRORS_PER_MINUTE = 'Errors per Minute'
APPD_METRIC_NAME_STALL_COUNT = 'Stall Count'
APPD_METRIC_NAME_AVERAGE_CPU_USED = 'Average CPU Used (ms)'
APPD_METRIC_NAME_AVERAGE_BLOCK_TIME = 'Average Block Time (ms)'
APPD_METRIC_NAME_AVERAGE_WAIT_TIME = 'Average Wait Time (ms)'
APPD_TRANSACTION = 'Transaction'

ART_MIN = 'Minimum Response Time (ms)'
ART_MAX = 'Maximum Response Time (ms)'
CPM_SUM = 'Total Calls'
EPM_SUM = 'Total Errors'

DELIMITER = ','
LINE_FORMAT = (APPD_TRANSACTION, 
            APPD_METRIC_NAME_AVERAGE_RESPONSE_TIME, ART_MIN, ART_MAX, 
            APPD_METRIC_NAME_NORMAL_AVERAGE_RESPONSE_TIME, APPD_METRIC_NAME_CALLS_PER_MINUTE, CPM_SUM, 
            APPD_METRIC_NAME_ERRORS_PER_MINUTE, EPM_SUM, APPD_METRIC_NAME_SLOW_CALLS, 
            APPD_METRIC_NAME_VERY_SLOW_CALLS, APPD_METRIC_NAME_STALL_COUNT, APPD_METRIC_NAME_AVERAGE_CPU_USED, 
            APPD_METRIC_NAME_AVERAGE_BLOCK_TIME, APPD_METRIC_NAME_AVERAGE_WAIT_TIME)


class Error(Exception):
    """Base class for exceptions"""
    pass
    
class NetworkError(Error):
    """Error for network i/o"""

    def __init__(self, code, url):
        self.stack_trace = traceback.format_exc()
        self.expression = url
        self.description = 'http error ' + str(code) + ' on \'' + self.expression + '\''

                
def url_retrieve(url, user, password):
    
    try:
        manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, url, user, password)
        auth = urllib2.HTTPBasicAuthHandler(manager)
        opener = urllib2.build_opener(auth)
        urllib2.install_opener(opener)
        response = urllib2.urlopen(url)
        d = response.read()
    except urllib2.HTTPError as e:
        raise NetworkError(e.code, url)
    return d
        
def appd_to_dict(s):
    """Returns a dict from AppDynamics JSON string"""
        
    transactions = dict()
    d = json.loads(s)     
    for i in d:
        path = i['metricPath'].split('|')
        tier = path[2]
        transaction = path[3]
        metric = path[4]
        if len(i['metricValues']) == 1:
            value = i['metricValues'][0]['value']
            sum = i['metricValues'][0]['sum']   
            min = i['metricValues'][0]['min'] 
            max = i['metricValues'][0]['max']
            if transaction not in transactions:
                transactions[transaction] = dict()    
            transactions[transaction][metric] = value 
            if metric == APPD_METRIC_NAME_AVERAGE_RESPONSE_TIME:
                transactions[transaction][ART_MIN] = min
                transactions[transaction][ART_MAX] = max 
            elif metric == APPD_METRIC_NAME_CALLS_PER_MINUTE:
                transactions[transaction][CPM_SUM] = sum
            elif metric == APPD_METRIC_NAME_ERRORS_PER_MINUTE:
                transactions[transaction][EPM_SUM] = sum
    return transactions 

def dict_to_text(transactions):
    """Returns a delimited text file from dict"""
        
    header = ''
    for i in LINE_FORMAT:
        header += i
        if LINE_FORMAT.index(i) != len(LINE_FORMAT) -1:
            header += DELIMITER
    output = header + '\n'
    for transaction in sorted(transactions):
        line_items = dict()
        line_items[APPD_TRANSACTION] = transaction
        metrics = transactions[transaction]
        for metric in sorted(metrics):
            value = str(metrics[metric])
            if metric in LINE_FORMAT:
                line_items[metric] = value
        line_txt = ''
        for i in LINE_FORMAT:
            if i in line_items:
                line_txt += line_items[i]
            if LINE_FORMAT.index(i) != len(LINE_FORMAT) -1:
                line_txt += DELIMITER
        output += line_txt + '\n'
    return output
        
def util_timestamp():
    """Return a timestamp string"""
 
    # return as YYYYY-MM-DD HH:MM:SS.MMMMMM
    ct = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + ' ' + time.strftime('%Z')
    return ct
    
def util_error(f, location, message):
    """Write a short error message"""

    t = util_timestamp() + ', ' + location + ': ' + message + '\n'
    f.write(t)
    return


if __name__ == '__main__':

    f_error = sys.stderr
    function = 'main'
    
    duration = sys.argv[1]
    url = '{0}{1}{2}{3}{4}%7C*%7C*&time-range-type=BEFORE_NOW&duration-in-mins={5}&output=JSON'.format(
        config.appd_auth['controller'], APPD_CONTROLLER_PATH, config.APPD_APP, 
        APPD_API_PATH, config.APPD_TIER, duration)
    login = '{0}@{1}'.format(config.appd_auth['user'], config.appd_auth['account'])
    try:
        d = url_retrieve(url, login, config.appd_auth['password'])
        transactions = appd_to_dict(d)
        output = dict_to_text(transactions)
        sys.stdout.write(output)
        sys.exit(0)
    except Error as e: 
        util_error(f_error, function, e.description)
        sys.exit(1)
