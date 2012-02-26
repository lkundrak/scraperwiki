require 'json'
require	'uri'
require	'net/http'
require 'scraperwiki/datastore'
require 'httpclient'

class SqliteException < RuntimeError
end

class NoSuchTableSqliteException < SqliteException
end

$apiwrapperattacheddata = [ ]

module ScraperWiki

    $metadatamessagedone = false
    $attachlist = [ ]

    def ScraperWiki.dumpMessage(hash)
        msg = JSON.generate(hash)
        $logfd.write( "JSONRECORD(" + msg.length.to_s() + "):" + msg + "\n")
        $logfd.flush()
    end

    # Allows _views_ to set some header values, those supported
    # are Content-type, Content-disposition and Location.
    #
    # === Parameters
    # * _headerkey_ = The header key to be set
    # * _headervalue_ = The value for the header
    #
    # === Example
    #
    # ScraperWiki::httpresponseheader('Content-type', 'application/json')
    #
    def ScraperWiki.httpresponseheader(headerkey, headervalue)
        ScraperWiki.dumpMessage({'message_type' => 'httpresponseheader', 'headerkey' => headerkey, 'headervalue' => headervalue})
    end

    # The scrape method fetches the content from a webserver.
    #
    # === Parameters
    #
    # * _url_ = The URL to fetch
    # * _params_ = The parameters to send with a POST request
    #
    # === Example
    # ScraperWiki::scrape('http://scraperwiki.com')
    #
    def ScraperWiki.scrape(url, params = nil)
      client = HTTPClient.new
      client.ssl_config.verify_mode = OpenSSL::SSL::VERIFY_NONE

      if params.nil? 
        return client.get_content(url)
      else
        return client.post_content(url, params)
      end
    end


    # Converts the provided UK postcode to latitude and longitude 
    # pair.
    #
    # === Parameters
    #
    # * _postcode_ = A valid UK postcode
    #
    # === Example
    #
    # ScraperWiki::gb_postcode_to_latlng('L3 6RP')
    #
    def ScraperWiki.gb_postcode_to_latlng(postcode)
        sres = ScraperWiki.scrape("https://views.scraperwiki.com/run/uk_postcode_lookup/?postcode="+URI.escape(postcode))
        jres = JSON.parse(sres)
        if jres["lat"] and jres["lng"]
            return [jres["lat"], jres["lng"]]
        end
        return nil
    end



    def ScraperWiki._unicode_truncate(string, size)
        # Stops 2 byte unicode characters from being chopped in half which kills JSON serializer
        string.scan(/./u)[0,size].join
    end

    # Saves the provided data into a local database for this scraper. Data is upserted
    # into this table (inserted if it does not exist, updated if the unique keys say it 
    # does).
    #
    # === Parameters
    #
    # * _unique_keys_ = A list of column names, that used together should be unique
    # * _data_ = A hash of the data where the Key is the column name, the Value the row
    #            value.  If sending lots of data this can be a list of hashes.
    # * _table_name_ = The name that the newly created table should use.
    #
    # === Example
    # ScraperWiki::save(['id'], {'id'=>1})
    #
    def ScraperWiki.save(unique_keys, data, date=nil, latlng=nil, table_name="swdata")
        if unique_keys != nil && !unique_keys.kind_of?(Array)
            raise 'unique_keys must be nil or an array'
        end
        if data == nil
            raise 'data must have a non-nil value'
        end

        ds = SW_DataStore.create()
        ldata = data.dup
        if date != nil
            ldata["date"] = date
        end
        if latlng != nil
            ldata["latlng_lat"] = latlng[0]
            ldata["latlng_lng"] = latlng[1]
        end
        return ScraperWiki.save_sqlite(unique_keys, ldata, table_name="swdata", verbose=2)
    end


    # Allows to the execution of user defined SQL against the database. When using this
    # method care should be taken to also call ScraperWiki::commit() at the appropriate
    # times to make sure that data is saved.
    #
    # === Parameters
    #
    # * _sqlquery_ = A valid SQL statement
    # * _data_ = Data replacement values for the sql statement
    # * _verbose_ = Verbosity level, 0 for no output.
    #
    # === Example
    # ScraperWiki::sqliteexecute('select * from swdata')
    #
    def ScraperWiki.sqliteexecute(sqlquery, data=nil, verbose=2)
        ds = SW_DataStore.create()
        res = ds.request({'maincommand'=>'sqliteexecute', 'sqlquery'=>sqlquery, 'data'=>data, 'attachlist'=>$attachlist})
        if (res.class == Hash) and res.include?("error")
            ScraperWiki.raisesqliteerror(res["error"])
        end

        if verbose
            if data.kind_of?(Array) 
                data.each do |value|
                    ldata = [ ]
                    if value == nil
                        value  = ''
                    end
                    ldata.push(ScraperWiki._unicode_truncate(value.to_s, 50))
                end
            else
                ldata = data
            end
            ScraperWiki.dumpMessage({'message_type'=>'sqlitecall', 'command'=>"execute", 'val1'=>sqlquery, 'val2'=>ldata})
        end
        return res
    end



            # this ought to be a local function
    def ScraperWiki._convdata(unique_keys, scraper_data)
        if unique_keys
            for key in unique_keys
                if !key.kind_of?(String) and !key.kind_of?(Symbol)
                    return { "error" => 'unique_keys must each be a string or a symbol', "bad_key" => key }
                end
                if !scraper_data.include?(key) and !scraper_data.include?(key.to_sym)
                    return { "error" => 'unique_keys must be a subset of data', "bad_key" => key }
                end
                if scraper_data[key] == nil and scraper_data[key.to_sym] == nil
                    return { "error" => 'unique_key value should not be nil', "bad_key" => key }
                end
            end
        end

        jdata = { }
        scraper_data.each_pair do |key, value|
            if not key
                return { "error" => 'key must not be blank', "bad_key" => key }
            end
            if key.kind_of?(Symbol)
                key = key.to_s
            end
            if key.class != String
                return { "error" => 'key must be string type', "bad_key" => key }
            end

            if !/[a-zA-Z0-9_\- ]+$/.match(key)
                return { "error"=>'key must be simple text', "bad_key"=> key }
            end

            if value.kind_of?(Date) 
                value = value.iso8601
            end
            if value.kind_of?(Time)
                value = value.iso8601
                raise "internal error, timezone came out as non-UTC while converting to SQLite format" unless value.match(/\+00:00$/)
                value.gsub!(/\+00:00$/, '')
            end
            if ![Fixnum, Float, String, TrueClass, FalseClass, NilClass].include?(value.class)
                value = value.to_s
            end
            jdata[key] = value
        end
        return jdata
    end


    # Saves the provided data into a local database for this scraper. Data is upserted
    # into this table (inserted if it does not exist, updated if the unique keys say it 
    # does).
    #
    # === Parameters
    #
    # * _unique_keys_ = A list of column names, that used together should be unique
    # * _data_ = A hash of the data where the Key is the column name, the Value the row
    #            value.  If sending lots of data this can be a list of hashes.
    # * _table_name_ = The name that the newly created table should use.
    # * _verbose_ = A verbosity level, 2 is the maximum (and default) and 0 means no debug  output
    #
    # === Example
    # ScraperWiki::save(['id'], {'id'=>1})
    #
    def ScraperWiki.save_sqlite(unique_keys, data, table_name="swdata", verbose=2)
        if !data
            ScraperWiki.dumpMessage({'message_type' => 'data', 'content' => "EMPTY SAVE IGNORED"})
            return
        end

        # convert :symbols to "strings"
        unique_keys = unique_keys.map { |x| x.kind_of?(Symbol) ? x.to_s : x }

        if data.class == Hash
            data = [ data ]
        elsif data.length == 0
            return
        end
            
        rjdata = [ ]
        for ldata in data
            ljdata = _convdata(unique_keys, ldata)
            if ljdata.include?("error")
                raise SqliteException.new(ljdata["error"])
            end
            rjdata.push(ljdata)
        end

        ds = SW_DataStore.create()
        res = ds.request({'maincommand'=>'save_sqlite', 'unique_keys'=>unique_keys, 'data'=>rjdata, 'swdatatblname'=>table_name})
       
        if res["error"]
            raise SqliteException.new(res["error"])
        end

        if verbose >= 2
            pdata = { }
            if rjdata.class == Hash
                sdata = rjdata
            elsif rjdata.length != 0 
                sdata = rjdata[0]
            else
                sdata = {}
            end
            sdata.each_pair do |key, value|
                key = ScraperWiki._unicode_truncate(key.to_s, 50)
                if value == nil
                    value  = ''
                else
                    value = ScraperWiki._unicode_truncate(value.to_s, 50)
                end
                pdata[key] = String(value)
            end
            if rjdata.class == Array and rjdata.size > 1
                pdata["number_records"] = "Number Records: "+String(rjdata.size)
            end
            ScraperWiki.dumpMessage({'message_type' => 'data', 'content' => pdata})
        end
        return res
    end

    # Allows the user to save a single variable (at a time) to carry state across runs of
    # the scraper.
    #
    # === Parameters
    #
    # * _name_ = The variable name
    # * _value_ = The value of the variable
    # * _verbose_ = Verbosity level
    #
    # === Example
    # ScraperWiki::save_var('current', 100)
    #
    def ScraperWiki.save_var(name, value, verbose=2)
        vtype = String(value.class)
        svalue = value.to_s
        if vtype != "Fixnum" and vtype != "String" and vtype != "Float" and vtype != "NilClass"
            puts "*** object of type "+vtype+" converted to string\n"
        end
        data = { "name" => name, "value_blob" => svalue, "type" => vtype }
        ScraperWiki.save_sqlite(unique_keys=["name"], data=data, table_name="swvariables", verbose=verbose)
    end

    # Allows the user to retrieve a previously saved variable
    #
    # === Parameters
    #
    # * _name_ = The variable name to fetch
    # * _default_ = The value to use if the variable name is not found
    # * _verbose_ = Verbosity level
    #
    # === Example
    # ScraperWiki::get_var('current', 0)
    #
    def ScraperWiki.get_var(name, default=nil, verbose=2)
        begin
            result = ScraperWiki.sqliteexecute("select value_blob, type from swvariables where name=?", [name], verbose)
        rescue NoSuchTableSqliteException => e   
            return default
        end
        
        if !result.has_key?("data") 
            return default          
        end 
        
        if result["data"].length == 0
            return default
        end
        # consider casting to type
        svalue = result["data"][0][0]
        vtype = result["data"][0][1]
        if vtype == "Fixnum"
            return svalue.to_i
        end
        if vtype == "Float"
            return svalue.to_f
        end
        if vtype == "NilClass"
            return nil
        end
        return svalue
    end




    # Shows all of the tables available in the database
    #
    # === Parameters
    #
    # * _dbname_ = The database name to connect to
    #
    # === Example
    # ScraperWiki::show_tables()
    #
    def ScraperWiki.show_tables(dbname=nil)
        name = "sqlite_master"
        if dbname != nil
            name = "`"+dbname+"`.sqlite_master" 
        end
        result = ScraperWiki.sqliteexecute("select tbl_name, sql from "+name+" where type='table'")
        #return result["data"]
        return (Hash[*result["data"].flatten])   # pre-1.8.7
    end


    # Retrieves information about the table specified by name
    #
    # === Parameters
    #
    # * _name_ = The name we want information on
    #
    # === Example
    # ScraperWiki::table_info('swdata')
    #
    def ScraperWiki.table_info(name)
        sname = name.split(".")
        if sname.length == 2
            result = ScraperWiki.sqliteexecute("PRAGMA %s.table_info(`%s`)" % sname)
        else
            result = ScraperWiki.sqliteexecute("PRAGMA table_info(`%s`)" % name)
        end
        res = [ ]
        for d in result["data"]
            res.push(Hash[*result["keys"].zip(d).flatten])   # pre-1.8.7
        end
        return res
    end

    def ScraperWiki.raisesqliteerror(rerror)
        if /sqlite3.Error: no such table:/.match(rerror)  # old dataproxy
            raise NoSuchTableSqliteException.new(rerror)
        end
        if /DB Error: \(OperationalError\) no such table:/.match(rerror)
            raise NoSuchTableSqliteException.new(rerror)
        end
        raise SqliteException.new(rerror)
    end

    # Attaches to a different database so that it can be queried along with
    # the current scraper's database.
    #
    # === Parameters
    #
    # * _name_ = The name of the database to attach to
    # * _asname_ = The name you wish this database to be known as in queries
    # * _verbose_ = A verbosity level
    #
    # === Example
    # ScraperWiki::attach('another_db', 'secondary')
    # Query can then call: select * from `secondary.swdata` ...
    #    
    def ScraperWiki.attach(name, asname=nil, verbose=1)
        $attachlist.push({"name"=>name, "asname"=>asname})

        ds = SW_DataStore.create()

        res = ds.request({'maincommand'=>'sqlitecommand', 'command'=>"attach", 'name'=>name, 'asname'=>asname})
        if res["error"]
            ScraperWiki.raisesqliteerror(res["error"])
        end
        
        if verbose
            ScraperWiki.dumpMessage({'message_type'=>'sqlitecall', 'command'=>"attach", 'val1'=>name, 'val2'=>asname})
        end
            
        return res
    end
    
    # Commits any previous sqlexecute calls to ensure the data is written into the database
    #
    # === Parameters
    #
    # * _verbose_ = A verbosity level
    #
    # === Returns
    # The output of the commit() command
    #
    # === Example
    # ScraperWiki::sqliteexecute('create index ...')    
    # ScraperWiki::commit()
    #    
    def ScraperWiki.commit(verbose=1)
        ds = SW_DataStore.create()
        res = ds.request({'maincommand'=>'sqlitecommand', 'command'=>"commit"})
    end

    # Allows for a simplified select statement
    #
    # === Parameters
    #
    # * _sqlquery_ = A valid select statement, without the select keyword
    # * _data_ = Any data provided for ? replacements in the query
    # * _verbose_ = A verbosity level
    #
    # === Returns
    # A list of hashes containing the returned data
    #
    # === Example
    # ScraperWiki::select('* from swdata')    
    #    
    def ScraperWiki.select(sqlquery, data=nil, verbose=1)
        if data != nil && sqlquery.scan(/\?/).length != 0 && data.class != Array
            data = [data]
        end
        result = ScraperWiki.sqliteexecute("select "+sqlquery, data, verbose)
        res = [ ]
        for d in result["data"]
            #res.push(Hash[result["keys"].zip(d)])           # post-1.8.7
            res.push(Hash[*result["keys"].zip(d).flatten])   # pre-1.8.7
        end
        return res
    end

