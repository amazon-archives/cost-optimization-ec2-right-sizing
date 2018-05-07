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
#
# v1.0 initial version - AWS Solutions Builders
# v1.1 fix f1.2xlarge zero price issue - AWS Solutions Builders
#
######################################################################################################################

import psycopg2
import math
import string, os, sys
import csv
import random
import boto3
import platform
import linecache
import logging
import urllib

#Global variables
CURRENTOS = platform.system()
if CURRENTOS == "Linux":
    import ConfigParser
    cf = ConfigParser.ConfigParser()
elif CURRENTOS == "Windows":
    import configparser
    cf = configparser.ConfigParser()
else:
    logging.error("The platform %s " % (CURRENTOS) + " is not supported.")
    exit()

#===============================================================================
# cf.read("resize.conf")
#
# CW_REGION = cf.get("cwatch","region")
# CW_ACCOUNT = cf.get("cwatch","account")
# CW_MODE = cf.get("cwatch","mode")
# CW_STATISTICS = cf.get("cwatch","statistics")
# CW_PERIOD = cf.get("cwatch","period")
# CW_STARTTIME = cf.get("cwatch","startTime")
# CW_ENDTIME = cf.get("cwatch","endTime")
# CW_OUTPUT = cf.get("cwatch","outputName")
# CW_DATAFILE = cf.get("parameters","cw_datafile")
#
# ACCOUNT_ID = CW_ACCOUNT
# REDSHIFT_IAM_ROLE = cf.get("parameters","redshift_iam_role")
# S3_BUCKET = cf.get("parameters","s3_bucket_name")
#
# DB_HOST = cf.get("db", "db_host")
# DB_PORT = cf.getint("db", "db_port")
# DB_USER = cf.get("db", "db_user")
# DB_PASS = cf.get("db", "db_pass")
# DB_NAME = cf.get("db", "db_name")
# IOSP_PER_SSD = int(cf.get("parameters","iops_per_ssd"))
#===============================================================================

CW_REGION = "cfn_region"
CW_ACCOUNT = "cfn_account"
CW_MODE = "single"
CW_STATISTICS = "Maximum"
CW_PERIOD = "60"
CW_STARTTIME = "336"
CW_ENDTIME = "0"
CW_OUTPUT = "result"
CW_DATAFILE = "cfn_datafile"

ACCOUNT_ID = CW_ACCOUNT
REDSHIFT_IAM_ROLE = "redshift_iam_role"
S3_BUCKET = "cfn_s3_bucket_name"

DB_HOST = "cfn_db_host"
DB_PORT = "cfn_db_port"
DB_USER = "cfn_db_user"
DB_PASS = "cfn_db_pass"
DB_NAME = "cfn_db_name"
IOSP_PER_SSD = int("6000")

def db_conn(db_host, db_port, db_user, db_pass, db_name):
    try:
        ls_dsn = "dbname='" + db_name + "' user='" + db_user + "' host='" + db_host + "' password='" + db_pass + "' port=" + str(db_port)
        conn = psycopg2.connect(ls_dsn)
        return conn
    except:
        logging.error("I am unable to connect to the database %s " % (ls_dsn))
        exit()

def execute_dml_ddl(db_conn, sql_stat):
    cur_dml_ddl = db_conn.cursor()
    cur_dml_ddl.execute(sql_stat)
    conn.commit()
    cur_dml_ddl.close()

def upload_s3(bucketname, keyname, file_upload):
    s3 = boto3.resource('s3',region_name=CW_REGION)
    s3.meta.client.upload_file(file_upload, bucketname, keyname)

