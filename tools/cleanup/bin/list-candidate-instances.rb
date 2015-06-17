#!/usr/bin/env ruby

require 'json'


class CandidateLister
  def initialize
    # Identify the environment
    @env_name = ENV['SBAC_ENV'].split('/')[0]
    @data_path = ENV['HOME'] + '/srl-devops/tools/cleanup/data/' + @env_name + '/'

    @instances = []
    
    # Decide which filter we are using
    # @filter =
    # TODO - command-line args parse to select filter
    @pipecmd = 'grep InstanceProfile'
    @filter = 'select(.IamInstanceProfile.Arn|endswith("s3yum_access"))'   
    # @filter = 'select(.State.Name == "stopped")'
    # @pipecmd = 'cat'
    
  end
  
  def run
    # Extract the instances using the filter and inflate to POROs
    load_instances
    @instances.each do |instance|
      # For each instance, lookup the creator and inject
      inject_creator_into_instance(instance)
    end

    # Sort instances by creator username, then by creation time
    sort_instances()

    @instances.each do |instance|
      #    print instance ID, name, creator, datetime
      msg = ""
      msg += instance['InstanceId'] + ','
      msg += get_tag('Name', instance) + ','
      msg += get_tag('environment', instance) + ','
      msg += get_creator_username(instance) + ','
      msg += get_creation_time(instance)

      puts msg
    end
  end


  def load_instances    
    `#{@pipecmd} #{@data_path}instances.all | jq -c '#{@filter}' `.each_line do |line|
      # puts line
      @instances.push(JSON.parse(line))
    end
  end

  def inject_creator_into_instance(instance)
    # Search for creation event
    instance_id = instance['InstanceId']
    line = `grep #{instance_id} #{@data_path}events.all | grep RunInstances`
    line.chomp!
    if line.empty?
      $stderr.puts "WARN: no RunInstances event for #{instance_id}"
    else
      instance['LaunchEvent'] = JSON.parse(line)
    end
  end

  def get_tag(tagname, instance)
    return '' unless instance['Tags']
    tag = instance['Tags'].find {|t| t['Key'] == tagname}
    return '' unless tag 
    return tag['Value']
  end
  
  def get_creator_username(instance)
    obj = instance
    obj = obj['LaunchEvent']
    return '' unless obj
    obj = obj['userIdentity']
    obj = obj['userName']
    return obj
  end

  def get_creation_time(instance)
    obj = instance
    obj = obj['LaunchEvent']
    return '' unless obj
    obj = obj['eventTime']
    return obj
  end

  def sort_instances
    @instances = @instances.sort do |a,b|
      next 0 if !a['LaunchEvent'] && !b['LaunchEvent']
      next -1 unless a['LaunchEvent']
      next 1 unless b['LaunchEvent']
      userSort = a['LaunchEvent']['userIdentity']['userName'] <=> b['LaunchEvent']['userIdentity']['userName']
      next userSort unless userSort == 0
      
      #next 0 if !a['LaunchEvent']['eventTime'] && !b['LaunchEvent']['eventTime']
      #next -1 unless a['LaunchEvent']['eventTime']
      #next 1 unless b['LaunchEvent']['eventTime']
      next a['LaunchEvent']['eventTime'] <=> b['LaunchEvent']['eventTime']        
    end
  end
  
end

CandidateLister.new().run()
