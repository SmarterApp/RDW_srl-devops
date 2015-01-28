#!/usr/bin/python
__author__ = 'pyi'

import os.path
import boto
import boto.ec2.elb
import argparse
import sys

def main(opts):
    ec2connection = EC2connection()
    iam = IAMconnection()
    if opts.listinstance:
        try:
            ec2connection.get_instances_info(opts.instance)
        except UnboundLocalError:
            print "Incorrect value for instance or instance not found"
    elif opts.listeip:
        try:
            ec2connection.get_elastic_ip_info(opts.elasticip)
        except boto.exception.EC2ResponseError:
            print "Incorrect value for elasticip or elasticip not found"
    elif opts.listkeypair:
        ec2connection.get_key_pairs_info()
    elif opts.listloadbalancer:
        ec2connection.get_load_balancers_info()
    elif opts.listsecurity:
        try:
            ec2connection.get_security_groups_info(opts.securitygroup, opts.detail)
        except boto.exception.EC2ResponseError:
            print "Incorrect value for securitygroup or securitygroup not found"
    elif opts.listamis:
        ec2connection.get_ami_info()
    elif opts.listusers:
        try:
            iam.get_users(opts.user)
        except boto.exception.EC2ResponseError:
            print "Incorrect value for user or user not found"
    elif opts.listgroups:
        try:
            iam.get_groups(opts.group)
        except boto.exception.EC2ResponseError:
            print "Incorrect value for group or group not found"
    elif opts.listroles:
        iam.get_roles()
    elif opts.getgrouppolicy:
        if not opts.group or not opts.policy:
            print "-ggp requires --group and --policy arguments"
        else:
            try:
                iam.get_group_policy_info(opts.group[0],opts.policy[0])
            except boto.exception.EC2ResponseError:
                print "Incorrect value for group/policy or group/policy not found"
    elif opts.getrolepolicy:
        if not opts.role or not opts.policy:
            print "-grp requires --role and --policy arguments"
        else:
            try:
                iam.get_role_policy_info(opts.role[0],opts.policy[0])
            except boto.exception.EC2ResponseError:
                print "Incorrect value for role/policy or role/policy not found"


