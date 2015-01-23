#!/usr/bin/python

import boto.ec2
import boto.vpc
from optparse import OptionParser
import logging
import yaml
import os
from subprocess import Popen, PIPE
import time

def main():
    opts = read_cli_opts()
    cfg = read_config_file(opts)
    ec2 = connect_to_ec2(opts, cfg)
    hints = validate_request(opts, cfg, ec2)
    spawn(hints, ec2)
    logging.info('          ~ FIN ~')
    
#=========================================================#
#                     Functions
#=========================================================#

def backtick(cmd):
    output = Popen(cmd, stdout=PIPE, shell=True).communicate()[0].rstrip()
    return output

def get_aws_creds():
    if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
        return (os.environ.get('AWS_ACCESS_KEY_ID'), os.environ.get('AWS_SECRET_ACCESS_KEY'))
    else:
        logging.debug("reading AWS creds from password store")
        access_id = backtick('pass $SBAC_ENV/aws/access_id')
        secret_key = backtick('pass $SBAC_ENV/aws/secret_key')
        return (access_id, secret_key)

def connect_to_ec2(opts, cfg):
    (access_id, secret_key) = get_aws_creds()
    # Relies on reading creds from env vars
    conn = boto.ec2.connect_to_region(cfg['region'],
        aws_access_key_id=access_id,
        aws_secret_access_key=secret_key
    )
    logging.info("connected to AWS EC2 OK")
    return conn
            
def read_cli_opts():
    parser = OptionParser()
    parser.add_option("-c", "--count", type="int", dest="count", default=1,
                        help="Number of instances to spawn", metavar="COUNT")
    parser.add_option("-b", "--begin", type="int", dest="begin", default=1,
                        help="Sequence number to begin at for naming", metavar="BEGIN")
    parser.add_option("-a", "--app", dest="app", type="string",
                        help="Which app to spawn", metavar="APP")
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                        help="Debug level output")
    parser.add_option("-V", "--vpc", dest="vpc", metavar="VPC", type="string", default="dev", help="Which VPC to target")
    
    (options, args) = parser.parse_args()
     
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debugging output enabled.")
    else:
        logging.basicConfig(level=logging.INFO)
        
    if options.app == None:
        logging.error("Must specify an app to spawn with -a.  See -h for more help.")
        exit(1)
    return options

def read_config_file(opts):
    logging.info("Reading config file from ./spawner.yaml")
    cfg = yaml.load(open("./spawner.yaml", 'r'))
    return cfg

def spawn(hints, ec2):

    logging.info("About to launch {0} instance(s).  Press Control-C to abort!".format(hints['count']))
    for t in range(5,0,-1):
        logging.info("Launching in {0}...".format(t))
        time.sleep(1)
        
    # Make the reservation call.
    logging.info("OK, sending launch request!")
    reservation = ec2.run_instances(hints['ami_id'],
                                    min_count = hints['count'],
                                    max_count = hints['count'],
                                    instance_type = hints['instance_type'],
                                    subnet_id = hints['subnet_id'],
                                    security_group_ids = hints['security_group_ids']
                                   )

    # Sleep a little bit.
    logging.info("Launch request sent.  Waiting a little bit to start tagging...")
    # TODO: make this smarter; we could poll, and continue when the reservation has the expected number of instances
    time.sleep(3 + 0.25*hints['count'])

    # Re-fetch the reservation, which "should" now have the instances populated
    # TODO: figure out the filter parameter to this call
    all_res = ec2.get_all_reservations()
    reservation = [r for r in all_res if r.id == reservation.id][0]
    
    # Apply tags to the instances.
    for idx in range(0, len(hints['names'])):
        instance = reservation.instances[idx]
        logging.info ("Tagging instance {0} as {1}".format(instance.id, hints['names'][idx]))
        instance.add_tags(hints['tags'])
        instance.add_tag('Name', value = hints['names'][idx])    

