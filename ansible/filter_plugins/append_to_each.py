
# Append a string to each element of the array
def append_to_each(arr, string):
    return [str(el) + string for el in arr]

def instance_id_2_node_id(arg):
    return int(arg[2:], 16)

class FilterModule(object):
    ''' Ansible custom jinja2 filters '''
    def filters(self):
        return {
            'append_to_each': append_to_each,
            'instance_id_2_node_id': instance_id_2_node_id,
        }
