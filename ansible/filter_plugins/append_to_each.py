
# Append a string to each element of the array
def append_to_each(arr, string):
    return [str(el) + string for el in arr]


class FilterModule(object):
    ''' Ansible custom jinja2 filters '''
    def filters(self):
        return {
            'append_to_each': append_to_each,
        }
