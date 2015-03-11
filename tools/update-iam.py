#!/usr/bin/python

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
    # create_managed_profiles(hints, cfg)
    # create_users(hints, cfg)

# TODO: copypasta from spawner.py, DRY up4
def backtick(cmd):
    output = Popen(cmd, stdout=PIPE, shell=True).communicate()[0].rstrip()
    return output
    
 # TODO: copypasta from spawner.py, DRY up
def get_aws_creds():
    if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
        return (os.environ.get('AWS_ACCESS_KEY_ID'), os.environ.get('AWS_SECRET_ACCESS_KEY'))
    else:
        
        logging.debug("reading AWS creds from password store")
        if not os.environ.get('SBAC_ENV').endswith('security'):
            logging.error("SBAC_ENV environment variable must be set to a credential set that ends in 'security', like 'dev/security'")
            exit(1)            
        access_id = backtick('pass $SBAC_ENV/aws/access_id')
        secret_key = backtick('pass $SBAC_ENV/aws/secret_key')
        return (access_id, secret_key)
    

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
    hints['vpc']['all_envs'] = [ v.tags.get('Environment') for v in vpc_conn.get_all_vpcs() if v.tags.get('Environment') ]
            
    return hints

def read_config_file(opts):
    logging.info("Reading config file from ./iam-config.yaml")
    cfg = yaml.load(open("./iam-config.yaml", 'r'))
    return cfg

def create_roles(hints, cfg):
    iam_conn = hints['iam']['conn']

    role_suffix = '' if hints['vpc']['env'] == 'prod' else '_' + hints['vpc']['env']

    # A tad clunky, this IAM interface
    roles_by_name = {}
    for r in iam_conn.list_roles()['list_roles_response']['list_roles_result']['roles']:
        roles_by_name[r.role_name] = r
    
    # Create the role
    for r in cfg['iam_roles']:    
        role_name = r + role_suffix

        if role_name in roles_by_name:
            logging.info(" - OK  - Role {0} already exists...".format(role_name))
        else:
            iam_conn.create_role(role_name)
            logging.info(" - NEW - Role {0} created!".format(role_name))
            
        # Create each of the inline policies in the role        
        for p in cfg['iam_roles'][r]:
            template = Template(cfg['inline_policies'][p])

            # If we are in a test env, just use the dev yum repo
            if p.startswith('yum') and hints['vpc']['env'].startswith('test'):
                s3_env = 'dev' 
            else:
                s3_env = hints['vpc']['env']
            
            policy = template.render(env = s3_env)
            policy_name = p
            # TODO - no easy way to tell if a change is needed here, it just always writes it
            logging.info("Updating policy {0} on role {1}".format(policy_name, role_name))
            iam_conn.put_role_policy(role_name, policy_name, policy)        

def create_instance_profiles(hints, cfg):
    iam_conn = hints['iam']['conn']

    suffix = '' if hints['vpc']['env'] == 'prod' else '_' + hints['vpc']['env']

    # A tad clunky, this IAM interface
    profiles_by_name = {}
    for p in iam_conn.list_instance_profiles()['list_instance_profiles_response']['list_instance_profiles_result']['instance_profiles']:
        profiles_by_name[p.instance_profile_name] = p

    # We've decided to go with a 
    # 1:1 mapping between roles and instance profiles    
    for r in cfg['iam_roles']:    
        role_name = r + suffix
        profile_name = r.replace('_role', '_profile') + suffix

        if profile_name in profiles_by_name:
            logging.info(" - OK  - Instance Profile {0} already exists...".format(profile_name))
        else:
            iam_conn.create_instance_profile(profile_name)
            logging.info(" - NEW - Instance Profile {0} created!".format(profile_name))


        # Need to idempotently ensure that the profile's role list contains exactly the right role.
        profile = iam_conn.get_instance_profile(profile_name)['get_instance_profile_response']['get_instance_profile_result']['instance_profile']

        if (len(profile.roles) == 1 and profile.roles.member.role_name == role_name):
            logging.info(" - OK  - Instance Profile {0} already maps 1:1 to {1}".format(profile_name, role_name))
        else:
            for r2 in profile.roles:
                iam_conn.remove_role_from_instance_profile(profile_name, r2.role_name)                
            iam_conn.add_role_to_instance_profile(profile_name, role_name)
            logging.info("- NEW - Instance Profile {0} updated to map 1:1 to {1}".format(profile_name, role_name))

def create_managed_profiles(hints, cfg):
    # iam_conn = hints['iam']['conn']
    # https://github.com/boto/boto/issues/2956
    None
            
main()
