#!/usr/bin/env ruby

require 'json'

class OrphanVolumeLister
  def initialize
    @env_name = ENV['SBAC_ENV'].split('/')[0]
    @data_path = ENV['HOME'] + '/srl-devops/tools/cleanup/data/' + @env_name + '/'

    # Decide which filter we are using
    # @filter =
    # TODO - command-line args parse to select filter
    # @instance_filter = 'select(.State.Name == "stopped")'
    @instance_filter = 'select(1 == 1)'
    @volume_filter = 'select(1 == 1)'
    
    load_volumes()
    load_instances()
  end
  
  def run

    total_size = 0
    
    # For each attachvolume event
    `grep AttachVolume #{@data_path}events.all`.each_line do |line|
      evt = JSON.parse(line)
      vol_id = evt['requestParameters']['volumeId']
      inst_id = evt['requestParameters']['instanceId']
      
      #  if the volume still exists
      next unless @volumes[vol_id]

      #puts 'have a vol!'
      
      #  and if the instance does NOT still exist
      next if @instances[inst_id]
      #puts 'have an inst!'
      
      # and if the volume is not now attached to something else
      next unless @volumes[vol_id]['Attachments'].length == 0
      #puts 'have no attachments!'
      
      # consider it an orphan
      puts vol_id
      total_size += @volumes[vol_id]['Size']
      
    end

    $stderr.puts total_size.to_s + 'GB'
    
  end

  def load_instances
    @instances = {}
    `jq -c '#{@instance_filter}' < #{@data_path}instances.all`.each_line do |line|
      inst = JSON.parse(line)
      @instances[inst['InstanceId']] = inst
    end
  end

  def load_volumes
    @volumes = {}
    `jq -c '#{@volume_filter}' < #{@data_path}volumes.all`.each_line do |line|
      vol = JSON.parse(line)
      @volumes[vol['VolumeId']] = vol
    end
  end
  
end

OrphanVolumeLister.new().run()


