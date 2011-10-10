#!/usr/bin/ruby

$stdout.sync = true

require 'rubygems'   # for nokigiri to work on all machines, and for JSON/Iconv on OSX
require 'json'
require 'date'
require 'iconv'
require 'optparse'
require	'scraperwiki'
require 'scraperwiki/datastore'
require 'scraperwiki/stacktrace'
require "base64"

$logfd  = $stderr

class ConsoleStream
    def initialize(fd)
        @fd   = fd
        @text = ''
    end

    # Do our best to turn anything into unicode, for display on console
    # (for datastore, we give errors if it isn't already UTF-8)
    def saveunicode(text)
        begin
            text = Iconv.conv('utf-8', 'utf-8', text)
        rescue Iconv::IllegalSequence
            begin
                text = Iconv.conv('utf-8', 'iso-8859-1', text)
            rescue Iconv::IllegalSequence
                text = Iconv.conv('utf-8//IGNORE', 'utf-8', text)
            end
        end
        return text
    end

    def write(text)
        @text = @text + saveunicode(text)
        if @text.length > 0 && @text[-1] == "\n"[0]
            flush
        end
    end

    def <<(text)
       write text
    end

    def flush
      if @text != ''
          ScraperWiki.dumpMessage( { 'message_type' => 'console', 'content' => @text }  )
          @fd.flush
          @text = ''
      end
    end

    def close
        @fd.close()
    end
end

$stdout = ConsoleStream.new($logfd)
$stderr = ConsoleStream.new($logfd)

Process.setrlimit(Process::RLIMIT_CPU, 80, 82) 
 
Signal.trap("XCPU") do
    raise Exception, "ScraperWiki CPU time exceeded"
end


options = {}
OptionParser.new do|opts|
   opts.on( '--script=[SCRIPT]') do|script|
     options[:script] = script
   end
end.parse(ARGV)

datastore = nil
scrapername = nil
querystring = nil
runid = nil
attachables = nil
webstore_port = nil
File.open( File.dirname(options[:script]) +  "/launch.json","r") do |f|
  results = JSON.parse( f.read )
  datastore = results['datastore']
  runid     = results['runid']
  querystring = results['querystring']
  scrapername = results['scrapername']
  attachables = results['attachables']
  webstore_port = results['webstore_port']
end


unless querystring.nil? || querystring == ''
     ENV['QUERY_STRING'] = querystring
     ENV['URLQUERY'] = querystring
end

host, port = datastore.split(':')
SW_DataStore.create(host, port, scrapername, runid, attachables, webstore_port)

code = File.new(options[:script], 'r').read()
begin
    #eval code # this doesn't give you line number of top level errors, instead we use require_relative:
    require options[:script]
rescue Exception => e
    est = getExceptionTraceback(e, code, options[:script])
    # for debugging:
    # File.open("/tmp/fairuby", 'a') {|f| f.write(JSON.generate(est)) }
    ScraperWiki.dumpMessage(est)
end

$stdout.flush
$stderr.flush