def copy_table(db_conn, tablename, bucketname, sourcefile, ignorerows, gzflag):
    #ls_rolesession_name = REDSHIFT_IAM_ROLE[REDSHIFT_IAM_ROLE.index("/")+1:]
    #client = boto3.client('sts')
    #assumedRoleObject = client.assume_role(RoleArn=REDSHIFT_IAM_ROLE, RoleSessionName=ls_rolesession_name)
    #credentials = assumedRoleObject['Credentials']
    #credentials = client.get_session_token()['Credentials']
    session = boto3.Session()
    credentials = session.get_credentials()
    ls_aws_access_key_id=credentials.access_key
    ls_aws_secret_access_key=credentials.secret_key
    ls_aws_session_token=credentials.token

    ls_import_pricelist_sql = "copy " + tablename + " from 's3://" + bucketname + "/" + sourcefile + "'"
    ls_import_pricelist_sql += " credentials 'aws_access_key_id=" + ls_aws_access_key_id + ";aws_secret_access_key="+ ls_aws_secret_access_key + ";token=" + ls_aws_session_token + "'"
    ls_import_pricelist_sql += " delimiter ',' QUOTE AS '" + '"' + "'" + " IGNOREHEADER " + str(ignorerows)
    if gzflag=="Y":
        ls_import_pricelist_sql += " gzip csv"
    else:
        ls_import_pricelist_sql += " csv"
    execute_dml_ddl(db_conn, ls_import_pricelist_sql)


def import_cwdata(db_conn, sourcefile, ignorerows, gzflag):
    ls_temp_cw_table = "cwdata" + ''.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 8)).replace(' ','')
    ls_create_cwtab_sql = "create table " + ls_temp_cw_table + "( "
    ls_create_cwtab_sql += " humanReadableTimestamp varchar(300), "
    ls_create_cwtab_sql += " timestamp varchar(300), accountId varchar(300), "
    ls_create_cwtab_sql += " az varchar(300), instanceId varchar(300) distkey, "
    ls_create_cwtab_sql += " instanceType varchar(300), instanceTags varchar(max), "
    ls_create_cwtab_sql += " ebsBacked varchar(300), volumeIds varchar(1024), "
    ls_create_cwtab_sql += " instanceLaunchTime varchar(300), humanReadableInstanceLaunchTime varchar(300), "
    ls_create_cwtab_sql += " CPUUtilization varchar(300), NetworkIn varchar(300), "
    ls_create_cwtab_sql += " NetworkOut varchar(300), DiskReadOps varchar(300), DiskWriteOps varchar(300) ) "
    execute_dml_ddl(db_conn, ls_create_cwtab_sql)

    copy_table(db_conn, ls_temp_cw_table, S3_BUCKET, sourcefile, ignorerows, gzflag)
    return ls_temp_cw_table

def download_ec2pricelist():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
    ls_pricelist_file = 'ec2pricelist.csv'
    if os.path.exists(ls_pricelist_file):
        if CURRENTOS == "Linux":
            os.system('rm -rf ' + ls_pricelist_file)
        elif CURRENTOS == "Windows":
            os.system('del ' + ls_pricelist_file)

    try:
        ec2pricelist = urllib.URLopener()
        ec2pricelist.retrieve("https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.csv","index.csv")
        #if CURRENTOS == "Linux":
        #    ls_download_ec2pricelist = "wget https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.csv -q"
        #elif CURRENTOS == "Windows":
        #    ls_download_ec2pricelist = "curl https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.csv -o index.csv"
        #os.system(ls_download_ec2pricelist)
    except Exception as inst:
        logging.error("Could not download the EC2 pricelist from https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.csv")
        exit()

    if os.path.exists("index.csv"):
        if CURRENTOS == "Linux":
            os.system('mv index.csv ' + ls_pricelist_file)
        elif CURRENTOS == "Windows":
            os.system('rename index.csv ' + ls_pricelist_file)

    ls_target_bucket=S3_BUCKET
    ls_source_file = "ec2pricelist.csv"
    logging.info("Uploading the EC2 pricelist file to S3 bucket %s " % (ls_target_bucket))
    upload_s3(ls_target_bucket, ls_pricelist_file, ls_source_file)
    return ls_pricelist_file

