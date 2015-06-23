
require 'csv'
require 'date'

class MonthlyReport
  WHISPER_PATH='/opt/carbon/whisper/'
  CSV_PATH='/tmp/'

  def initialize
    
    # TODO _ read these from CLI
    @from_sec_ago = 30 * 60*60*24
    @until_sec_ago = 0
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
