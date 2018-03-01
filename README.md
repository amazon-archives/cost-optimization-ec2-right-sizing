# AWS Cost Optimization: EC2 Right Sizing
Source code for the AWS solution "Cost Optimization: EC2 Right Sizing". Please see the main solution for the [Cost Optimization: EC2 Right Sizing](https://aws.amazon.com/answers/account-management/cost-optimization-ec2-right-sizing/).

## Cloudformation template

- cost-optimization-ec2-right-sizing.template

You will need to replace %%BUCKET_NAME%% in the template to point to the bucket where you put your own copies of the Python source code below.

## Python source code

- callgcw.py
- deleteandterminate.py
- getcloudwatchmetrics.py
- run-rightsizing-redshift.py

## Troubleshooting
Log files are exported to the CloudWatch Logs log group cost-optimization-ec2-right-sizing, log streams:
{instance_id}/cfn-init.log
{instance_id}/run-rightsizing-redshift.log
{instance_id}/deleteandterminate.log

Log files are also located locally on the solution created EC2 instance (if you chose to not terminate resources):
/var/log/cfn-init.log
/tmp/run-rightsizing-redshift.log
/tmp/deleteandterminate.log



***

Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/asl/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
