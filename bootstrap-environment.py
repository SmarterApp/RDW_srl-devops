#!/usr/bin/python

import boto.ec2
import boto.vpc
from optparse import OptionParser
import logging
import os
import os.path
from subprocess import Popen, PIPE
import time

def main():
    opts = read_options()
    hints = preflight(opts)
    create_vpc_and_security_groups(hints)
    init_iam(hints)
    create_ansible_host(hints)
    
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


def read_options():
    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                        help="Debug level output")
    parser.add_option("-e", "--env", dest="env", metavar="ENV", type="string",
                       help="Required.  Which environment (VPC) to target.  'dev' not permitted.  If the VPC exists, will create instances there; if not will create the VPC. Values are the Environment tags on the VPCs.")
    parser.add_option("-b", "--block", dest="block", metavar="BLOCK", type="int",
                       help="Required.  Which CIDR B-block to place the VPC in under 10.BLOCK.0.0.")

        
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
        logging.info("We'll be creating a new VPC environment {0}".format(opts.env))
        
    # TODO - check for b-block collision
    hints['vpc']['block'] = opts.block
            
    return hints

def create_vpc_and_security_groups(hints):
    if hints['vpc'].get('obj'):
        return

    os.environ['SBAC_ENVIRO_BUILDER_VPC_BLOCK'] = str(hints['vpc']['block'])
    os.environ['SBAC_ENVIRO_BUILDER_MODE'] = 'dynamic'
    os.environ['SBAC_ENVIRO_BUILDER_ENV_NAME'] = hints['vpc']['env']

    os.chdir('ansible')
    os.system('ansible-playbook -i inventories/localhost vpc-and-security-groups.yml')
    os.chdir('..')

def init_iam(hints):
    os.chdir('tools')
    os.system("./initialize_iam_s3_roles.py -e {0}".format(hints['vpc']['env']))
    os.chdir('..')

def create_ansible_host(hints):

    # Spawn, but do not ansiblize, the ansible server.
    os.chdir('spawner')

    os.system("./spawner.py -a ansible -e {0} -s".format(hints['vpc']['env']))
    os.system("./spawner.py -a nat -e {0} -s".format(hints['vpc']['env'])) 
    os.chdir('..')
        
main()
