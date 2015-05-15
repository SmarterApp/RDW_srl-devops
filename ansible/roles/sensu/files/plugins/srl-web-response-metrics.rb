#!/usr/bin/env ruby
#  encoding: UTF-8
#
#   srl-web-response-metrics
#
# DESCRIPTION:
#   Reads sumamrized apache web response time data and passes it to sensu
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
#   script: srl-web-response-metric-processor.rb
#
# USAGE:
#
# NOTES:
#

STATS_FILE = '/var/log/sensu/httpd_response_time_stats.json'

require 'sensu-plugin/metric/cli'
require 'socket'
require 'json'

class MemoryGraphite < Sensu::Plugin::Metric::CLI::Graphite
  option :scheme,
         description: 'Metric naming scheme, text to prepend to metric',
         short: '-s SCHEME',
         long: '--scheme SCHEME',
         default: "middleware.httpd.#{Socket.gethostname}.response_usec"

  def run
    metrics = read_stats_file

    metrics.each do |k, v|
      output "#{config[:scheme]}.#{k}", v
    end

    ok
  end

  def read_stats_file
    file = File.new(STATS_FILE,'r')
    file.flock(File::LOCK_SH)
    json = file.read
    file.flock(File::LOCK_UN)
    file.close
    return JSON.load(json)
  end
end
