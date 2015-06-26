#!/opt/sensu/embedded/bin/ruby

# This script will create a csv file with the daily average of 90th percentile web response time
#    for servers monitored on this sensu server '''

require_relative './monthly-report.rb'

class WebResponseReport < MonthlyReport

  def initialize
    super
    # by day, by server instance = { sum: N, count: N }
    @responses = {}

    @glob = '/middleware/httpd/srl-reporting-web-???/response_usec/percentile_90.wsp'
  end
    
  def run()
    # list whisper files for the web response time metrics
    list_whisper_files(@glob).each do |whisper_filename|
      server_name = whisper_filename.split('/')[7]
      puts server_name
        
      # run whisper-fetch on the file
      whisper_fetch(whisper_filename) do |data|
        # add line data to response tracker, accumulating data for averaging along the way
        @responses[data[:date]] ||= {}
        @responses[data[:date]][server_name] ||= { sum: 0, count: 0 }
        @responses[data[:date]][server_name][:count] += 1
        @responses[data[:date]][server_name][:sum] += data[:value]
      end

    end

    CSV.open(CSV_PATH + 'web-response.csv', 'wb') do |csv|
      # Emit CSV header
      csv << ['Date', 'Avg of 90th Percentile Response time (microseconds)']
      
      # for each day with data
      @responses.keys.sort.each do |date|
        row = [date]

        per_server_averages = @responses[date].values.map do |server_data|
          if server_data[:count] > 0
            server_data[:sum] / server_data[:count]
          else
            0
          end
        end

        overall_average = per_server_averages.reduce {|acc,el| acc+el} / per_server_averages.length
        
        # Average across all servers, 0 if no servers reporting
        row << overall_average
        
        csv << row
      end
    end
  end
end

WebResponseReport.new().run()
