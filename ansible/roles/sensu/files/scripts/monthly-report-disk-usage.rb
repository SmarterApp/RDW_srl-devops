#!/opt/sensu/embedded/bin/ruby

# This script will create a csv file with the daily max of disk usage
#    for servers monitored on this sensu server '''

require 'date'
require 'csv'

class DiskUsageReport

  WHISPER_PATH='/opt/carbon/whisper/'
  CSV_PATH='/tmp/'
  
  def initialize
    # by day, by server type, by server-mount = max usage over the day
    @usage = {}

    # TODO _ read these from CLI
    @from_sec_ago = 30 * 60*60*24
    @until_sec_ago = 0
    
    @glob_for_app_class = {
      :gluster => 'sys/srl-gluster-server-???/disk/by_mount/*/used_mb.wsp',
      # On database servers, we only want mounts that are the data dir - which varies :(
      :db => 'sys/srl-*db*-???/disk/by_mount/_mnt_*/used_mb.wsp',
      :extract => 'sys/srl-*extract*-???/disk/by_mount/_mnt_*/used_mb.wsp',
    }
  end
    
  def run()
    # for each app class
    @glob_for_app_class.each do |app_type, whisper_glob|
      # list whisper files for the app class
      list_whisper_files(whisper_glob).each do |whisper_filename|
        server_mount = whisper_filename.split('/')[5] + ':' + whisper_filename.split('/')[8].gsub!('_','/')
        puts server_mount
        
        # run whisper-fetch on the file
        whisper_fetch(whisper_filename) do |data|
          # add line data to usage, maxing along the way
          @usage[data[:date]] ||= {}
          @usage[data[:date]][app_type] ||= {}
          @usage[data[:date]][app_type][server_mount] ||= 0
          @usage[data[:date]][app_type][server_mount] = [data[:value], @usage[data[:date]][app_type][server_mount]].max()
        end

      end
    end

    CSV.open(CSV_PATH + 'disk-usage.csv', 'wb') do |csv|
      # Emit CSV header
      csv << ['Date'] + @glob_for_app_class.keys.sort

      # for each day
      @usage.keys.sort.each do |date|
        row = [date]
        
        # for each app class
        @glob_for_app_class.keys.sort.each do |app_type|
          # Add the max of each mount for that day
          sum = 0
          if @usage[date][app_type]
            @usage[date][app_type].values.each {|v| sum += v }
          end
          row << sum
        end
        csv << row
      end

    end
  end
  
  def whisper_fetch(filename)
    epoch_start = Time.now.to_i - @from_sec_ago
    epoch_end = Time.now.to_i - @until_sec_ago
    `whisper-fetch --from #{epoch_start} --until #{epoch_end} #{filename} | grep -v None`.each_line do |line|
      line.chomp!
      next if line.empty?
      match = /(\d+)\s+(\d+\.?\d*)/.match(line)
      next unless match
      epoch = match[1]
      value = match[2].to_f
      date = DateTime.strptime(epoch, '%s').strftime('%F')
      yield({epoch: epoch, value: value, date: date})      
    end
  end
  
  def list_whisper_files(glob)
    # stat filename and filter out any that have not been updated in our window of interest
    return Dir.glob(WHISPER_PATH + glob).reject do |filename|
      File::Stat.new(filename).mtime.to_i < (Time.now.to_i - @from_sec_ago)
    end.sort
  end
  
end

DiskUsageReport.new().run()
