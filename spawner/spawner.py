#!/usr/bin/python

import boto.ec2
import boto.vpc
from optparse import OptionParser
import logging
import yaml
import os
import os.path
from subprocess import Popen, PIPE
import time
from distutils.version import LooseVersion

#import pdb; pdb.set_trace()

def main():
    opts = read_cli_opts()
    cfg = read_config_file(opts)
    ec2_conn = connect_to_ec2(opts, cfg)
    vpc_conn = connect_to_vpc(opts, cfg)
    hints = validate_request(opts, cfg, ec2_conn, vpc_conn)
    spawn(hints, ec2_conn)
    run_ansible(opts, hints)
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
    conn = boto.ec2.connect_to_region(cfg['region'],
        aws_access_key_id=access_id,
        aws_secret_access_key=secret_key
    )
    logging.info("connected to AWS EC2 OK")
    return conn

def connect_to_vpc(opts, cfg):
    (access_id, secret_key) = get_aws_creds()
    vpc_conn = boto.vpc.VPCConnection(aws_access_key_id=access_id, aws_secret_access_key=secret_key)
    logging.info("connected to AWS VPC OK")
    return vpc_conn

def read_cli_opts():
    parser = OptionParser()
    parser.add_option("-a", "--app", dest="app", type="string",
                        help="Which app to spawn.  Required; values are app names from spawner.yaml", metavar="APP")
    parser.add_option("-B", "--base-ami", dest="force_base_ami", action="store_true",
                        help="Instead of using the applciation's AMI, force starting from the base AMI", metavar="BASE")
    parser.add_option("-b", "--begin", type="int", dest="begin",
                        help="Sequence number to begin at for naming to avoid naming collisions.  Optional, default auto.", metavar="BEGIN")
    parser.add_option("-c", "--count", type="int", dest="count", default=1,
                        help="Number of instances to spawn.  Optional, default 1.", metavar="COUNT")
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                        help="Debug level output")
    parser.add_option("-e", "--env", dest="env", metavar="ENV", type="string",
                       default="dev", help="Which environment (VPC) to target.  Defaults to dev; values are the Environment tags on the VPCs.")
    parser.add_option("-p", "--playbook", dest="playbook", type = "string",
                        help="Which playbook in ../ansible/*.yml to run.  Defaults to same name as -a.")
    parser.add_option("-s", "--skip-ansible", dest="run_ansible", action="store_false", default=True,
                        help="Do not run ansible playbook after spawning.")
    parser.add_option("-t", "--tag", dest="extra_tag", type="string",
                        help="Extra tag to apply to the instances, in the form key:value.")
    parser.add_option("-V", "--app-version", dest="app_version", metavar="APP_VERSION", type="string",
                       help="Which application version (AMI) to use.  AMI is selected by looking for an AMI tagged with the application and version.  Optional, latest version is default.")
    
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

def run_ansible(opts, hints):
    if not opts.run_ansible:
        logging.info("Skipping ansible run due to -s")
        return

    logging.info("Waiting 30 seconds for AWS inventory to be consistent, eventually...")
    time.sleep(30)
    
    os.chdir(os.environ['SBAC_DEVOPS'] + '/ansible')    
    logging.info("Using Ansible to detect when SSH is up...")
    cmd = []
    cmd.append("ansible-playbook")
    cmd.append('-l'); cmd.append(':'.join(hints['ips'].values())) # Limit to newly-created instances
    cmd.append('wait-for-ssh.yml')
    rv = os.system(' '.join(cmd))
    if not rv == 0:
        logging.error("Hrm, never got a good SSH port opening!")
        exit(10)
    
    playbook_name = opts.playbook if opts.playbook else opts.app
    cmd = []
    cmd.append("ansible-playbook")
    cmd.append('-e'); cmd.append('spawner_env=' + opts.env)
    cmd.append('-l'); cmd.append(':'.join(hints['ips'].values())) # Limit to newly-created instances
    cmd.append(playbook_name + '.yml')

    logging.info("Running ansible as: {0}".format(' '.join(cmd)))
    
    os.execvp('ansible-playbook', cmd)
    

