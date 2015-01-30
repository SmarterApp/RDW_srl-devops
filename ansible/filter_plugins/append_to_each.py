
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

def srl_hostvars_lookup(hostvars, ip):
    # ip might be None, or missing
    # hostvars is a dict-like object that lies - keys() and get() operate on a different keyset than [ ]
    # such hate
    try:
        info = hostvars[ip]
        return info
    except AnsibleError:
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
        }