class EC2connection(object):

    def __init__(self):
        self.ec2 = boto.connect_ec2()
        self.instanceNameDict = self.get_instance_name_list()

    def get_instance_name_list(self):
        """creates a dictionary with instance id paired with name"""
        #Names are tags and associated with the instance object
        #Since instance objects will not be used in every method,
        #This dictionary will serve as a quick lookup between instance id and instance name
        instanceNameDict = {}
        #This will be deprecated and the method would be called get_all_instances in the future
        instances = self.ec2.get_only_instances()
        for i in instances:
            #Not all instances will have names(aka tags)
            try:
                name = i.tags['Name']
            except:
                name = 'None'
            insttag = i.id + ".alltags"
            instanceNameDict[i.id] = name
            instanceNameDict[insttag] = i.tags
        return instanceNameDict

    def get_security_group_id(self, groupname):
        """Returns group id of the security group when group name is given"""
        #AWS is retarded and doesnt like it when you filter by group name
        #Even though it is allowed and actually in the code
        groups = self.ec2.get_all_security_groups()
        for group in groups:
            if group.name == groupname:
                return group.id

    def get_instances_info(self, instance):
        """Prints instance name, id , state, ip and dns"""
        #Checks if a specific instance name was given
        #If none was given it will give info on all instances
        if instance:
            allinstances = self.ec2.get_only_instances()
            for i in allinstances:
                if "Name" in i.tags and instance[0] in i.tags['Name']:
                    instances = [i]
        else:
            instances = self.ec2.get_only_instances()
        for i in instances:
            name = self.instanceNameDict[i.id]
            insttag = i.id + ".alltags"
            tagstring = ""
            for istncetags in self.instanceNameDict[insttag].keys():
                tagstring = tagstring + istncetags + ":" + self.instanceNameDict[insttag][istncetags] + ";"
            tagstring = tagstring[:-1]
            print "Name: " + name + "| ID: "+ str(i.id) +\
                  " | State: " + str(i.state) +\
                  " | Type: " + str(i.instance_type) +\
                  " | Public IP: " + str(i.ip_address) +\
                  " | Public DNS: " + str(i.public_dns_name) +\
                  " | Private IP: " + str(i.private_ip_address) +\
                  " | Tags: [" + str(tagstring) + "]"

    def get_elastic_ip_info(self, eip=None):
        """Prints elastic ip and assocation if any"""
        eips = self.ec2.get_all_addresses(eip)
        for e in eips:
            print "elastic IP: " + str(e.public_ip) +\
                  " | Instance ID: " +str(e.instance_id) +\
                  " | Association ID: " +str(e.association_id)

    def get_key_pairs_info(self):
        """Prints Keypairs and Fingerprints """
        keypairs = self.ec2.get_all_key_pairs()
        for keypair in keypairs:
            print "Keypair Name: " +str(keypair.name)+\
                  " | Fingerprint: " +str(keypair.fingerprint)

    def get_load_balancers_info(self):
        """Prints loadbalancer names"""
        elbConnection = boto.ec2.elb.connect_to_region('us-east-1')
        load_balancers = elbConnection.get_all_load_balancers()
        for elb in load_balancers:
            print "Name: " +str(elb.name) +\
                  " | Listeners: " +str(elb.listeners) +\
                  " | Instances: " +str(elb.instances)
            for instance in elb.instances:
                print "Instance ID: " +str(instance.id)+\
                    " | Status: " +str(instance.state)

    def get_security_groups_info(self, group=None, detail=False):
        """Prints security group information and its rules"""
        #Checks if specific group or if detail level is called
        #Detail level will print with all the specific information given as if
        #a specific security group was given in the parameters
        if group:
            groupid = self.get_security_group_id(group[0])
            if groupid == None:
                print "Incorrect value for securitygroup or securitygroup not found"
                sys.exit()
        else:
            groupid = None
        securityGroups = self.ec2.get_all_security_groups(group_ids=groupid)
        for sg in securityGroups:
            if group or detail:
                print "Group ID: " +str(sg.id)+\
                      " | Name: " +str(sg.name)+\
                      " | Description: " +str(sg.description)
                print "Rules:"
                for rule in sg.rules:
                    print "Ip Protocol: " + str(rule.ip_protocol)+\
                          " | From Port: "+ str(rule.from_port)+\
                          " | To Port: "+ str(rule.to_port)+\
                          " | Grants: "+ str(rule.grants)
                print ""
            else:
                print " | Name: " +str(sg.name)+\
                      " | Description: " +str(sg.description)

    def get_ami_info(self):
        """Prints AMI information"""
        images = self.ec2.get_all_images(owners=["self"])
        print "==Private Images Owned by You=="
        for image in images:
            print "Name: " +str(image.name)+\
                  " | ID: " +str(image.id)+\
                  " | Source: " +str(image.location)+\
                  " | Owner: " +str(image.owner_alias)+\
                  " | Visibility: " +str(image.is_public)+\
                  " | Status: " +str(image.state)+\
                  " | Platform: " +str(image.platform)+\
                  " | Root Device Type: " +str(image.root_device_type)+\
                  " | Virtualization: " +str(image.virtualization_type)

    @staticmethod
    def check_config():
        """Checks if boto credentials are in the config file,
        will exit script if it doesn't exist"""
        #checks to see if aws config was setup with access key and secret key
        if os.path.exists(os.path.expanduser('~/.boto')):
            x_file = open(os.path.expanduser('~/.boto'), "r")
            if not x_file.readline()  == "[Credentials]\n":
                print "Boto config files need credential info"
                print "Please create .boto file with aws credentials"
                sys.exit()
        else:
            print "Boto config files need credential info"
            print "Please create .boto file with aws credentials"
            sys.exit()