def import_ec2pricelist(db_conn, p_ec2pricelist_file):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
    ls_pricelist_file = p_ec2pricelist_file

    ls_columns = linecache.getline(ls_pricelist_file, 6)
    logging.info("Generate Redshift table structure")
    ls_columns_list = [str(x) for x in ls_columns.split(',')]
    if CURRENTOS == "Linux":
        ls_temp_price_table = "pricelist" + string.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 8)).replace(' ','')
    elif CURRENTOS == "Windows":
        ls_temp_price_table = "pricelist" + ''.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 8)).replace(' ','')

    logging.info("Importing the pricelist files to Redshift table: %s " % (ls_temp_price_table))
    ls_create_table_sql = "create table " + ls_temp_price_table + "( "
    for col in ls_columns_list:
        ls_colname = col.replace(' ','').replace('/','').replace('-','').replace('"','')
        if ls_colname == "Group":
            ls_colname = "GroupId"
        ls_create_table_sql += " " + ls_colname + " varchar(300) ,"

    ls_create_table_sql = ls_create_table_sql[:-1]
    ls_create_table_sql += " )"
    execute_dml_ddl(db_conn, ls_create_table_sql)

    copy_table(db_conn, ls_temp_price_table, S3_BUCKET, ls_pricelist_file, 6, "N")

    ls_alter_pricelist_sql = " alter table " + ls_temp_price_table + " add regionabbr varchar(300) "
    execute_dml_ddl(db_conn, ls_alter_pricelist_sql)
    ls_update_pricelist_sql = "update " + ls_temp_price_table + " set regionabbr=case "
    ls_update_pricelist_sql += " when location='US West (Oregon)' then 'USW2' "
    ls_update_pricelist_sql += " when location='US East (N. Virginia)' then 'USE1' "
    ls_update_pricelist_sql += " when location='US West (N. California)' then 'USW1' "
    ls_update_pricelist_sql += " when location='Asia Pacific (Seoul)' then 'APN2' "
    ls_update_pricelist_sql += " when location='Asia Pacific (Singapore)' then 'APS1' "
    ls_update_pricelist_sql += " when location='Asia Pacific (Sydney)' then 'APS2' "
    ls_update_pricelist_sql += " when location='Asia Pacific (Tokyo)' then 'APN1' "
    ls_update_pricelist_sql += " when location='EU (Frankfurt)' then 'EU' "
    ls_update_pricelist_sql += " when location='EU (Ireland)' then 'EUW1' "
    ls_update_pricelist_sql += " when location='South America (Sao Paulo)' then 'SAE1' "
    ls_update_pricelist_sql += " when location='Asia Pacific (Mumbai)' then 'APS1' "
    ls_update_pricelist_sql += " end "
    execute_dml_ddl(db_conn, ls_update_pricelist_sql)
    ls_delete_zero_entry_pricelist_sql = "delete from " + ls_temp_price_table + " where to_number(trim(both ' ' from priceperunit),'9999999D99999999') <= 0.00"
    execute_dml_ddl(db_conn, ls_delete_zero_entry_pricelist_sql)

    return ls_temp_price_table

