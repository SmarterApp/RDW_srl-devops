#!/usr/bin/env ruby

# Simple file to simulate the log output from Apache to test the concurrent session counter

prng = Random.new()

$stdout.sync = true

sessions = %w(
aaaaaaaaaaaaaa
bbbbbbbbbbbbbb
cccccccccccccc
dddddddddddddd
eeeeeeeeeeeeee
ffffffffffffff
)

while true do
  sleep(prng.rand(2.0))
  line = Time.now.to_i().to_s() + ',' + sessions[prng.rand(sessions.length)]
  $stderr.puts "Sending: #{line}"
  puts line
end
