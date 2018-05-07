######################################################################################################################
#  Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://aws.amazon.com/asl/                                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import boto3
import json
import re
import os
import sys
import logging
import multiprocessing
import itertools
from functools import partial
from argparse import ArgumentParser
import time
import datetime
import codecs

account = ""
instanceNum = {}

def getInstances(region):
    ec2 = boto3.resource('ec2',region_name=region)
    json_result = []
    runningInstances = []
    #countInstance = []
    try:
        json_result = ec2.meta.client.describe_instances()

    except Exception as e:
        print(e)

    if "Reservations" in json_result:
        for reservation in json_result["Reservations"]:
            for instance in reservation["Instances"]:
                if instance["State"]["Name"] == "running":
                    instance["OwnerAccountId"] = account
                    runningInstances.append(instance)
                    #countInstance.append(instance["InstanceId"])

    return runningInstances

def getMetrics(intNow, startTime, endTime, period, statistics, unit, metrics, outputName, instance):
    global instanceNum
    instanceNum[instance["InstanceId"]] = 1
    res = ""
    output = {}
    for metric in metrics:
        args = {
            "dimensions": [{"Name": "InstanceId", "Value": instance["InstanceId"]}],
            "startTime": intNow - startTime,
            "endTime": intNow - endTime,
            "period": period,
            "statistics": [statistics],
            "metricName": metric,
            "namespace": "AWS/EC2",
            "unit": unit[metric]
        }
        logging.info("instance %s (%s)" % (instance["InstanceId"], len(instanceNum)))
        logging.info("metric %s" % (metric))

        numRetries = 0
        gettingMetrics = True
        while gettingMetrics:
        	try:
                    session = boto3.session.Session(region_name=instance["Placement"]["AvailabilityZone"][:-1])
                    cloudwatch = session.resource('cloudwatch')
                    json_result = cloudwatch.meta.client.get_metric_statistics(Dimensions=args['dimensions'],
                                                                       StartTime=datetime.datetime.fromtimestamp(args['startTime']/1e3).strftime("%Y-%m-%d %H:%M:%S"),
                                                                       EndTime=datetime.datetime.fromtimestamp(args['endTime']/1e3).strftime("%Y-%m-%d %H:%M:%S"),
                                                                       Period=args['period'],
                                                                       Statistics=args['statistics'],
                                                                       MetricName=args['metricName'],
                                                                       Namespace=args['namespace'],
                                                                       Unit=args['unit'])
                    gettingMetrics = False
        	except Exception as e:
                    numRetries+=1
                    logging.error("Getting CW metric %s try %s of 3" % (args['metricName'], numRetries))
                    logging.error("Exception: %s" % (e))
                    if numRetries > 3:
                        gettingMetrics = False
                        raise
                    time.sleep(1)

        #logging.info("metric_stats %s" % (json_result))
        for datapoint in json_result['Datapoints']:
            try:
                if(str(datapoint['Timestamp']) in output):
                    output[str(datapoint["Timestamp"])][metric] = datapoint[statistics]
                else:
                    readableTimeStamp = datapoint['Timestamp']
                    readableInstanceLaunchTime = instance["LaunchTime"]
                    tagString = ""
                    ebsString = ""

                    if instance.get('Tags',"None") <> "None":
                        for tag in instance["Tags"]:
                            tagString += re.sub('[^a-zA-Z0-9-_ *.]', '', tag["Key"].replace(",", " ")) + ":" + re.sub('[^a-zA-Z0-9-_ *.]', '', tag["Value"].replace(",", " ")) + " | "
                        tagString = tagString[:-3]
                    if instance["BlockDeviceMappings"]:
                        for ebs in instance["BlockDeviceMappings"]:
                            ebsString += ebs["Ebs"]["VolumeId"] + " | "
                        ebsString = ebsString[:-3]

                    output[str(datapoint['Timestamp'])] = {
                        "humanReadableTimestamp": readableTimeStamp,
                        "timestamp": datapoint['Timestamp'],
                        "accountId": instance["OwnerAccountId"],
                        "az": instance["Placement"]["AvailabilityZone"],
                        "instanceId": instance["InstanceId"],
                        "instanceType": instance["InstanceType"],
                        "instanceTags": tagString,
                        "ebsBacked": True if instance["RootDeviceType"] == "ebs" else "false",
                        "volumeIds": ebsString,
                        "instanceLaunchTime": instance["LaunchTime"],
                        "humanReadableInstanceLaunchTime": readableInstanceLaunchTime,
                        metric: datapoint[statistics]
                    }
            except Exception as e:
                print(e)

    for row in output:
       res += u"\"{0}\",\"{1}\",\"{2}\",\"{3}\",\"{4}\",\"{5}\",\"{6}\",\"{7}\",\"{8}\",\"{9}\",\"{10}\",\"{11}\",\"{12}\",\"{13}\",\"{14}\",\"{15}\"\n".format(\
                                                                            output[row].setdefault("humanReadableTimestamp",""),\
                                                                            output[row].setdefault("timestamp",""),\
                                                                            output[row].setdefault("accountId",""),\
                                                                            output[row].setdefault("az",""),\
                                                                            output[row].setdefault("instanceId",""),\
                                                                            output[row].setdefault("instanceType",""),\
                                                                            output[row].setdefault("instanceTags",""),\
                                                                            output[row].setdefault("ebsBacked",""),\
                                                                            output[row].setdefault("volumeIds",""),\
                                                                            output[row].setdefault("instanceLaunchTime",""),\
                                                                            output[row].setdefault("humanReadableInstanceLaunchTime",""),\
                                                                            output[row].setdefault("CPUUtilization","0"),\
                                                                            output[row].setdefault("NetworkIn","0"),\
                                                                            output[row].setdefault("NetworkOut","0"),\
                                                                            output[row].setdefault("DiskReadOps","0"),\
                                                                            output[row].setdefault("DiskWriteOps","0"))
    return res

# Main
def download_metrics(p_region, p_account, p_mode, p_statistics, p_period, p_starttime, p_endtime, p_output):

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')

    region = p_region
    account = p_account
    mode = p_mode
    statistics = p_statistics
    period = p_period
    startTime = p_starttime
    endTime = p_endtime
    outputName = p_output


    metrics = ['NetworkIn', 'NetworkOut', 'DiskReadOps', 'DiskWriteOps', 'CPUUtilization'];

    unit = {
        'CPUUtilization': 'Percent',
        'NetworkIn': 'Bytes',
        'NetworkOut': 'Bytes',
        'DiskReadOps': 'Count',
        'DiskWriteOps': 'Count'
    }

    intNow = int(time.time()*1000)

    logging.info("region %s " % (region))
    logging.info("account %s " % (account))
    logging.info("mode %s " % (mode))
    logging.info("statistics %s " % (statistics))
    logging.info("period %s " % (period))
    logging.info("time %s " % (startTime))
    logging.info("endtime %s " % (endTime))
    logging.info("metrics %s " % (metrics))
    logging.info("unit %s " % (unit))
    logging.info("now %s " % (intNow))
    logging.info("startTime %s " % (intNow - startTime))
    logging.info("endTime %s " % (intNow - endTime))
    logging.info("output %s " % (outputName))

    outfile = codecs.open(outputName, 'a', encoding='utf-8')

    if (p_mode == 'single'):
        accounts = p_account
    else:
        logging.error('Mode is not correct')

    p = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
    func = partial(getMetrics, intNow, startTime, endTime, period, statistics, unit, metrics, outputName)
    response = p.map(func, getInstances(region[0]))
    p.close()
    p.join()

    for line in response:
        outfile.write(line)
    outfile.close()
