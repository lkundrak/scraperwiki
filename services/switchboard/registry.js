/******************************************************************************
* registry.js
*
* The main registry of run_id -> readers + writers
******************************************************************************/

var max_read  = 10;
var max_write = 10;

var connections = [  ];

exports.ConnectionTypeEnum = ConnectionTypeEnum = {
    READER : 0,
    WRITER : 1
};


/******************************************************************************
* 
******************************************************************************/
exports.set_max = function( read, write ) {
	max_read = read;
	max_write = write;
}

/******************************************************************************
* 
******************************************************************************/
exports.bind = function( key, socket, type ) {
	var obj = connections[key] || null;
	if ( obj == null ) {
		obj = create_binding(key);
	} 
	
	// set the relevant connection if we have space
	if ( type == ConnectionTypeEnum.READER ) {
		
		if ( obj.Readers.length >= max_read ) 
			return false;
		obj.Readers.push( socket );
		
	} else if ( type == ConnectionTypeEnum.WRITER ) {
		
		if ( obj.Writers.length >= max_write ) 
			return false;
		obj.Writers.push( socket );
		
	}
	connections[key] = obj;
		
	return true;
}


/******************************************************************************
* 
******************************************************************************/
exports.unbind = function( socket, type ) {
	var obj = connections[key] || null;
	if ( obj == null )
		return;

	if ( type == ConnectionTypeEnum.READER ) {
		delete obj.Readers[socket];
	} else if ( type == ConnectionTypeEnum.WRITER ) {
		delete obj.Writers[socket];		
	}
	
	if ( obj.Writers.length == obj.Readers.length == 0 ) {
		delete connections[key];
	}
}


function create_binding( k ) {
	return {
		Key: k,
		Readers: [],
		Writers: []
	}
}