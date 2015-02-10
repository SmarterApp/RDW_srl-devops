#!/usr/bin/python

import boto.ec2
import boto.vpc
from optparse import OptionParser
import logging
import yaml
import os
import os.path
from subprocess import Popen, PIPE
from jinja2 import Template
import time


def main():
    opts = read_options()
    cfg = read_config_file(opts)
    hints = preflight(opts, cfg)
    create_roles(hints, cfg)
    create_instance_profiles(hints, cfg)

    #for p in cfg['instance_profiles']:
    #	for r in p['profile_roles']:
    #		logging.info("Profile {0} will get created with {1}".format(p['name'],r))

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

def connect_to_iam():
	(access_id, secret_key) = get_aws_creds()
	iam_conn = boto.connect_iam(aws_access_key_id=access_id, aws_secret_access_key=secret_key)
	logging.info("connected to AWS IAM OK")
	return iam_conn

def read_options():
    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                        help="Debug level output")
    parser.add_option("-e", "--env", dest="env", metavar="ENV", type="string",
                       help="Required.  Which environment (VPC) to target.  If the VPC exists, will create iam roles.")
        
    (options, args) = parser.parse_args()
     
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debugging output enabled.")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("INFO logging enabled.")
        
    if options.env == None:
        logging.error("Must specify an Environment to spawn with -e.  See -h for more help.")
        exit(1)

    return options

def preflight(opts, cfg):
    hints = {}

    #--------------
    # Verify VPC
    #--------------
    hints['vpc'] = {}
    hints['iam'] = {}
    vpc_conn = connect_to_vpc()
    hints['vpc']['conn'] = vpc_conn
    hints['vpc']['env'] = opts.env
    iam_conn = connect_to_iam()
    hints['iam']['conn'] = iam_conn
    vpcs = [ v for v in vpc_conn.get_all_vpcs() if v.tags.get('Environment') == opts.env ]
    if len(vpcs) > 1:
        logging.error("Yipes, VPC environment {0} is non-unique!".format(opts.env))
        exit(3)
    if len(vpcs) == 1:
        logging.info("Selected EXISTING VPC environment {0} {1}".format(opts.env, vpcs[0].id))
        hints['vpc']['obj'] = vpcs[0]
        hints['vpc']['id'] = vpcs[0].id
    if len(vpcs) == 0:
        logging.info("VPC Not found {0}".format(opts.env))
        exit(3)
            
    return hints

def read_config_file(opts):
    logging.info("Reading config file from ./iam_s3_roles.yaml")
    cfg = yaml.load(open("./iam_s3_roles.yaml", 'r'))
    return cfg

def create_roles(hints, cfg):
	iam_conn = hints['iam']['conn']

	for r in cfg['roles']:
		template = Template(cfg['roles'][r])
		policy = template.render(env=hints['vpc']['env'])
		policy_name = r + "_policy"
		try:
			iam_conn.create_role(r)
			logging.info("Role {0} created".format(r))
		except Exception:
			logging.error("Role {0} threw an exception. Hope that's ok.".format(r))
		try:
			iam_conn.put_role_policy(r, policy_name, policy)
			logging.info("Policy {0} added to role {1}".format(policy_name, r))
			logging.debug("policy is \n{0}".format(policy))
		except Exception:
			logging.error("Policy {0} on role {1} threw an exception. Hope that's ok. Text:\n".format(policy_name, r))

def create_instance_profiles(hints, cfg):
	iam_conn = hints['iam']['conn']

	for p in cfg['instance_profiles']:
		try:
			iam_conn.create_instance_profile(p['name'])
			logging.info("Profile {0} created".format(p['name']))
		except Exception:
			logging.error("Profile {0} not created. hope that's ok".format(p['name']))
		for r in p['profile_roles']:
			time.sleep(1)
			try:
				iam_conn.add_role_to_instance_profile(p['name'], r)
				logging.info("Role {0} added to profile {1}".format(r,p['name']))	
			except Exception:
				logging.error("Error adding role {0} to profile {1}. hope that's ok".format(r,p['name']))

main()
