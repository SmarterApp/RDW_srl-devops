#!/opt/sensu/embedded/bin/ruby

# This script will create a csv file with the daily max of concurrent sessions
#    for servers monitored on this sensu server '''

require_relative './monthly-report.rb'

class ConcurrentSessionsReport < MonthlyReport

  def initialize
    super
    # by day, by server instance = max of concurrent user count
    @sessions = {}

    @glob = '/middleware/httpd/srl-reporting-web-???/concurrency/concurrent_sessions_300_sec_window.wsp'
  end
    
  def run()
    # list whisper files for the concurrent sessions
    list_whisper_files(@glob).each do |whisper_filename|
      server_name = whisper_filename.split('/')[7]
      puts server_name
        
      # run whisper-fetch on the file
      whisper_fetch(whisper_filename) do |data|
        # add line data to session tracker, maxing along the way
        @sessions[data[:date]] ||= {}
        @sessions[data[:date]][server_name] ||= 0
        @sessions[data[:date]][server_name] = [data[:value], @sessions[data[:date]][server_name]].max()
      end

    end

    CSV.open(CSV_PATH + 'concurrent-sessions.csv', 'wb') do |csv|
      # Emit CSV header
      csv << ['Date', 'Session Count']
      
      # for each day with data
      @sessions.keys.sort.each do |date|
        row = [date]
        
        # Max across all servers, 0 if no servers reporting
        row << (@sessions[date].values << 0).max()
        
        csv << row
      end
    end
  end
end

ConcurrentSessionsReport.new().run()
