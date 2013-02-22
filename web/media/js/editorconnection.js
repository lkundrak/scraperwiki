// Module to manage the connection to twister via Orbited
// (Replace this if we use SocketIO)

var buffer = "";
var conn = undefined; // Orbited connection
var bConnected  = false; 
var bSuppressDisconnectionMessages = false; 

function setupOrbited() 
{
    TCPSocket = Orbited.TCPSocket;
    conn = new TCPSocket(); 
    conn.open('localhost', '9010'); 
    buffer = " "; 
    sChatTabMessage = 'Connecting...'; 
    $('.editor_output div.tabs li.chat a').html(sChatTabMessage);
    
    conn.onclose = function(code)
    {
        var mcode; 
        if (code == Orbited.Statuses.ServerClosedConnection)
            mcode = 'ServerClosedConnection'; 
        else if (code == Orbited.Errors.ConnectionTimeout)
            mcode = 'ConnectionTimeout'; 
        else if (code == Orbited.Errors.InvalidHandshake)
            mcode = 'InvalidHandshake'; 
        else if (code == Orbited.Errors.UserConnectionReset)
            mcode = 'UserConnectionReset'; 
        else if (code == Orbited.Errors.Unauthorized)
            mcode = 'Unauthorized'; 
        else if (code == Orbited.Errors.RemoteConnectionFailed)
            mcode = 'RemoteConnectionFailed'; 
        else if (code == Orbited.Statuses.SocketControlKilled)
            mcode = 'SocketControlKilled'; 
        else
            mcode = 'code=' + code;

        writeToChat('Connection closed: ' + mcode); 
        bConnected = false; 

        // couldn't find a way to make a reconnect button work!
            // the bSuppressDisconnectionMessages technique doesn't seem to work (unload is not invoked), so delay message in the hope that window will close first
        window.setTimeout(function() 
        {
            if (!bSuppressDisconnectionMessages)
            {
                writeToChat('<b>You will need to reload the page to reconnect</b>');  
                writeToConsole("Connection to execution server lost, you will need to reload this page.", "exceptionnoesc"); 
                writeToConsole("(You can still save your work)", "exceptionnoesc"); 
            }
        }, 250); 


        $('.editor_controls #run').val('Unconnected');
        $('.editor_controls #run').unbind('click.run');
        $('.editor_controls #run').unbind('click.abort');
        $('#running_annimation').hide(); 

        sChatTabMessage = 'Disconnected'; 
        $('.editor_output div.tabs li.chat a').html(sChatTabMessage + '<b class="unread"></b>');
    }
    
    
    conn.onread = function(ldata) 
    {
        buffer = buffer+ldata;
        while (true) 
        {
            var linefeed = buffer.indexOf("\n"); 
            if (linefeed == -1)
                break; 
            sdata = buffer.substring(0, linefeed); 
            buffer = buffer.substring(linefeed+1); 
            sdata = sdata.replace(/[\s,]+$/g, '');  // trailing commas cannot be evaluated in IE
            if (sdata.length == 0)
                continue; 

            var jdata; 

            try 
            {
				// Check if the sdata appears to be an integer
				var i = parseInt( sdata, 10 );
				if ( ! isNaN(i)) continue; // it is an integer, we don't want it.		
			} catch (errorParse) {
				// nothing to do
			}
			
            try 
            {
                //writeToChat("--- "+cgiescape(sdata)); // for debug of what's coming out
                jdata = $.evalJSON(sdata);
            } 
            catch(err) 
            {
				if (window.console != undefined) {
        			console.log( "Malformed json: '''" + sdata + "'''" );
    			}
                //alert("Malformed json: '''" + sdata + "'''"); 
                continue
            }
            ReceiveRecordJ(jdata); 
        }
    }
}

//send a message to the server (needs linefeed delimeter because sometimes records get concattenated)
function sendjson(json_data) 
{
    var jdata = $.toJSON(json_data); 
    try 
    {
        if (jdata.length < 10000)  // only concatenate for smallish strings
            conn.send(jdata + "\r\n");  
        else
        {
            conn.send(jdata);  
            conn.send("\r\n");  // this goes out in a second chunk
        }
    } 
    catch(err) 
    {
        if (!bSuppressDisconnectionMessages)
        {
            writeToConsole("Send error: " + err, "exceptionnoesc"); 
            writeToChat(jdata); 
        }
    }
}
