#!/usr/bin/python

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


import boto.utils, boto3
import logging

CW_REGION = "cfn_region"
DB_CLID = "cfn_db_clusteridentifier"
# Main
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')

    logging.info("Deleting the redshift cluster")
    rs = boto3.client('redshift',CW_REGION)
    response = rs.delete_cluster(ClusterIdentifier=DB_CLID,SkipFinalClusterSnapshot=True)

    logging.info("Terminating the EC2 instance")
    ec2 = boto3.resource('ec2',CW_REGION)
    instanceid = boto.utils.get_instance_metadata()['instance-id']
    instance = ec2.Instance(instanceid)
    response = instance.terminate(DryRun=False)
