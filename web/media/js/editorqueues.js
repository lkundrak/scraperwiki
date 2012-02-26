// Module to manage the incoming queues of records to twister
// most outgoing information goes directly to sendjson() in editorconnection, 
// except for the editorpatchqueues.js


var receiverecordcall = null;     // timeout object
var receiverecordqueue = [ ]; 
var receivechatqueue = [ ]; 
var receivechainpatchqueue = [ ]; // coming in
var receivechainpatchcall = null; // timeout object
var receiveRecordMain = null;     // function in main editor.js


//read data back from twisted
function ReceiveRecordJ(jdata)
{
    if ((jdata.message_type == 'chat') || (jdata.message_type == 'editorstatus'))
        receivechatqueue.push(jdata); 
    else if (jdata.message_type == 'othertyping')
    {
        $('#lasttypedtimestamp').text(String(new Date())); 
        if (jdata.insertlinenumber != undefined)
            receivechainpatchqueue.push(jdata); 
    }
    else
        receiverecordqueue.push(jdata); 

    // allow the user to clear the choked data if they want
    if ((jdata.message_type == 'executionstatus')  && (jdata.content == 'runfinished')) 
    {
        $('.editor_controls #run').val('Finishing');
        $('.editor_controls #run').unbind('click.abort');
        $('.editor_controls #run').bind('click.stopping', clearJunkFromQueue);
    }

    if ((receiverecordcall == null) && (receiverecordqueue.length + receivechatqueue.length >= 1))
        receiverecordcall = window.setTimeout(function() { receiveRecordFromQueue(); }, 1);  

    if (receivechainpatchqueue.length != 0)
    {
        if (receivechainpatchcall != null)
            window.clearTimeout(receivechainpatchcall); 
        receivechainpatchcall = window.setTimeout(function() { receiveChainpatchFromQueue(null); }, 10);  
    }
    
    // clear batched up data that's choking the system
    if ((jdata.message_type == 'executionstatus')  && (jdata.content == 'killrun'))
        window.setTimeout(clearJunkFromQueue, 1); 
}

function clearJunkFromQueue() 
{
    var lreceiverecordqueue = [ ]; 
    for (var i = 0; i < receiverecordqueue.length; i++) 
    {
        jdata = receiverecordqueue[i]; 
        if ((jdata.message_type != "data") && (jdata.message_type != "console") && (jdata.message_type != "sqlitecall"))
            lreceiverecordqueue.push(jdata); 
    }

    if (receiverecordqueue.length != lreceiverecordqueue.length) 
    {
        message = "Clearing " + (receiverecordqueue.length - lreceiverecordqueue.length) + " records from receiverqueue, leaving: " + lreceiverecordqueue.length; 
        writeToConsole(message); 
        receiverecordqueue = lreceiverecordqueue; 
    }
}

// run our own queue not in the timeout system (letting chat messages get to the front)
function receiveRecordFromQueue() 
{
    receiverecordcall = null; 
    var jdata; 
    if (receivechatqueue.length != 0)
        jdata = receivechatqueue.shift(); 
    else if (receiverecordqueue.length != 0) 
        jdata = receiverecordqueue.shift(); 
    else
        return; 
    
    receiveRecordMain(jdata);
    if (receiverecordqueue.length + receivechatqueue.length >= 1)
        receiverecordcall = window.setTimeout(function() { receiveRecordFromQueue(); }, 1); 
}


// chain patches outg