def determine_right_type(db_conn, sql_stat, s_temp_table, s_instanceid, iops_usage, ssd_size_usage, cpu_nbr_usage, network_level_usage, rate_usage, mem_size):
    ln_iops_usage = iops_usage
    ln_ssd_size_usage = ssd_size_usage
    ln_cpu_nbr = cpu_nbr_usage
    ln_network_level_usage = network_level_usage
    ln_rate = rate_usage
    ln_mem_size = mem_size
    ls_instanceid = s_instanceid
    ls_temp_table = s_temp_table
    cur_resize = db_conn.cursor()
    cur_resize.execute(sql_stat)
    row_newtypes = cur_resize.fetchall()

    for record in row_newtypes:
        ls_min_type = record[1]
        ls_min_storage = record[3]
        ln_min_cpu = int(record[4])
        ln_min_network_level = int(record[5])
        ls_min_network = record[6]
        ln_min_mem = float(record[7].split(' ')[0].replace(',',''))
        ln_min_rate = float(record[2])
        if ls_min_storage.find('SSD')>0:
            if ls_min_storage.find('NVMe')>0:
                ls_min_storage1 = ls_min_storage[:(ls_min_storage.find('NVMe SSD')-1)]
            else:
                ls_min_storage1 = ls_min_storage[:(ls_min_storage.find('SSD')-1)]
            ln_min_ssd_nbr = int(ls_min_storage1[:ls_min_storage1.find('x')-1])
            ln_min_ssd_size = float(ls_min_storage1[ls_min_storage1.find('x')+1:])
            ln_min_ssd_total_size = ln_min_ssd_nbr * ln_min_ssd_size
            ln_min_ssd_total_iops = IOSP_PER_SSD * ln_min_ssd_nbr

        if ln_iops_usage>3000 and ls_min_storage.find('SSD')>0:
             if ln_min_ssd_total_iops>=ln_iops_usage and ln_min_ssd_total_size>=ln_ssd_size_usage:
                 if ln_min_mem>=ln_mem_size:
                     if ln_min_cpu>=ln_cpu_nbr:
                         if ln_min_network_level>=ln_network_level_usage:
                             if ln_min_rate<=ln_rate:
                                 ls_update_type_sql = "update " + ls_temp_table + " set resizetype='" + ls_min_type + "', resizeprice='" + str(ln_min_rate) + "', "
                                 ls_update_type_sql += " newvcpu='" + str(ln_min_cpu) + "', newmemory='" + str(ln_min_mem) + " GiB" + "', newstorage='" + ls_min_storage + "', newnetwork='" + ls_min_network + "' "
                                 ls_update_type_sql += " where instanceid = '" + ls_instanceid + "'"
                                 execute_dml_ddl(db_conn, ls_update_type_sql)
                                 break
        else:
             if ln_min_cpu>=ln_cpu_nbr:
                 if ln_min_mem>=ln_mem_size:
                     if ln_min_network_level>=ln_network_level_usage:
                         if ln_min_rate<=ln_rate:
                             ls_update_type_sql = "update " + ls_temp_table + " set resizetype='" + ls_min_type + "', resizeprice='" + str(ln_min_rate) + "', "
                             ls_update_type_sql += " newvcpu='" + str(ln_min_cpu) + "', newmemory='" + str(ln_min_mem) + " GiB" + "', newstorage='" + ls_min_storage + "', newnetwork='" + ls_min_network + "' "
                             ls_update_type_sql += " where instanceid = '" + ls_instanceid + "'"
                             execute_dml_ddl(db_conn, ls_update_type_sql)
                             break
    cur_resize.close()


