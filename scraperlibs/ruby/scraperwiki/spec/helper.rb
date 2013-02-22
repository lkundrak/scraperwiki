$LOAD_PATH.unshift File.dirname(__FILE__) + '/..'
 
require 'rspec'
require 'scraperwiki'
require 'vcr'
require 'webmock/rspec'
require 'bourne'

RSpec.configure do |c|
	c.mock_framework = :mocha
end

VCR.config do |c|
  c.cassette_library_dir = 'spec/fixtures/vcr_cassettes'
  c.stub_with :webmock
end

