import boto.vpc
import os
from subprocess import Popen, PIPE
import logging

def backtick(cmd):
    output = Popen(cmd, stdout=PIPE, shell=True).communicate()[0].rstrip()
    return output

def get_aws_creds(required_cred_class):
    if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
        return (os.environ.get('AWS_ACCESS_KEY_ID'), os.environ.get('AWS_SECRET_ACCESS_KEY'))
    else:
        
        logging.debug("reading AWS creds from password store")
        if not os.environ.get('SBAC_ENV').endswith(required_cred_class):
            logging.error("SBAC_ENV environment variable must be set to a credential set that ends in '{0}', like 'dev/{0}'".format(required_cred_class))
            exit(1)            
        access_id = backtick('pass $SBAC_ENV/aws/access_id')
        secret_key = backtick('pass $SBAC_ENV/aws/secret_key')
        return (access_id, secret_key)

def connect_to_vpc(required_cred_class = 'inventory'):
    (access_id, secret_key) = get_aws_creds(required_cred_class)
    vpc_conn = boto.vpc.VPCConnection(aws_access_key_id=access_id, aws_secret_access_key=secret_key)
    logging.info("connected to AWS VPC OK")
    return vpc_conn

def connect_to_iam(required_cred_class = 'inventory'):
    (access_id, secret_key) = get_aws_creds(required_cred_class)
    iam_conn = boto.connect_iam(aws_access_key_id=access_id, aws_secret_access_key=secret_key)
    logging.info("connected to AWS IAM OK")
    return iam_conn

def connect_to_ec2(region = 'us-east-1', required_cred_class = 'inventory'):
    (access_id, secret_key) = get_aws_creds(required_cred_class)
    conn = boto.ec2.connect_to_region(region,
        aws_access_key_id=access_id,
        aws_secret_access_key=secret_key
    )
    logging.info("connected to AWS EC2 OK")
    return conn