def right_sizing(db_conn, pricelist_table, cw_tablename):
    if CURRENTOS == "Linux":
        ls_temp_table = "rightsizing" + string.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 8)).replace(' ','')
    elif CURRENTOS == "Windows":
        ls_temp_table = "rightsizing" + ''.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 8)).replace(' ','')

    ls_gen_list_sql = "create table " + ls_temp_table + " as "
    ls_gen_list_sql += " select upper(substring(a.az,1,2))||upper(substring(a.az,4,1))|| substring(substring(a.az, position('-' in a.az)+1),position('-' in substring(a.az, position('-' in a.az)+1))+1,1) as region, "
    ls_gen_list_sql += " a.instancetype, b.vcpu, b.memory, b.storage, b.networkperformance, b.priceperunit, a.instanceid, max(a.maxcpu) as maxcpu, max(a.maxiops) as maxiops, max(a.maxnetwork) as maxnetwork, a.instancetags "
    ls_gen_list_sql += " from (select instanceid, instancetags, instanceType, az, max(to_number(trim(both ' ' from CPUUtilization),'9999999D99999999')) as maxcpu, "
    ls_gen_list_sql += " max(to_number(trim(both ' ' from diskreadops),'9999999D99999999')/60+to_number(trim(both ' ' from diskwriteops),'9999999D99999999')/60) as maxiops, "
    ls_gen_list_sql += " max((to_number(trim(both ' ' from networkin),'9999999999999D99999999')/60/1024/1024)*8+(to_number(trim(both ' ' from networkout),'9999999999999D99999999')/60/1024/1024)*8) as maxnetwork "
    ls_gen_list_sql += " from " + cw_tablename
    #ls_gen_list_sql += " where accountid like '%" + ACCOUNT_ID + "%' "
    ls_gen_list_sql += " where accountid not like '%accountId%' "
    ls_gen_list_sql += " group by instanceid, instancetags, instanceType, az) a, " + pricelist_table + " b "
    ls_gen_list_sql += " where a.instanceid in (select instanceid from (select instanceid,max(maxcpu) as topcpu from "
    ls_gen_list_sql += "(select instanceid, instancetags, instanceType, az, max(to_number(trim(both ' ' from CPUUtilization),'9999999D99999999')) as maxcpu, "
    ls_gen_list_sql += " max(to_number(trim(both ' ' from diskreadops),'9999999D99999999')/60+to_number(trim(both ' ' from diskwriteops),'9999999D99999999')/60) as maxiops, "
    ls_gen_list_sql += " max((to_number(trim(both ' ' from networkin),'9999999999999D99999999')/60/1024/1024)*8+(to_number(trim(both ' ' from networkout),'9999999999999D99999999')/60/1024/1024)*8) as maxnetwork "
    #ls_gen_list_sql += " from " + cw_tablename + " where accountid like '%" + ACCOUNT_ID + "%' group by instanceid, instancetags, instanceType, az) group by instanceid) where topcpu<50) "
    ls_gen_list_sql += " from " + cw_tablename + " where accountid not like '%accountId%' group by instanceid, instancetags, instanceType, az) group by instanceid) where topcpu<50) "
    ls_gen_list_sql += " and a.instancetype=b.instancetype "
    ls_gen_list_sql += " and upper(substring(a.az,1,2))||upper(substring(a.az,4,1))|| substring(substring(a.az, position('-' in a.az)+1),position('-' in substring(a.az, position('-' in a.az)+1))+1,1)=b.regionabbr "
    ls_gen_list_sql += " and b.termtype='OnDemand' and b.location<>'AWS GovCloud (US)' and b.servicecode='AmazonEC2' "
    ls_gen_list_sql += " and b.tenancy='Shared' and b.processorarchitecture='64-bit' and b.operatingsystem='Linux' and b.preinstalledsw='NA'"
    ls_gen_list_sql += " group by upper(substring(a.az,1,2))||upper(substring(a.az,4,1))|| substring(substring(a.az, position('-' in a.az)+1),position('-' in substring(a.az, position('-' in a.az)+1))+1,1), "
    ls_gen_list_sql += " a.instancetype, b.vcpu, b.memory, b.storage, b.networkperformance, b.priceperunit, a.instanceid, a.instancetags"

    execute_dml_ddl(db_conn, ls_gen_list_sql)

    ls_alter_temp_table = "alter table " + ls_temp_table + " add resizetype varchar(300)"
    execute_dml_ddl(db_conn, ls_alter_temp_table)
    ls_alter_temp_table = "alter table " + ls_temp_table + " add newvcpu varchar(300)"
    execute_dml_ddl(db_conn, ls_alter_temp_table)
    ls_alter_temp_table = "alter table " + ls_temp_table + " add newmemory varchar(300)"
    execute_dml_ddl(db_conn, ls_alter_temp_table)
    ls_alter_temp_table = "alter table " + ls_temp_table + " add newnetwork varchar(300)"
    execute_dml_ddl(db_conn, ls_alter_temp_table)
    ls_alter_temp_table = "alter table " + ls_temp_table + " add resizeprice varchar(300)"
    execute_dml_ddl(db_conn, ls_alter_temp_table)
    ls_alter_temp_table = "alter table " + ls_temp_table + " add costsavedpermonth varchar(300)"
    execute_dml_ddl(db_conn, ls_alter_temp_table)
    ls_alter_temp_table = "alter table " + ls_temp_table + " add newstorage varchar(300)"
    execute_dml_ddl(db_conn, ls_alter_temp_table)

    ls_resizelist_sql = "select * from " + ls_temp_table
    cur = db_conn.cursor()
    cur.execute(ls_resizelist_sql)
    row_resizelists = cur.fetchall()
    ln_instance_nbr = cur.rowcount
    ln_curr_nbr = 0
    for row in row_resizelists:
        ln_curr_nbr += 1
        sys.stdout.write("\rComplete percent: " + str(round(float(ln_curr_nbr)/ln_instance_nbr * 100))+"%")
        sys.stdout.flush()
        ln_cpu = int(row[2])
        ls_storage = row[4]
        ln_mem = float(row[3].split(' ')[0].replace(',',''))
        ln_ssd_type = ''

        if ls_storage.find('SSD')>0:
            if ls_storage.find('NVMe')>0:
                ln_ssd_type = 'NVMe'
                ls_storage1 = ls_storage[:(ls_storage.find('NVMe SSD')-1)]
            else:
                ln_ssd_type = 'SSD'
                ls_storage1 = ls_storage[:(ls_storage.find('SSD')-1)]
            ln_ssd_nbr = int(ls_storage1[:ls_storage1.find('x')-1])
            ln_ssd_size = float(ls_storage1[ls_storage1.find('x')+1:])
            ln_ssd_total_size = ln_ssd_nbr * ln_ssd_size
            ln_ssd_total_iops = IOSP_PER_SSD * ln_ssd_nbr
        else:
            ln_ssd_total_size = 0
            ln_ssd_total_iops = 0

        ln_rate = float(row[6])
        ls_instanceid = row[7]
        ln_cpu_usage = math.ceil(row[8])
        ln_cpu_nbr = math.ceil(float(ln_cpu_usage)/100 * ln_cpu)
        ln_iops_usage = math.ceil(row[9])
        ls_networkperf = row[5]
        ln_network_usage = math.ceil(row[10])

        if ls_networkperf == '10 Gigabit':
            ln_network_level_usage = 99
        else:
            if ln_network_usage<=300:
                ln_network_level_usage = 1
            elif ln_network_usage>300 and ln_network_usage<=1000:
                ln_network_level_usage = 2
            else:
        		ln_network_level_usage = 3

        ls_resizetype_sql = "select regionabbr, instancetype, priceperunit, storage, vcpu, "
        ls_resizetype_sql += " case when networkperformance='Low' then 1 when networkperformance='Moderate' then 2 when networkperformance='High' then 3 else 99 end as networkperformance, networkperformance as newnetwork, memory from " + pricelist_table
        ls_resizetype_sql += " where termtype='OnDemand' and location<>'AWS GovCloud (US)' and servicecode='AmazonEC2' "
        ls_resizetype_sql += " and tenancy='Shared' and processorarchitecture='64-bit' and operatingsystem='Linux' "
        ls_resizetype_sql += " and regionabbr = '" + row[0] + "' "
        if ln_network_level_usage == 99:
            ls_resizetype_sql += " and networkperformance = '10 Gigabit' "
        if ln_ssd_type == 'NVMe':
            ls_resizetype_sql += " and storage like '%NVMe%' "
        else:
            ls_resizetype_sql += " and storage not like '%NVMe%' "
        ls_resizetype_sql += " order by to_number(trim(both ' ' from priceperunit),'9999999D99999999')"

        determine_right_type(db_conn, ls_resizetype_sql, ls_temp_table, ls_instanceid, ln_iops_usage, ln_ssd_total_size, ln_cpu_nbr, ln_network_level_usage, ln_rate, ln_mem)

    print ("\n")
    ls_update_costsaved = "update " + ls_temp_table + " set costsavedpermonth=(to_number(trim(both ' ' from priceperunit),'9999999D99999999') - to_number(trim(both ' ' from resizeprice),'9999999D99999999'))*30*24 "
    execute_dml_ddl(db_conn, ls_update_costsaved)
    ls_update_totalsaved = "insert into " + ls_temp_table + " (region,costsavedpermonth) select 'Total', sum(to_number(trim(both ' ' from costsavedpermonth),'9999999999D99999999')) from " + ls_temp_table
    execute_dml_ddl(db_conn, ls_update_totalsaved)
    ls_delete_sametype = "delete " + ls_temp_table + " where instancetype=resizetype"
    execute_dml_ddl(db_conn, ls_delete_sametype)

    cur.close()
    return ls_temp_table