def spawn(hints, ec2):

    logging.info("About to launch {0} instance(s).  Press Control-C to abort!".format(hints['count']))
    for t in range(5,0,-1):
        logging.info("Launching in {0}...".format(t))
        time.sleep(1)
    profile_suffix = '' if hints['tags']['environment'] == 'prod' else '_' + hints['tags']['environment']
    instance_profile = hints['tags']['application'] + "_profile" + profile_suffix

    logging.info("OK, sending launch request!")
    # Make the reservation call.    
    if hints['public_ip']:
        # http://stackoverflow.com/questions/19029588/how-to-auto-assign-public-ip-to-ec2-instance-with-boto
        interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=hints['subnet_id'],
                                                                            groups=hints['security_group_ids'],
                                                                            associate_public_ip_address=True)
        interfaces = boto.ec2.networkinterface.NetworkInterfaceCollection(interface)
        reservation = ec2.run_instances(hints['ami_id'],
                                instance_type = hints['instance_type'],
                                network_interfaces=interfaces,
                                instance_profile_name = instance_profile,
                                )
    else:                
        reservation = ec2.run_instances(hints['ami_id'],
                                        min_count = hints['count'],
                                        max_count = hints['count'],
                                        instance_type = hints['instance_type'],
                                        subnet_id = hints['subnet_id'],
                                        security_group_ids = hints['security_group_ids'],
                                        instance_profile_name = instance_profile,
                                    )

    # Sleep a little bit.
    logging.info("Launch request sent.  Waiting for instances to be created...")
    time.sleep(5)
    reservation_id = reservation.id
    sentinel = 0
    while len(reservation.instances) != hints['count'] or [ i for i in reservation.instances if i.private_ip_address == None ]:
        print '.'
        time.sleep(2)
        sentinel = sentinel + 1
        if sentinel > 30:
            logging.error("Giving up!")
            exit(11)            
        reservation = ec2.get_all_reservations(filters={"reservation-id":reservation_id})        

    hints['ips'] = {}
    
    # Apply tags to the instances.
    for idx in range(0, len(hints['names'])):
        instance = reservation.instances[idx]
        logging.info ("Tagging instance {0} as {1}".format(instance.id, hints['names'][idx]))
        instance.add_tags(hints['tags'])
        instance.add_tag('Name', value = hints['names'][idx])
        # Store private IP by name
        hints['ips'][hints['names'][idx]] = instance.private_ip_address


        
