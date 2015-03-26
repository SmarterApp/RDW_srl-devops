#!/usr/bin/python

import boto.ec2
import boto.vpc
from optparse import OptionParser
import logging
import os
import os.path
import yaml
from subprocess import Popen, PIPE
import time


def main():
    opts = read_options()
    cfg = read_config_file(opts)
    create_app_instances(opts, cfg)
    
#===========================================================#
#                    
#===========================================================#

# TODO: copypasta from spawner.py, DRY up
def backtick(cmd):
    output = Popen(cmd, stdout=PIPE, shell=True).communicate()[0].rstrip()
    return output

# TODO: copypasta from spawner.py, DRY up
def get_aws_creds():
    if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
        return (os.environ.get('AWS_ACCESS_KEY_ID'), os.environ.get('AWS_SECRET_ACCESS_KEY'))
    else:
        logging.debug("reading AWS creds from password store")
        access_id = backtick('pass $SBAC_ENV/aws/access_id')
        secret_key = backtick('pass $SBAC_ENV/aws/secret_key')
        return (access_id, secret_key)
    
# TODO: copypasta from spawner.py, DRY up
def connect_to_ec2(region):
    (access_id, secret_key) = get_aws_creds()
    conn = boto.ec2.connect_to_region(region,
        aws_access_key_id=access_id,
        aws_secret_access_key=secret_key
    )
    logging.info("connected to AWS EC2 OK")
    return conn

# TODO: copypasta from spawner.py, DRY up
def connect_to_vpc():
    (access_id, secret_key) = get_aws_creds()
    vpc_conn = boto.vpc.VPCConnection(aws_access_key_id=access_id, aws_secret_access_key=secret_key)
    logging.info("connected to AWS VPC OK")
    return vpc_conn

def read_config_file(opts):
    logging.info("Reading config file from ./spawner/spawner.yaml")
    cfg = yaml.load(open("./spawner/spawner.yaml", 'r'))
    return cfg

def read_options():
    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                        help="Debug level output")
    parser.add_option("-e", "--env", dest="env", metavar="ENV", type="string",
                       help="Required.  Which environment (VPC) to target.  'dev' not permitted.  If the VPC exists, will create instances there; if not will create the VPC. Values are the Environment tags on the VPCs.")    

    parser.add_option("-s", "--skip-to", dest="skip_to", metavar="SKIPTO", type="string",
                       help="Optional.  If provided, the name of an app to skip to and continue from.")    

    (options, args) = parser.parse_args()
     
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debugging output enabled.")
    else:
        logging.basicConfig(level=logging.INFO)
        
    if options.env == None:
        logging.error("Must specify an Environment to spawn with -e.  See -h for more help.")
        exit(1)
        
    if options.env == 'dev':
        logging.error("No, you're not allowed to deploy to the 'dev' env because that would break just literally everything.")
        exit(2)
    return options

def preflight(opts):
    hints = {}

    #--------------
    # Verify VPC
    #--------------
    hints['vpc'] = {}
    vpc_conn = connect_to_vpc()
    hints['vpc']['conn'] = vpc_conn
    hints['vpc']['env'] = opts.env
    vpcs = [ v for v in vpc_conn.get_all_vpcs() if v.tags.get('Environment') == opts.env ]
    if len(vpcs) > 1:
        logging.error("Yipes, VPC environment {0} is non-unique!".format(opts.env))
        exit(3)
    if len(vpcs) == 1:
        logging.info("Selected EXISTING VPC environment {0} {1}".format(opts.env, vpcs[0].id))
        hints['vpc']['obj'] = vpcs[0]
        hints['vpc']['id'] = vpcs[0].id
    if len(vpcs) == 0:
        logging.error("Yipes, VPC environment {0} is non-existant!".format(opts.env))
        exit(3)
        
    return hints

def create_app_instances(opts, cfg):

    os.chdir('spawner')
    
    start = 0
    if opts.skip_to:
        for idx, app in enumerate(cfg['apps']):
            if app['name'] == opts.skip_to:
                start = idx
    
    for app in cfg['apps'][start:]:
        app_name = app['name']
        
        # TODO: for now, take all counts from the dev setting.
        count = app['spawn_count']['dev']
                
        if count == 0:
            logging.info('Skipping app {0} due to zero count'.format(app_name))
        else:
            logging.info('Examining app {0}'.format(app_name))
            rc = os.system("./spawner.py -a {0} -e {1} -c {2}".format(app_name, opts.env, count))
            if rc != 0:
                logging.info('Cowardly giving up. ')
                exit(4)
    
    os.chdir('..')

    
main()
