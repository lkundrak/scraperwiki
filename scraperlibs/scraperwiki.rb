require 'json'
require	'uri'
require	'net/http'
require 'scraperwiki/datastore'
require 'generator'
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
        $logfd.write(JSON.generate(hash) + "\n")
        $logfd.flush()
    end

    def ScraperWiki.httpresponseheader(headerkey, headervalue)
        ScraperWiki.dumpMessage({'message_type' => 'httpresponseheader', 'headerkey' => headerkey, 'headervalue' => headervalue})
    end

    def ScraperWiki.scrape(url, params = nil)
      client = HTTPClient.new
      client.ssl_config.verify_mode = OpenSSL::SSL::VERIFY_NONE

      if params.nil? 
        return client.get_content(url)
      else
        return client.post_content(url, params)
      end
    end

    def ScraperWiki.gb_postcode_to_latlng(postcode)
        uri = URI.parse("http://views.scraperwiki.com/run/uk_postcode_lookup/?postcode="+URI.escape(postcode))
        sres = Net::HTTP.get(uri)
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


    def ScraperWiki.sqliteexecute(sqlquery, data=nil, verbose=2)
        ds = SW_DataStore.create()
        res = ds.request({'maincommand'=>'sqliteexecute', 'sqlquery'=>sqlquery, 'data'=>data, 'attachlist'=>$attachlist})
        if res["error"]
            if /sqlite3.Error: no such table:/.match(res["error"])
                raise NoSuchTableSqliteException.new(res["error"])
            end
            raise SqliteException.new(res["error"])
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
    def ScraperWiki.convdata(unique_keys, scraper_data)
        if unique_keys
            for key in unique_keys
                if !scraper_data.include?(key)
                    return { "error" => 'unique_keys must be a subset of data', "bad_key" => key }
                end
                if scraper_data[key] == nil
                    return { "error" => 'unique_key value should not be None', "bad_key" => key }
                end
            end
        end

        jdata = { }
        scraper_data.each_pair do |key, value|
            if not key
                return { "error" => 'key must not be blank', "bad_key" => key }
            end
            if key.class != String
                return { "error" => 'key must be string type', "bad_key" => key }
            end

            if !/[a-zA-Z0-9_\- ]+$/.match(key)
                return { "error"=>'key must be simple text', "bad_key"=> key }
            end
            
            if ![Fixnum, Float, String, TrueClass, FalseClass, NilClass].include?(value.class)
                value = value.to_s
            end
            jdata[key] = value
        end
        return jdata
    end


    def ScraperWiki.save_sqlite(unique_keys, data, table_name="swdata", verbose=2)
        if !data
            ScraperWiki.dumpMessage({'message_type' => 'data', 'content' => "EMPTY SAVE IGNORED"})
            return
        end

        if data.class == Hash
            rjdata = convdata(unique_keys, data)
            if rjdata.include?("error")
                raise SqliteException.new(rjdata["error"])
            end
        else
            rjdata = [ ]
            for ldata in data
                ljdata = convdata(unique_keys, ldata)
                if ljdata.include?("error")
                    raise SqliteException.new(ljdata["error"])
                end
                rjdata.push(ljdata)
            end
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
            else
                sdata = rjdata[0]
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

            # also needs to handle the types better (could save json and datetime objects handily
    def ScraperWiki.save_var(name, value, verbose=2)
        data = { "name" => name, "value_blob" => value, "type" => value.class }
        ScraperWiki.save_sqlite(unique_keys=["name"], data=data, table_name="swvariables", verbose=verbose)
    end

    def ScraperWiki.get_var(name, default=nil, verbose=2)
        begin
            result = ScraperWiki.sqliteexecute("select value_blob, type from swvariables where name=?", [name], verbose)
        rescue NoSuchTableSqliteException => e   
            return default
        end
        if result["data"].length == 0
            return default
        end
        return result["data"][0][0]
    end

    # These are DEPRECATED and just here for compatibility
    def ScraperWiki.get_metadata(metadata_name, default = nil)
        if !$metadatamessagedone == nil
            puts "*** instead of get_metadata('"+metadata_name+"') please use\n    get_var('"+metadata_name+"')"
            metadatamessagedone = true
        end
        result = ScraperWiki.get_var(metadata_name, default)
        return result
    end

    # These are DEPRECATED and just here for compatibility
    def ScraperWiki.save_metadata(metadata_name, value)
        if !$metadatamessagedone
            puts "*** instead of save_metadata('"+metadata_name+"') please use\n    save_var('"+metadata_name+"')"
            $metadatamessagedone = true
        end
        return ScraperWiki.save_var(metadata_name, value)
    end


    def ScraperWiki.show_tables(dbname=nil)
        name = "sqlite_master"
        if dbname != nil
            name = "`"+dbname+"`.sqlite_master" 
        end
        result = ScraperWiki.sqliteexecute("select tbl_name, sql from "+name+" where type='table'")
        #return result["data"]
        return (Hash[*result["data"].flatten])   # pre-1.8.7
    end


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


    def ScraperWiki.getDataByDate(name, start_date, end_date, limit=-1, offset=0)
        raise SqliteException.new("getDataByDate has been deprecated")
    end
    
    def ScraperWiki.getDataByLocation(name, lat, lng, limit=-1, offset=0)
        raise SqliteException.new("getDataByLocation has been deprecated")
    end
        
    def ScraperWiki.search(name, filterdict, limit=-1, offset=0)
        raise SqliteException.new("SW_APIWrapper.search has been deprecated")
    end


    def ScraperWiki.attach(name, asname=nil, verbose=1)
        $attachlist.push({"name"=>name, "asname"=>asname})

        ds = SW_DataStore.create()
        res = ds.request({'maincommand'=>'sqlitecommand', 'command'=>"attach", 'name'=>name, 'asname'=>asname})
        if res["error"]
            if /sqlite3.Error: no such table:/.match(res["error"])
                raise NoSuchTableSqliteException.new(res["error"])
            end
            raise SqliteException.new(res["error"])
        end
        if verbose
            ScraperWiki.dumpMessage({'message_type'=>'sqlitecall', 'command'=>"attach", 'val1'=>name, 'val2'=>asname})
        end
        return res
    end
    

    def ScraperWiki.commit(verbose=1)
        ds = SW_DataStore.create()
        res = ds.request({'maincommand'=>'sqlitecommand', 'command'=>"commit"})
    end

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

    # old functions put back in for regression
    def ScraperWiki.getData(name, limit=-1, offset=0)
        if !$apiwrapperattacheddata.include?(name)
            puts "*** instead of getData('"+name+"') please use\n    ScraperWiki.attach('"+name+"') \n    print ScraperWiki.select('* from `"+name+"`.swdata')"
            ScraperWiki.attach(name)
            $apiwrapperattacheddata.push(name)
        end

        apilimit = 500
        g = Generator.new do |g|
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
end
