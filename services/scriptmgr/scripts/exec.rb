#!/usr/bin/ruby1.9.1

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
    
    def tty?
      return false 
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

Process.setrlimit(Process::RLIMIT_CPU, 160, 162) 
 
Signal.trap("XCPU") do
    raise ScraperWiki::CPUTimeExceededError, "ScraperWiki CPU time exceeded"
end


options = {}
OptionParser.new do|opts|
   opts.on( '--script=[SCRIPT]') do |script|
     options[:script] = script
   end
   opts.on('--scraper=[name]') do |name|
     # nothing to do
   end
end.parse(ARGV)

datastore = nil
scrapername = nil
querystring = nil
runid = nil
attachables = nil
verification_key = nil

File.open( File.dirname(options[:script]) +  "/launch.json","r") do |f|
  results = JSON.parse( f.read )
  datastore = results['datastore']
  runid     = results['runid']
  querystring = results['querystring']
  scrapername = results['scrapername']
  attachables = results['attachables']
  verification_key = results['verification_key']
end

ENV['REQUEST_METHOD'] = "GET"

unless verification_key.nil? || verification_key == ''
    ENV['VERIFICATION_KEY'] = verification_key
end

unless querystring.nil? || querystring == ''
     ENV['QUERY_STRING'] = querystring
     ENV['URLQUERY'] = querystring
end

host, port = datastore.split(':')
SW_DataStore.create(host, port, scrapername, runid, attachables,verification_key)

# Searches for encoding line and forces encoding
# @see https://github.com/lsegal/yard/blob/master/lib/yard/parser/source_parser.rb#L469
ENCODING_LINE = /\A(?:\s*#*!.*\r?\n)?\s*(?:#+|\/\*+|\/\/+).*coding\s*[:=]{1,2}\s*([a-z\d_\-]+)/i
# Byte order marks for various encodings
ENCODING_BYTE_ORDER_MARKS = {
  'utf-8' => "\xEF\xBB\xBF",
  # Not yet supported
  #'utf-16be' => "\xFE\xFF",
  #'utf-16le' => "\xFF\xFE",
  #'utf-32be' => "\x00\x00\xFF\xFE",
  #'utf-32le' => "\xFF\xFE",
}
def convert_encoding(content)
  return content unless content.respond_to?(:force_encoding)
  if content =~ ENCODING_LINE
    content.force_encoding($1)
  else
    old_encoding = content.encoding
    content.force_encoding('binary')
    ENCODING_BYTE_ORDER_MARKS.each do |encoding, bom|
      bom.force_encoding('binary')
      if content[0,bom.size] == bom
        content.force_encoding(encoding)
        return content
      end
    end
    content.force_encoding(old_encoding)
    content
  end
end

code = convert_encoding(File.open(options[:script], 'rb') {|f| f.read})
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
