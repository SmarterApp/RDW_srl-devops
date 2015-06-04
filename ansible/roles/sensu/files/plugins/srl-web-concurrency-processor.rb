#!/opt/sensu/embedded/bin/ruby
#  encoding: UTF-8
#
#   Reads apache response time info from STDIN, and updates a
# file with statistics about the moving percentiles.
#   Reports on a window over the last N samples.

STATS_FILE = '/var/log/sensu/httpd_session_concurrency_stats.json'
WINDOW_LENGTH = 300

require 'json'
require 'base64'

def main()
  state = initial_state
  last_write_out = Time.now
  
  $stdin.each_line do |line|
    datapoint = parse_line(line)
    next unless datapoint
    
    state = add_point_to_state(datapoint, state)
    
    # Only write out update every so often to avoid hammering the filesystem
    if true or last_write_out + WINDOW_LENGTH/2 < Time.now then      
      state = cull_stale_state(state) # possible memory issue during heavy traffic
      # puts "Session:" + datapoint[:session_id]
      # puts "Concurrency: " + count_concurrrent_sessions(state).to_s
      update_stats_file(state)
      last_write_out = Time.now
    end    
  end
end

def initial_state
  # State is an hash of data points, keyed by epoch
  # each element is a hash of session_ids seen at that timestamp
  return {}
end

def parse_line(line)
  parts = line.chomp.split(',')

  # If no cookie, apache, sends a '-'
  return nil if parts[1] == '-'

  # Otherwise, the value is a b64 encoded binary blob
  # The value looks like this initially (slashes are literally present)
  # \"a3ef3d327bf7faf064063ee2f6c080a821fa58aa5a54cf68f0ed2105c505cdcde336986a61e73457b02c33ace83ec84478023aebdaca596d991bca8d5278b01f55662216MDljNzlhNWQtZjE4OS00YWRlLWEwMTktN2U2Y2QyYzg2NzIw!userid_type:b64unicode\"

  match = /\\"(.+)\!userid.+/.match(parts[1])
  return nil unless match
  blob = Base64.decode64(match[1])
  
  # Within that opaque blob is a GUID as a string - we assume it is the session ID?
  match = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.match(blob)
  return nil unless match
  session_id = match[1]

  return {
    epoch: parts[0],
    session_id: session_id
  }
end

def add_point_to_state(datapoint, state)

  # Create a slot for the timestamp if it doesn't exist
  state[datapoint[:epoch]] ||= {}

  # Record that a particular session ID was seen
  state[datapoint[:epoch]][datapoint[:session_id]] = 1
  
  return state
end

def cull_stale_state(state)
  oldest_allowed = Time.now.to_i() - WINDOW_LENGTH
  state.reject! { |time, sessions| time.to_i < oldest_allowed }
  return state
end

def update_stats_file(state)


  key = ('concurrent_sessions_' + WINDOW_LENGTH.to_s + '_sec_window').to_sym
  json = JSON.generate({
                         key => count_concurrrent_sessions(state)
                       })

  
  file = File.new(STATS_FILE, File::RDWR|File::CREAT, 0644)
  file.flock(File::LOCK_EX) # Reader plugin will flock
  File.truncate(STATS_FILE,0)
  file.write(json)
  file.flush
  file.flock(File::LOCK_UN)
  file.close
end

def count_concurrrent_sessions(state)
  unique_sessions = {}
  state.values.each do |sessions_at_this_timestamp|
    sessions_at_this_timestamp.keys.each do |session_id|
        unique_sessions[session_id] = 1
    end
  end

  return unique_sessions.size
end

main()

