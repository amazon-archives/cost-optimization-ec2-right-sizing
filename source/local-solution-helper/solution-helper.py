######################################################################################################################  
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #  
#                                                                                                                    #  
#  Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except in compliance     #  
#  with the License. A copy of the License is located at                                                             #  
#                                                                                                                    #  
#      http://www.apache.org/licenses/                                                                               #  
#                                                                                                                    #  
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #  
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #  
#  and limitations under the License.                                                                                #  
###################################################################################################################### 

import os
import string
import ast
import crypt
import logging
import uuid
import json
import datetime
import re
import urllib
from pycfn_custom_resource.lambda_backed import CustomResource

log = logging.getLogger()
log.setLevel(logging.INFO)

def SendAnonymousData(AnonymousData):
    log.info("Sending anonymous data")
    TimeNow = datetime.datetime.utcnow().isoformat()
    TimeStamp = str(TimeNow)
    AnonymousData['TimeStamp'] = TimeStamp
    data = json.dumps(AnonymousData)
    log.info("Data: %s", data)
    data_utf8 = data.encode('utf-8')
    url = 'https://metrics.awssolutionsbuilder.com/generic'
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'content-length': len(data_utf8)
    }
    req = urllib.request.Request(url, data_utf8, headers)
    rsp = urllib.request.urlopen(req)
    rspcode = rsp.getcode()
    content = rsp.read()
    log.info("Response from APIGateway: %s, %s", rspcode, content)
    return data

def createRandomPassword(pwdLength=13, specialChars="True"):
    log.info("Creating random password")
    if specialChars is None:
        specialChars = "True"
    # Generate new random password
    chars = string.ascii_letters + string.digits
    if specialChars == "True":
        chars += '#$%^&+='
        p=re.compile('^(?=.{1,})(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])(?=.*[#$%^&+=]).*$')
    else:
        p=re.compile('^(?=.{1,})(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z]).*$')
    numTries = 0
    pwdFound = False
    while not pwdFound:
        password = ''
        numTries += 1
        for i in range(int(pwdLength)):
            password += chars[ord(os.urandom(1)) % len(chars)]
        m=p.match(password)
        if m is not None:
            pwdFound = True
    log.info("Password created after %s tries", numTries)
    log.debug("%s", password)
    return password


def createUniqueID():
    log.info("Creating Unique ID")
    # Generate new random Unique ID
    uniqueID = uuid.uuid4()
    log.debug("UUID: %s", uniqueID)
    return uniqueID


def md5hash(value, salt):
    return crypt.crypt(value, '$1$' + salt)


class myCustomResource(CustomResource):
    def __init__(self, event):
        super(myCustomResource, self).__init__(event)

    def create(self):
        try:
            FunctName = self._resourceproperties.get('FunctionName')
            FunctArn = self._resourceproperties.get('LambdaArn')
            CreateRandomPassword = self._resourceproperties.get('CreateRandomPassword')
            CreateUniqueID = self._resourceproperties.get('CreateUniqueID')
            SendData = self._resourceproperties.get('SendAnonymousData')
            response = None

            if SendData is not None:
                log.debug("Sending Data: %s", SendData)
                SendData = ast.literal_eval(SendData)
                SendData['Data'].update({'CFTemplate': 'Created'})
                data = SendAnonymousData(SendData)
                response = {"Status": "SUCCESS", "Data": str(data)}
                log.debug("%s", response)

            if CreateRandomPassword is not None:
                # Expect value of CreateRandomPassword to be the desired password length
                password = createRandomPassword(CreateRandomPassword, self._resourceproperties.get('RandomPasswordSpecialCharacters'))
                response = {"Status": "SUCCESS", "Password": password}

            if CreateUniqueID is not None:
                # Value of CreateUniqueID does not matter
                newID = createUniqueID()
                response = {"Status": "SUCCESS", "UUID": str(newID)}
                log.debug("%s", response)

            if response is None:
                response = {"Status": "SUCCESS"}

            # Results dict referenced by GetAtt in template
            return response

        except Exception as e:
            log.error("Create exception: %s", e)
            return {"Status": "FAILED", "Reason": str(e)}

    def update(self):
        try:
            FunctName = self._resourceproperties.get('FunctionName')
            FunctArn = self._resourceproperties.get('LambdaArn')
            # S3Event = self._resourceproperties.get('S3Event')
            SendData = self._resourceproperties.get('SendAnonymousData')

            response = None

            if SendData is not None:
                log.debug("Sending Data: %s", SendData)
                SendData = ast.literal_eval(SendData)
                SendData['Data'].update({'CFTemplate': 'Updated'})
                SendAnonymousData(SendData)
                response = {"Status": "SUCCESS", "Data": str(SendData)}
                log.debug("%s", response)

            if response is None:
                response = {"Status": "SUCCESS"}

            # Results dict referenced by GetAtt in template
            return response

        except Exception as e:
            log.error("Update exception: %s", e)
            return {"Status": "FAILED", "Reason": str(e)}

    def delete(self):
        try:
            FunctName = self._resourceproperties.get('FunctionName')
            # CreateSshKey = self._resourceproperties.get('CreateSshKey')
            SendData = self._resourceproperties.get('SendAnonymousData')

            log.info("Delete called, cleaning up")

            if SendData is not None:
                log.debug("Sending Data: %s", SendData)
                SendData = ast.literal_eval(SendData)
                SendData['Data'].update({'CFTemplate': 'Deleted'})
                data = SendAnonymousData(SendData)
                response = {"Status": "SUCCESS", "Data": str(data)}
                log.debug("%s", response)

            return {"Status": "SUCCESS"}

        # Delete operations do not return result data
        except Exception as e:
            log.error("Delete exception: %s -- %s", FunctName, e)
            return {"Status": "FAILED", "Reason": str(e)}


def lambda_handler(event, context):
    resource = myCustomResource(event)
    resource.process_event()
    return {'message': 'done'}
