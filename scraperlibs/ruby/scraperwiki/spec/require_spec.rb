require File.dirname(__FILE__) + '/helper'

WebMock.allow_net_connect!

describe Kernel do
  context "When we include scraper_require" do
    before do
      require File.dirname(__FILE__) + '/../lib/scraperwiki/scraper_require'
    end

    context "When we require a Ruby scraper" do
      before do
        @scraper_name = 'test_require'
        require "scrapers/#{@scraper_name}"
      end

      it "fetches the scraper's code from ScraperWiki" do
        a_request(:get, "https://scraperwiki.com/editor/raw/#{@scraper_name}").should have_been_made
      end

      it "can call the 'hello' method of the included code" do
        hello.should == 'world'
      end

      it "find the class TestClass and can call its methods" do
        TestClass.should_not be_nil
        TestClass.test.should == 'self test'
        t = TestClass.new
        t.test.should == 'test'
      end

    end

    context "When we require a Python scraper" do
      it "should raise a LoadError" do
        lambda { require "scrapers/wirral-globe-letters-scraper-newsquest" }.should raise_error LoadError
      end
    end

    context "When we require something that is not a scraper" do
      it "loads the module if it exists" do
        require 'time'
      end

      it "raises a LoadError if it does not exist" do
        lambda { require 'bobalobablob' }.should raise_error LoadError
      end
    end
  end
end