################################################################################ Deprecated code


    # <b>DEPRECATED:</b> use ScraperWiki.attach
    def ScraperWiki.getData(name, limit=-1, offset=0)
        if !$apiwrapperattacheddata.include?(name)
            puts "*** instead of getData('"+name+"') please use\n    ScraperWiki.attach('"+name+"') \n    print ScraperWiki.select('* from `"+name+"`.swdata')"
            ScraperWiki.attach(name)
            $apiwrapperattacheddata.push(name)
        end

        apilimit = 500
        g = Enumerator.new do |g|
            count = 0
            while true
                if limit == -1
                    step = apilimit
                else
                    step = apilimit < (limit - count) ? apilimit : limit - count
                end
                query = "* from `#{name}`.swdata limit #{step} offset #{offset+count}"

                records = ScraperWiki.select(query)
                for r in records
                    g.yield r
                end

                count += records.length
                if records.length < step
                    break
                end
                if limit != -1 and count >= limit
                    break
                end
            end
        end
    end

    # <b>DEPRECATED:</b> use ScraperWiki.attach instead
    def ScraperWiki.getKeys(name)
        if !$apiwrapperattacheddata.include?(name)
            puts "*** instead of getKeys('"+name+"') please use\n    ScraperWiki.attach('"+name+"') \n    print ScraperWiki.sqliteexecute('select * from `"+name+"`.swdata limit 0')['keys']"
            ScraperWiki.attach(name)
            $apiwrapperattacheddata.push(name)
        end
        result = ScraperWiki.sqliteexecute("select * from `"+name+"`.swdata limit 0")
        if result.include?("error")
            raise SqliteException.new(result["error"])
        end
        return result["keys"]
    end
    
    
    # <b>DEPRECATED:</b>
    def ScraperWiki.get_metadata(metadata_name, default = nil)
        if !$metadatamessagedone == nil
            puts "*** instead of get_metadata('"+metadata_name+"') please use\n    get_var('"+metadata_name+"')"
            metadatamessagedone = true
        end
        result = ScraperWiki.get_var(metadata_name, default)
        return result
    end

    # <b>DEPRECATED:</b>
    def ScraperWiki.save_metadata(metadata_name, value)
        if !$metadatamessagedone
            puts "*** instead of save_metadata('"+metadata_name+"') please use\n    save_var('"+metadata_name+"')"
            $metadatamessagedone = true
        end
        return ScraperWiki.save_var(metadata_name, value)
    end    

    # <b>DEPRECATED:</b>    
    def ScraperWiki.getDataByDate(name, start_date, end_date, limit=-1, offset=0)
        raise SqliteException.new("getDataByDate has been deprecated")
    end
    
    # <b>DEPRECATED:</b>    
    def ScraperWiki.getDataByLocation(name, lat, lng, limit=-1, offset=0)
        raise SqliteException.new("getDataByLocation has been deprecated")
    end
        
    # <b>DEPRECATED:</b>        
    def ScraperWiki.search(name, filterdict, limit=-1, offset=0)
        raise SqliteException.new("SW_APIWrapper.search has been deprecated")
    end

end
