var EventEmitter = process.EventEmitter;
var net = require('net');
var qs = require('querystring');

exports.DataProxyClient =  DataProxyClient = function() {
	this.host = "";
	this.port  = 0;
	this.scrapername = "";	
	this.connection = null;
}

DataProxyClient.prototype.__proto__ = EventEmitter.prototype;

DataProxyClient.prototype.init = function(host, port,scrapername,runid,verification_key) {
	this.host = host;
	this.port = port;
	this.scrapername = scrapername;
	this.runid = runid;
	this.attachables = [];
	this.connected = false;
	this.verification_key = verification_key;
}

DataProxyClient.prototype.ensureConnected = function( callback ) {
	if ( this.connected ) { 
		callback(this.connected);
		return;
	}
	
	this.connection = net.createConnection(this.port, this.host);
	this.connection.setEncoding( 'utf8');
	
	var me = this;
	this.connection.once('data', function (data) {
		var str = JSON.parse( data );
		me.connected = str.status && str.status == 'good';
		callback(me.connected);
		return;
	});
	
	this.connection.once('connect', function(){
        var data = {"uml": me.connection.address().address , "port": me.connection.address().port}
        data["vscrapername"] = me.scrapername;
        data["vrunid"] = me.runid
        data["attachables"] = me.attachables.join(" ")
		data["verify"] = me.verification_key

		// naughty semi-http request.... sigh
		var msg = "GET /?" + qs.stringify(data) + " HTTP/1.1\r\n\r\n";
		me.connection.write( msg);
	});	
}

DataProxyClient.prototype.close = function() {
	if ( this.connected ) {
		this.connection.end();
		this.connected = false;
	}
}
	
DataProxyClient.prototype.save = function(indices, data, callback) {
	var self = this;
	this.ensureConnected(function(ok){
		if ( ok ) {
			internal_save(indices,data, function(result){
				callback( result );	
			});
		}
	});
}


DataProxyClient.prototype.request = function(req) {
    this.ensure_connected();

	this.connection.write( JSON.stringify(req) + "\n", function(){ });	

//    line = receiveoneline(m_socket)
//    if not line:
//        return {"error":"blank returned from dataproxy"}
//    return json.loads(line)
}

function internal_save(indices,data, callback) {

	console.log( 'internal save ');
	callback( 'status' );
	
	
	/*	
    if unique_keys != None and type(unique_keys) not in [ list, tuple ]:
        raise databaseexception({ "error":'unique_keys must a list or tuple', "unique_keys_type":str(type(unique_keys)) })

    def convdata(unique_keys, scraper_data):
        if unique_keys:
            for key in unique_keys:
                if key not in scraper_data:
                    return { "error":'unique_keys must be a subset of data', "bad_key":key }
                if scraper_data[key] == None:
                    return { "error":'unique_key value should not be None', "bad_key":key }
        jdata = { }
        for key, value in scraper_data.items():
            if not key:
                return { "error": 'key must not be blank', "bad_key":key }
            if type(key) not in [unicode, str]:
                return { "error":'key must be string type', "bad_key":key }
            if not re.match("[a-zA-Z0-9_\- ]+$", key):
                return { "error":'key must be simple text', "bad_key":key }
            
            if type(value) in [datetime.datetime, datetime.date]:
                value = value.isoformat()
            elif value == None:
                pass
            elif isinstance(value, SqliteError):
                return {"error": str(value)}
            elif type(value) == str:
                try:
                    value = value.decode("utf-8")
                except:
                    return {"error": "Binary strings must be utf-8 encoded"}
            elif type(value) not in [int, bool, float, unicode, str]:
                value = unicode(value)
            jdata[key] = value
        return jdata
            

    if type(data) == dict:
        rjdata = convdata(unique_keys, data)
        if rjdata.get("error"):
            raise databaseexception(rjdata)
        if date:
            rjdata["date"] = date
    else:
        rjdata = [ ]
        for ldata in data:
            ljdata = convdata(unique_keys, ldata)
            if ljdata.get("error"):
                raise databaseexception(ljdata)
            rjdata.append(ljdata)
    result = scraperwiki.datastore.request({"maincommand":'save_sqlite', "unique_keys":unique_keys, "data":rjdata, "swdatatblname":table_name})

    if "error" in result:
        raise databaseexception(result)

    if verbose >= 2:
        pdata = {}
        if type(data) == dict:
            for key, value in data.items():
                pdata[strencode_trunc(key, 50)] = strencode_trunc(value, 50)
        elif data:
            for key, value in data[0].items():
                pdata[strencode_trunc(key, 50)] = strencode_trunc(value, 50)
            pdata["number_records"] = "Number Records: %d" % len(data)
        scraperwiki.dumpMessage({'message_type':'data', 'content': pdata})
    return result
*/		
};


DataProxyClient.prototype.toString = function() {
	return "DataProxy (" + this.host + ":" + this.port + " - " +  this.scrapername +")";
}
