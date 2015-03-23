#!/usr/bin/python

from optparse import OptionParser
import logging
import yaml
from srl.aws import *

#import pdb; pdb.set_trace()

def main():
    opts = read_options()
    cfg = read_config_file(opts)
    hints = preflight(opts, cfg)    
    apply_security_groups(hints, cfg)

def read_options():
    parser = OptionParser()
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                        help="Debug level output")
    parser.add_option("-e", "--env", dest="env", metavar="ENV", type="string",
                       help="Required.  Which environment (VPC) to target.  Only instances in that VPC will be affected.")
    parser.add_option("-n", "--dry-run", dest="dry_run", action='store_true', default=False,
                       help="Don't actually make any changes.")
    parser.add_option("-A", "--add-only", dest="add_only", action='store_true', default=False,
                       help="Only add, don't delete")
        
    (options, args) = parser.parse_args()
     
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debugging output enabled.")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("INFO logging enabled.")
        
    if options.env == None:
        logging.error("Must specify an Environment to target with -e.  See -h for more help.")
        exit(1)

    return options

def preflight(opts, cfg):
    hints = {}

    hints['dry-run'] = opts.dry_run
    hints['add-only'] = opts.add_only
    
    #--------------
    # Cache connections
    #--------------
    hints['vpc'] = {}
    vpc_conn = connect_to_vpc(required_cred_class = 'spinup')    
    hints['vpc']['conn'] = vpc_conn

    hints['ec2'] = {}
    ec2_conn = connect_to_ec2(required_cred_class = 'spinup')    
    hints['ec2']['conn'] = ec2_conn
    
    #--------------
    # Verify VPC
    #--------------
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
        logging.info("VPC Not found {0}".format(opts.env))
        exit(3)

    #--------------
    # Get mapping of SG IDs <=> names
    #--------------
    sgs = ec2_conn.get_all_security_groups()
    sgs = [sg for sg in sgs if sg.vpc_id == hints['vpc']['id']]
    hints['sgs'] = {}
    hints['sgs']['id'] = {}
    hints['sgs']['name'] = {}
    for sg in sgs:
        hints['sgs']['id'][sg.id] = sg.name
        hints['sgs']['name'][sg.name] = sg.id
    
    return hints

def read_config_file(opts):
    logging.info("Reading config file from ./spawner.yaml")
    cfg = yaml.load(open("./spawner.yaml", 'r'))
    return cfg

def apply_security_groups(hints, cfg):

    ec2 = hints['ec2']['conn']
    
    all_instances = [r.instances for r in ec2.get_all_reservations()]
    all_instances = [i for sublist in all_instances for i in sublist] # List flattening incantation
    all_instances = [i for i in all_instances if i.tags.get('environment') == hints['vpc']['env']]
            
    # For each app type
    for app_info in cfg['apps']:
        app_name = app_info['name']
        intended_sg_names = set(app_info['security_groups'])
        intended_sg_ids = [ hints['sgs']['name'][sgn] for sgn in intended_sg_names ]
                
        # For each instance
        for instance in [i for i in all_instances if i.tags.get('application') == app_name]:
            instance_name = instance.tags.get('Name')
            current_sg_names = set([g.name for g in instance.groups])
            spurious = current_sg_names - intended_sg_names
            missing = intended_sg_names - current_sg_names
            if len(missing) > 0 or len(spurious) > 0:
                if len(missing) > 0:
                    logging.info(" - TO ADD - {0}: {1}".format(instance_name, ', '.join(missing)))
                if len(spurious) > 0:
                    logging.info(" - TO DEL - {0}: {1}".format(instance_name, ', '.join(spurious)))
                    
                if not hints['dry-run']:
                    if hints['add-only']:
                        with_missing = [ hints['sgs']['name'][sgn] for sgn in current_sg_names | missing]
                        instance.modify_attribute('groupSet', with_missing)
                        logging.info(" -  ADDED - {0}: {1}".format(instance_name, ', '.join(missing)))
                    else:
                        instance.modify_attribute('groupSet', intended_sg_ids)
                        logging.info(" -  RESET - {0}: {1}".format(instance_name, ', '.join(intended_sg_names)))
            else:
                logging.info(" - OK     - {0}".format(instance_name))            
            
main()
