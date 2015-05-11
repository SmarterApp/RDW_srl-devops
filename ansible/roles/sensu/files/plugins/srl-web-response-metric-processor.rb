#!/opt/sensu/embedded/bin/ruby
#  encoding: UTF-8
#
#   Reads apache response time info from STDIN, and updates a
# file with statistics about the moving percentiles.
#   Reports on a window over the last N samples.

STATS_FILE = '/var/log/sensu/httpd_response_time_stats.json'
IGNORE_URLS = [
  Regexp.new('/services/heartbeat'),
]
SAMPLE_COUNT = 100

require 'json'

def main()
  state = initial_state
  ARGF.each do |line|
    datapoint = split_line(line)
    if want_datapoint?(datapoint) then
      state = update_state(datapoint, state)
      update_stats_file(state)
    end
  end
end

def initial_state
  return (1..SAMPLE_COUNT).to_a.map { |e| 0 }
end

def split_line(line)
  parts = line.split(',')
  return {
    epoch: parts[0],
    status: parts[1].to_s,
    duration_usec: parts[2].to_i,
    url_path: parts[3]
  }
end

def want_datapoint?(datapoint)
  # Ignore all 4xx client errors
  if datapoint[:status].start_with?('4') then
    return false
  end
  
  IGNORE_URLS.each do |re|
    if re.match(datapoint[:url_path]) then
      return false
    end
  end
  
  return true
end

def update_state(datapoint, state)
  state.push(datapoint[:duration_usec])
  if state.length >= SAMPLE_COUNT then
    state = state.slice(1,SAMPLE_COUNT)
  end
  return state
end

def update_stats_file(state)
  info = {
    percentile_90: calc_percentile(state, 90),
    percentile_50: calc_percentile(state, 50),
    max: calc_max(state),
    average: calc_average(state),
  }
  json = JSON.generate(info)
  
  file = File.new(STATS_FILE, File::RDWR|File::CREAT, 0644)
  file.flock(File::LOCK_EX) # Reader plugin will flock
  File.truncate(STATS_FILE,0)
  file.write(json)
  file.flush
  file.flock(File::LOCK_UN)
  file.close
end

def calc_percentile(state, tile)
  idx = ((tile / 100.00) * state.length).to_i
  return state.sort[idx]
end

def calc_average (state)
  return state.inject{ |result, el| result + el } / state.length
end

def calc_max (state)
  return state.inject { |result, el| result > el ? result : el }
end

main()

