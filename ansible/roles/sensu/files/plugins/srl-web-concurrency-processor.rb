#!/opt/sensu/embedded/bin/ruby
#  encoding: UTF-8
#
#   Reads apache response time info from STDIN, and updates a
# file with statistics about the moving percentiles.
#   Reports on a window over the last N samples.

STATS_FILE = '/var/log/sensu/httpd_session_concurrency_stats.json'
WINDOW_LENGTH = 300

require 'json'

def main()
  state = initial_state
  last_write_out = Time.now
  
  $stdin.each_line do |line|
    datapoint = split_line(line)
    state = add_point_to_state(datapoint, state)
    
    # Only write out update every so often to avoid hammering the filesystem
    if last_write_out + WINDOW_LENGTH/2 < Time.now then      
      state = cull_stale_state(state) # possible memory issue during heavy traffic
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

def split_line(line)
  parts = line.split(',')
  return {
    epoch: parts[0],
    session: parts[1]   # TODO - need to identify actual cookie format, see if we need to parse it
  }
end

def add_point_to_state(datapoint, state)

  # Create a slot for the timestamp if it doesn't exist
  state[datapoint[:epoch]] ||= {}

  # Record that a particular session ID was seen
  state[datapoint[:epoch]][datapoint[:session]] = 1
  
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

