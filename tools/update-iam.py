#!/usr/bin/python

from optparse import OptionParser
import logging
import yaml
import json
from StringIO import StringIO
from jinja2 import Template
import time
from srl.aws import *

def main():
    opts = read_options()
    cfg = read_config_file(opts)
    hints = preflight(opts, cfg)
    create_groups(hints, cfg)
    create_roles(hints, cfg)
    create_instance_profiles(hints, cfg)

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
    vpc_conn = connect_to_vpc(required_cred_class = 'security')
    hints['vpc']['conn'] = vpc_conn
    hints['vpc']['env'] = opts.env
    iam_conn = connect_to_iam(required_cred_class = 'security')
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
            template = Template(cfg['iam_policies'][p])

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

def create_groups(hints, cfg):
    # List groups and look for the ones that should exist
    conn = hints['iam']['conn']
    all_groups = iam_list(conn, 'groups', 'get_all')

    for tier in ['inventory', 'spinup', 'security']:
        
        # Ensure group exists
        group_name = 'edware-' + tier
        policy_name = group_name + '_pol'
        group = all_groups.get(group_name)
        if group:
            logging.info("- OK  - Group {0} exists".format(group_name))
        else:
            group = conn.create_group(group_name)['create_group_response']['create_group_result']['group']
            logging.info("- NEW - Group {0} created".format(group_name))

        # Check policy members on group - should be exactly one 
        current_policy_names = set(conn.get_all_group_policies(group.group_name)['list_group_policies_response']['list_group_policies_result']['policy_names']) # @#$%#$ irregular API
        expected_policy_names = set([ policy_name ])
        spurious_policy_names = current_policy_names - expected_policy_names
        missing_policy_names  = expected_policy_names - current_policy_names
        for gp in spurious_policy_names:
            conn.delete_group_policy(group_name, gp)
            current_policy_names = current_policy_names - set([gp])
            logging.info("- DEL - Group {0} has spurious policy named {1}, deleting".format(group_name, gp))

        desired_definition = generate_group_policy(tier, policy_name, cfg, conn)
        current_definition = '{}'
        if len(current_policy_names) == 1:
            current_definition = conn.get_group_policy(group_name, policy_name)
            
        if current_definition == desired_definition:  # These are strings of canonicalized JSON
            logging.info("- OK  - Group {0} has correct policy named {1}".format(group_name, policy_name))
        else:
            conn.put_group_policy(group_name, policy_name, desired_definition)
            if len(current_policy_names) == 1:
                logging.info("- UPD - Group {0} needed update on policy named {1}".format(group_name, policy_name))
            else:
                logging.info("- NEW - Group {0} was missing policy named {1}".format(group_name, policy_name))            

def iam_list(conn, subject, method = 'list', key='name', args=[], singular=None):
    items_by_key = {}
    if not singular:
        singular = subject[:-1]
    
    raw_result = getattr(conn, method + '_' + subject)(*args)
    # Note that the response is always packed with a 'list' prefix
    raw_result = raw_result['list_' + subject + '_response']
    raw_result = raw_result['list_' + subject + '_result']
    raw_result = raw_result[subject]
    for i in raw_result:
        item_key = getattr(i, singular + '_' + key)
        items_by_key[item_key] = i
    return items_by_key


def generate_group_policy(tier, policy_name, cfg, conn):
    # Fetch policy definition from YAML into python dict
    policy = json.loads(cfg['iam_policies'][policy_name])
    
    # If spinup, generate the pass role perms
    if tier == 'spinup':
        add_pass_roles_to_spinup_policy(policy, cfg, conn)
        
    # Convert to JSON string, canonicalizing
    return dict2json(policy)

def dict2json(thing):
    io = StringIO()
    json.dump(thing, io, sort_keys=True,indent=2)
    return io.getvalue()
    
def add_pass_roles_to_spinup_policy(policy, cfg, conn):

    # Find PassRole rule
    rule = [r for r in policy['Statement'] if r['Action'][0] == 'iam:PassRole'][0] # TODO - seems brittle
    # Reset targets
    rule['Resource'] = []
    
    # Get a list of environments
    for env in ['', '_test186']: # TODO: make this dynamnic, using conn to get VPC list?                
        # Get a list of roles
        for role in cfg['iam_roles'].keys():
            rule['Resource'].append('arn:aws:iam::*:role/' + role + env)

    rule['Resource'].sort()

    return policy

main()
