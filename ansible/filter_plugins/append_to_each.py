
# Append a string to each element of the array
def append_to_each(arr, string):
    return [str(el) + string for el in arr]

def instance_id_2_node_id(arg):
    return int(arg[2:], 16)

def first(arg):
    if len(arg) > 0:
        return arg[0]
    else:
        return None

# Return a host-unique number that doesn't change often
# Used for staggering cronjobs
def stagger_from_mac(mac_addr, limit):
     last_octet = int('0x' + mac_addr.split(':')[-1], 16)
     return int((last_octet / 255.0) * limit)
    
def srl_hostvars_lookup(hostvars, ip):
    # ip might be None, or missing
    # hostvars is a dict-like object that lies - keys() and get() operate on a different keyset than [ ]
    # such hate
    try:
        if ip is not None:
           info = hostvars[ip]
           return info
        else:
           return { 'ec2_tag_Name': 'dummy' }
    except:
        # OK, no host with that IP.
        # Return a dummy hash.
        return { 'ec2_tag_Name': 'dummy' }
    
class FilterModule(object):
    ''' Ansible custom jinja2 filters '''
    def filters(self):
        return {
            'append_to_each': append_to_each,
            'first': first,
            'instance_id_2_node_id': instance_id_2_node_id,
            'srl_hostvars_lookup': srl_hostvars_lookup,
            'stagger_from_mac': stagger_from_mac,
        }