class IAMconnection(object):
    def __init__(self):
        self.iam = boto.connect_iam()

    def get_users(self, user=None):
        """Returns IAM users and the groups that each user is in"""
        if not user:
            usersresponse = self.iam.get_all_users()
            users = usersresponse.get('list_users_response').get('list_users_result').get('users')
        else:
            usersresponse = self.iam.get_user(user[0])
            users = [usersresponse.get('get_user_response').get('get_user_result').get('user')]
        for user in users:
            print "Name: " + str(user.user_name)
            groups = self.iam.get_groups_for_user(user.user_name).get('list_groups_for_user_response')\
                    .get('list_groups_for_user_result').get('groups')
            print "Groups: "
            returnlist = []
            for group in groups:
                returnlist.append((group.group_name).encode("UTF-8"))
            print returnlist

    def get_groups(self, groupname=None):
        """Returns the group name and users within the group"""
        #Checks if specific group name is given
        #If specific group is not given it will return all groups
        if not groupname:
            groups = self.iam.get_all_groups().get('list_groups_response').get('list_groups_result').get('groups')
        else:
            groups = [self.iam.get_group(groupname).get('get_grEC2ResponseErroroup_response').get('get_group_result').get('group')]

        for group in groups:
            print "Group: " +str(group.group_name)
            print "Users: " +str(self.find_users_from_group(group.group_name))
            policies = (self.iam.get_all_group_policies(group.group_name)\
                                  .get('list_group_policies_response')\
                                  .get('list_group_policies_result')\
                                  .get('policy_names'))
            policylist =[]
            for policy in policies:
                policylist.append(policy.encode("UTF-8"))
            print "Policies: " +str(policylist) +"\n"
            
    def get_roles(self):
        """Returns roles and role policy names"""
        roles = self.iam.list_roles().get('list_roles_response').get('list_roles_result').get('roles')
        for role in roles:
            print "Role Name: " + str((role.role_name).encode("UTF-8"))
            role_policies = self.iam.list_role_policies(role.role_name).get('list_role_policies_response')\
                                .get('list_role_policies_result').get('policy_names')
            policy_list = []
            for policy in role_policies:
                 policy_list.append(policy.encode("UTF-8"))
            print "Role Policies: " + str(policy_list) +"\n"

    def get_group_policy_info(self, groupname, policyname):
        "Returns policy document for group policy"
        policyresponse = self.iam.get_group_policy(groupname,policyname)
        policy = policyresponse.get('get_group_policy_response').get('get_group_policy_result')
        print self.decode_policy_doc(policy.policy_document)

    def get_role_policy_info(self, rolename, policyname):
        """Returns policy document for role policy"""
        policyresponse = self.iam.get_role_policy(rolename, policyname)
        policy = policyresponse.get('get_role_policy_response').get('get_role_policy_result')
        print self.decode_policy_doc(policy.policy_document)

    def find_users_from_group(self, group):
        """Returns users from a specified group"""
        # aws boto doesnt have find users belonging to a group
        # had to makeshift my own =(
        userlist = []
        usersresponse = self.iam.get_all_users()
        users = usersresponse.get('list_users_response').get('list_users_result').get('users')
        for user in users:
            groups = self.iam.get_groups_for_user(user.user_name).get('list_groups_for_user_response')\
                    .get('list_groups_for_user_result').get('groups')
            for usergroup in groups:
                if group == usergroup.group_name:
                    userlist.append((user.user_name).encode("UTF-8"))
        return userlist

    def decode_policy_doc(self, hexstring):
        """returns an readable policy doc string"""
        # aws is retarded by giving a semi hex representation of the document policy
        # spaces and symbols are in hex but alpha characters and numbers are not
        hexstring = hexstring.encode('ascii')
        stringlist = []
        x = 0
        while x < hexstring.__len__():
            if hexstring[x]=="%":
                hexchars = str(hexstring[x+1])+str(hexstring[x+2])
                stringlist.append((hexchars).decode('hex'))
                x = x+2
            else:
                stringlist.append((hexstring[x]))
            x += 1
        return "".join(stringlist)




if __name__ == "__main__":
    argParser = argparse.ArgumentParser(description='Placeholder Text')
    argParser.add_argument('-li',dest='listinstance',action='store_true',\
            help='list instance', default=False)
    argParser.add_argument('-leip',dest='listeip',action='store_true',\
            help='list elastic ip', default=False)
    argParser.add_argument('-lkp',dest='listkeypair',action='store_true',\
            help='list key pair', default=False)
    argParser.add_argument('-llb',dest='listloadbalancer',action='store_true',\
            help='list load balancer', default=False)
    argParser.add_argument('-lsg',dest='listsecurity',action='store_true',\
            help='list security group', default=False)
    argParser.add_argument('-lami',dest='listamis',action='store_true',\
            help='list AMIs', default=False)
    argParser.add_argument('-lu', dest='listusers',action='store_true',\
            help='list users', default=False)
    argParser.add_argument('-lg', dest='listgroups',action='store_true',\
            help='list groups', default=False)
    argParser.add_argument('-lr', dest='listroles',action='store_true',\
            help='list roles', default=False)
    argParser.add_argument('-ggp', dest='getgrouppolicy', action='store_true',\
            help='get group policy', default=False)
    argParser.add_argument('-grp', dest='getrolepolicy', action='store_true',\
            help='get role policy', default=False)
    argParser.add_argument('--user', help='user', nargs='+')
    argParser.add_argument('--instance', help='instance', nargs='+')
    argParser.add_argument('--elasticip', help='elastic ip', nargs='+')
    argParser.add_argument('--securitygroup', help='security group', nargs='+')
    argParser.add_argument('--detail', help='detail level', action='store_true')
    argParser.add_argument('--group', help='group name', nargs='+')
    argParser.add_argument('--role', help='role name', nargs='+')
    argParser.add_argument('--policy', help='policy name', nargs='+')
    args = argParser.parse_args()
    #EC2connection.check_config()
    main(args)
