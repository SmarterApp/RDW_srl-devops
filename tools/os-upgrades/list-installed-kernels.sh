cd $SBAC_DEVOPS/ansible

for IP in $(inventories/srl.py | jq -r '.test186|.[]' | grep -v 10.186.49.194); do
    echo -n $IP,; ssh ansible@$IP 'rpm -q kernel | sort | tr "\\n" ":" | sed -e "s/:\$/\n/"'
done
