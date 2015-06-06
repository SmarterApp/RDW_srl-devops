#!/usr/bin/env ruby
#  encoding: UTF-8
#
#   srl-web-concurrency-metrics
#
# DESCRIPTION:
#   Reads sumamrized apache concurrent session data and passes it to sensu
#
# OUTPUT:
#   metric data
#
# PLATFORMS:
#   Linux
#
# DEPENDENCIES:
#   gem: sensu-plugin
#   gem: socket
#   script: srl-web-concurrency-processor.rb
#
# USAGE:
#
# NOTES:
#

STATS_FILE = '/var/log/sensu/httpd_session_concurrency_stats.json'  # TODO: DRY this up
WINDOW_LENGTH = 300  # TODO: DRY this up


require 'sensu-plugin/metric/cli'
require 'socket'
require 'json'

class MemoryGraphite < Sensu::Plugin::Metric::CLI::Graphite
  option :scheme,
         description: 'Metric naming scheme, text to prepend to metric',
         short: '-s SCHEME',
         long: '--scheme SCHEME',
         default: "middleware.httpd.#{Socket.gethostname}.concurrency"

  def run
    metrics = read_stats_file

    metrics.each do |k, v|
      output "#{config[:scheme]}.#{k}", v
    end

    ok
  end

  def read_stats_file

    # If apache has never received a request, then the file won't exist.
    # That's odd, and might indicate a malfunctioning server.
    unless File.exists?(STATS_FILE) then
      $stderr.puts "#{STATS_FILE} does not exist - exiting"
      exit(3) # exit code 3 is nagios/sensu check speak for "indeterminate result"
    end
    
    # We need to figure out if the data is stale.  Apache will only
    # send an update when it actually gets a request, so if it doesn't get a
    # request within the time window, the data is stale - and we know the
    # concurrent session count must be zero.

    last_modified_time = File::Stat.new(STATS_FILE).mtime
    too_old = Time.new - WINDOW_LENGTH
    if last_modified_time < too_old then
      key = ('concurrent_sessions_' + WINDOW_LENGTH.to_s + '_sec_window').to_sym

      # Stale file, must not have been any requests in the last WINDOW_LENGHT seconds - so, 0 concurrent sessions.
      return { key => 0 }
    else 
      file = File.new(STATS_FILE,'r')
      file.flock(File::LOCK_SH)
      json = file.read
      file.flock(File::LOCK_UN)
      file.close
      return JSON.load(json)
    end
  end
end