def dump_results(db_conn, sql_stat, csv_filename):
    cur_csv = db_conn.cursor()
    cur_csv.execute(sql_stat)
    row_csv = cur_csv.fetchall()
    csvfile = open(csv_filename, 'w')
    writers = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL, lineterminator='\n')
    writers.writerow(['region', 'InstanceId', 'Old-InstanceType', 'Old-vCPU', 'Old-Memory', 'Old-Storage', 'Old-NetworkPerformance', 'Old-Rate', 'New-InstanceType', 'New-vCPU', 'New-Memory', 'New-Storage', 'New-Network', 'New-Rate', 'Cost-Saved-Per-Month', 'Max-CPU-Uti', 'Max-IOPS', 'Max-Network', 'Instance-Tag'])

    for line in row_csv:
        writers.writerows([line])

    csvfile.close()
    cur_csv.close()

# Main
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')

    logging.info("Downloading the CloudWatch metrics")
    sys.path.append('callgcw.py')
    import callgcw
    ls_cwfile = callgcw.call_gcw(CW_REGION, CW_ACCOUNT, CW_MODE, CW_STATISTICS, CW_PERIOD, CW_STARTTIME, CW_ENDTIME, CW_OUTPUT)
    #ls_cwfile = "result.20160825.csv.gz"
    logging.info("Finish to download the CloudWatch metrics to the file %s " % ls_cwfile)

    logging.info("Uploading the CloudWatch files to S3 ")
    upload_s3(S3_BUCKET, ls_cwfile, ls_cwfile)
    logging.info("Finish to upload the CloudWatch files to S3 bucket %s " % (S3_BUCKET))

    logging.info("Downloading the EC2 pricelist file and upload it to S3 bucket")
    ls_ec2pricelist_fileame = download_ec2pricelist()
    logging.info("Finish to download EC2 pricelist file and upload it to S3 bucket: %s " % (ls_ec2pricelist_fileame))

    conn = db_conn(DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME)
    logging.info("Connected to the database")

    logging.info("Importing the CloudWatch files to Redshift table")
    ls_cw_tabname = import_cwdata(conn, ls_cwfile, 0, "Y")
    logging.info("Finish to import the CloudWatch files to the Redshift table: %s " % (ls_cw_tabname))

    logging.info("Importing the EC2 pricelist to Redshift")
    ls_pricelist_tabname = import_ec2pricelist(conn, ls_ec2pricelist_fileame)
    logging.info("Finish to import the EC2 pricelist to Redshift table: %s " % (ls_pricelist_tabname))

    logging.info("Analyzing the instances need to be resized")
    ls_temp_table = right_sizing(conn, ls_pricelist_tabname, ls_cw_tabname)
    logging.info("Finish the analysis and store the instances to the table %s " % (ls_temp_table))

    logging.info("Dumping the instances into the csv file")
    #ls_csv_sql = "select * from " + ls_temp_table + " order by to_number(trim(both ' ' from costsavedpermonth),'9999999999D99999999')"
    ls_csv_sql = " select region, instanceid, instancetype, vcpu, memory, storage, networkperformance, priceperunit, "
    ls_csv_sql += " resizetype, newvcpu, newmemory, newstorage, newnetwork, resizeprice, costsavedpermonth, maxcpu, maxiops, maxnetwork, instancetags "
    ls_csv_sql += " from " + ls_temp_table + " order by to_number(trim(both ' ' from costsavedpermonth),'9999999999D99999999')"
    ls_csvfile = "results_" + ls_temp_table + ".csv"
    dump_results(conn, ls_csv_sql, ls_csvfile)
    logging.info("Finish to dump to the csv file %s " % (ls_csvfile) )

    logging.info("Uploading the rightsizing results file to S3 bucket %s " % (S3_BUCKET))
    upload_s3(S3_BUCKET, ls_csvfile, ls_csvfile)

    # @logging.info("Delete the temp table with EC2 pricelist %s " % (ls_pricelist_tabname))
    #execute_dml_ddl(conn, "drop table "+ls_pricelist_tabname)
    #logging.info("Delete the temp table with instances need to be resized %s " % (ls_temp_table))
    #execute_dml_ddl(conn, "drop table "+ls_temp_table)
    #if CURRENTOS == "Windows":
    #    logging.info("Delete the temp table with CloudWatch data %s " % (ls_cw_tabname))
    #    execute_dml_ddl(conn, "drop table "+ls_cw_tabname)

    logging.info("Analysis complete.")
    conn.close()