def validate_request(opts, cfg, ec2):
    logging.info("Gathering info about your spawn request....")

    hints = {}
    hints['count'] = opts.count
    
    #------
    # Verify that requested app type exists in the config file
    #------
    if not opts.app in cfg['apps']:
        logging.error("I don't know anything about an application named {0}".format(opts.app))
        exit(2)
    app = cfg['apps'][opts.app]
    
    #------
    # Verify that no existing instances have names that will collide over the spawn range
    #------
    # TODO: consider examining DNS instead of / in addition to the AWS tags
    logging.debug("Generating names and checking for collisions")
    hints['names'] = ["srl-{0}-{1}".format(opts.app, str(i).zfill(3)) for i in range(opts.begin, opts.count + opts.begin)]
    instance_tags = ec2.get_all_tags({'resource-type':'instance'})
    existing_names = [t.value for t in instance_tags if t.name == 'Name']
    for proposed_name in hints['names']:
        if proposed_name in existing_names:
            logging.error("A machine already exists named {0}. Consider the -b option. You shall not pass.".format(proposed_name))
            exit(3)
            
    #------
    # Verify that AMI ID for that app type exists, and get tags
    #------
    logging.debug("Fetching tags for AMI id {0}".format(app['ami']))
    ami_tags = ec2.get_all_tags({'resource-type':'image','resource-id':app['ami']})
    if not len(ami_tags) > 0:
        logging.error("AMI id {0} either doesn't exist, or has no tags - you shall not pass.".format(app['ami']))
        exit(4)
    hints['ami_id'] = app['ami']
    hints['tags'] = {}
    for tn in ['application', 'version', 'environment', 'tier']:
        ami_tag = filter(lambda t: t.name == tn, ami_tags)
        if len(ami_tag) > 0:
            hints['tags'][tn] = ami_tag[0].value

    #------
    # Map security group names to IDs
    #------
    # TODO: Dev has no default VPC, so calling ec2.get_all_security_groups(groupnames=[...]) fails with a "No Default VPC" error.  BUt, oddly, we CAN lsit all SG's.
    all_sgs = ec2.get_all_security_groups()
    hints['security_group_ids'] = []
    for sgn in app['security_groups']:
        # TODO: There has got to be a be a better way
        matched_sg = filter(lambda g: g.name == sgn, all_sgs)
        if len(matched_sg) > 0:
            hints['security_group_ids'].append(matched_sg[0].id)
        else:
            logging.error("Security group {0} does not seem to exist - you shall not pass.".format(sgn))
            exit(5)

    #------
    # Check VPC selection (via opts.vpc matching on VPC 'environment' tag)
    #------
    logging.debug("Verifying VPC selection")
    (access_id, secret_key) = get_aws_creds()    
    vpc_conn = boto.vpc.VPCConnection(aws_access_key_id=access_id, aws_secret_access_key=secret_key)
    logging.info("connected to AWS VPC OK")
    vpcs = vpc_conn.get_all_vpcs()
    selected_vpc = [v for v in vpcs if v.tags.get('Environment') == opts.vpc] # Note capitalization
    if len(selected_vpc) == 0 or len(selected_vpc) > 1:
        logging.error("Could not find a unique VPC tagged with the {0} environment - you shall not pass.".format(opts.vpc))
        exit(6)
    hints['vpc_id'] = selected_vpc[0].id
        
    #------
    # Locate subnet within VPC using 'Tier' tag
    #------
    subnet_type = 'private' if not app.get('subnet_type') else app['subnet_type']
    subnets = vpc_conn.get_all_subnets()
    subnets = [s for s in subnets if s.vpc_id == hints['vpc_id']]
    subnets = [s for s in subnets if str(s.tags.get('Tier')).lower() == subnet_type.lower() ]

    if len(subnets) < 1 or len(subnets) > 1:
        logging.error("Could not find a unique Subnet tagged for the {0} tier in VPC {1} - you shall not pass.".format(subnet_type, hints['vpc_id']))
        exit(7)
    hints['subnet_id'] = subnets[0].id
                
    # TODO: Verify instance type ?
    hints['instance_type'] = app['instance_type']
    
    logging.info("Preflight looks good.  Hang onto your hats!")
    
    return hints

#=========================================================#
#                         Executor
#=========================================================#
main()
