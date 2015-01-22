# How to setup password caching

This will show you how to set things up so that your ansible vault password will be cached for you securely.

## Setup a GPG key, if you don't already have one.

From https://www.madboa.com/geek/gpg-quickstart/ :

gpg --gen-key

Accept defaults.  Set key comment to "SBAC-devops-key".

When challenged for a passphrase, enter a passphrase you will remember.
This is how you will unlock your password store.

## Setup gpg-agent to run

From https://wiki.archlinux.org/index.php/GnuPG#gpg-agent

Tell gpg to rely on the agent:

>  echo 'use-agent' >> ~/.gnupg/gpg.conf

Append this to your .bash_profile to start the agent at login:


> envfile="$HOME/.gnupg/gpg-agent.env"
> if [[ -e "$envfile" ]] && kill -0 $(grep GPG_AGENT_INFO "$envfile" | cut -d: -f 2) 2>/dev/null; then
>     eval "$(cat "$envfile")"
> else
>     eval "$(gpg-agent --daemon --write-env-file "$envfile")"
> fi
> export GPG_AGENT_INFO  # the env file does not contain the export statement

The default cache life is 600 seconds.  To change that, edit ~/.gnupg/gpg-agent.conf :

> default-cache-ttl 3600

Re-source your bash profile to start the agent.

> source ~/.bash_profile

## Setup a password store.

From http://www.passwordstore.org/ :

> pass init "SBAC-devops-key"

## Add your Secrets

### Adding your AWS credentials

> pass insert dev/aws/access_id

When prompted for the "password", paste in your AWS access ID.
You won't be challenged for your password store passphrase at this point.

Verify the access ID:

> pass dev/aws/access_id

The first time you do this, you will be challenged for your password store passphrase.

Run this again to verify that your password store passphrase has been cached by the GPG agent:

> pass dev/aws/access_id

Finally, add your secret key as well:

> pass insert dev/aws/secret_key

### Add the ansible vault key

pass insert ansible/vault

## Feeding the vault password to ansible

You can feed the vault password to Ansible like this:

ansible-vault view --vault-password-file=$SBAC_DEVOPS/tools/read-vault-pass.sh

Or, you can place that in ansible.cfg :

> # Adjust path as needed
> vault_password_file=../tools/read-vault-pass.sh


## Accessing AWS creds within Ansible

You can set the output of a command like so:

# TODO: verify this is a local action

>  aws_access_id: {{ lookup('pipe', 'pass dev/aws/access_id') }}

Or "register" a variable by running a command locally

>  - name: "Read AWS Access ID"
>    local_action: command pass aws/access_id
>    register: my_aws_access_id