def validate_request(opts, cfg, ec2_conn, vpc_conn):
    logging.info("Gathering info about your spawn request....")

    hints = {}
    hints['count'] = opts.count
    
    #------
    # Verify that requested app type exists in the config file
    #------
        
    matched_apps = [a for a in cfg['apps'] if a['name'] == opts.app]    
    if len(matched_apps) < 1:
        logging.error("I don't know anything about an application named {0}".format(opts.app))
        exit(2)
    if len(matched_apps) > 1:
        logging.error("App {0} appears more than once in spawner.yaml!".format(opts.app))
        exit(2)
    app_cfg = matched_apps[0]
    
    #------
    # Verify that no existing instances have names that will collide over the spawn range
    #------
    # TODO: consider examining DNS instead of / in addition to the AWS tags
    logging.debug("Generating names and checking for collisions")
    instance_tags = ec2_conn.get_all_tags({'resource-type':'instance'})
    existing_names = sorted([t.value for t in instance_tags if t.name == 'Name' and t.value.startswith('srl-' +  opts.app)])

    new_start = opts.begin if opts.begin else 1
    hints['names'] = ["srl-{0}-{1}".format(opts.app, str(i).zfill(3)) for i in range(new_start, opts.count + new_start)]
    intersection = sorted([ n for n in hints['names'] if n in existing_names])
    while len(intersection) != 0:
        if opts.begin:
            logging.error("A naming collision would exist for {0}. Consider the removing the -b option. You shall not pass.".format(','.join(intersection)))
            exit(3)
        else:
            new_start = int(intersection[-1][-3:]) + 1
            hints['names'] = ["srl-{0}-{1}".format(opts.app, str(i).zfill(3)) for i in range(new_start, opts.count + new_start)]
            intersection = sorted([ n for n in hints['names'] if n in existing_names])
                                    
    #------
    # Verify that AMI ID for that app type exists, and get tags
    #------
    amis = ec2_conn.get_all_images(owners=['self', '479572410002'])
    app_name = app_cfg.get('ami_app_name') if app_cfg.get('ami_app_name') else opts.app
    app_name = 'base' if opts.force_base_ami else app_name
    amis = [a for a in amis if a.tags.get('application') == app_name]
    if len(amis) < 1:
        logging.error("No AMIs have the tag application:{0} - you shall not pass.".format(app_name))
        exit(4)
    if opts.app_version:
        amis = [a for a in amis if a.tags.get('version') == opts.app_version]
        if len(amis) < 1:
            logging.error("No AMIs have the tags application:{0}, version:{1} - you shall not pass.".format(app_name, opts.app_version))
            exit(4)
        hints['app_version'] = opts.app_version
        ami = amis[0]
    else:
        amis.sort(key=lambda a: LooseVersion(a.tags.get('version')))
        ami = amis[-1]
        hints['app_version'] = ami.tags['version']
    
    hints['ami_id'] = ami.id

    logging.info("Using version {0} of ami_app_name {1} from AMI {2}".format(hints['app_version'], app_name, hints['ami_id']))
    
    # Copy out tags for the AMI
    hints['tags'] = {}
    for tn in ['version', 'tier']:
        if ami.tags.get(tn):
            hints['tags'][tn] = ami.tags[tn]
            
    # Regardless of what the AMI was, tag it according to the app and env that was requested
    hints['tags']['application'] = opts.app
    hints['tags']['environment'] = opts.env

    # If extra tags were provided, pass them on.
    if opts.extra_tag:
        (key, value) = opts.extra_tag.split(':')
        hints['tags'][key] = value
                        
    #------
    # Check VPC selection (via opts.vpc matching on VPC 'environment' tag)
    #------
    logging.debug("Verifying VPC selection")
    vpcs = vpc_conn.get_all_vpcs()
    selected_vpc = [v for v in vpcs if v.tags.get('Environment') == opts.env] # Note capitalization
    if len(selected_vpc) == 0 or len(selected_vpc) > 1:
        logging.error("Could not find a unique VPC tagged with the {0} environment - you shall not pass.".format(opts.env))
        exit(6)
    hints['vpc_id'] = selected_vpc[0].id
            
    #------
    # Map security group names to IDs
    #------
    # NOTE: Dev has no default VPC, so calling ec2_conn.get_all_security_groups(groupnames=[...]) fails with a "No Default VPC" error.  But, oddly, we CAN list all SG's.
    sgs = ec2_conn.get_all_security_groups()
    sgs = [sg for sg in sgs if sg.vpc_id == hints['vpc_id']]
    hints['security_group_ids'] = []
    for sgn in app_cfg['security_groups']:
        matched_sg = [sg for sg in sgs if sg.name == sgn]
        if len(matched_sg) == 1:
            hints['security_group_ids'].append(matched_sg[0].id)
        else:
            logging.error("Could not find a unique security group {0} in vpc {1} - you shall not pass.".format(sgn, hints['vpc_id']))
            exit(5)

        
    #------
    # Locate subnet within VPC using 'Tier' tag
    #------
    subnet_type = 'private' if not app_cfg.get('subnet_type') else app_cfg['subnet_type']
    subnets = vpc_conn.get_all_subnets()
    subnets = [s for s in subnets if s.vpc_id == hints['vpc_id']]
    subnets = [s for s in subnets if str(s.tags.get('Tier')).lower() == subnet_type.lower() ]

    if len(subnets) < 1 or len(subnets) > 1:
        logging.error("Could not find a unique Subnet tagged for the {0} tier in VPC {1} - you shall not pass.".format(subnet_type, hints['vpc_id']))
        exit(7)
    hints['subnet_id'] = subnets[0].id
                
    # TODO: Verify instance type ?
    hints['instance_type'] = app_cfg['instance_type']

    if app_cfg.get('public_ip') and hints['count'] > 1:
        logging.error("Refusing to assign public IPs to a multi-instance request, because that is hard.")
        exit(9)
    hints['public_ip'] = app_cfg.get('public_ip')
        

    if opts.run_ansible:
        playbook_name = opts.playbook if opts.playbook else opts.app
        offset = os.environ.get('SBAC_DEVOPS') if os.environ.get('SBAC_DEVOPS') else '..'
        path = offset + '/ansible/' + playbook_name + '.yml'
        if not os.path.isfile(path):
            logging.error("Could not find an Ansible playbook at {0}.  Either specify an alternate playbook with -p, or disable ansible with -s.  You shall not pass.".format(path))
            exit(8)
                    
    logging.info("Preflight looks good, you are cleared for launch attempt.")
    
    return hints

#=========================================================#
#                         Executor
#=========================================================#
main()
