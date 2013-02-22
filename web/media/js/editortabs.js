// Module for handling the console, sources, data, chat tabs at the bottom of the editor

// Important functions:
//  writeToChat(seMessage, sechatname)
//  writeExceptionDump
//  writeToSources
//  writeToSqliteData
//  clearOutput

var scrollPositions = { 'console':0, 'data':0, 'sources':0, 'chat':0 }; 
var outputMaxItems = 400;
// *sTabCurrent* is generally to the class name of the currently shown tab.
var sTabCurrent = ''; 
var sChatTabMessage = 'Chat';

// information handling who else is watching and editing during this session
var editingusername = "";  // primary editor
var loggedinusers = [ ];   // all people watching
var loggedineditors = [ ]; // list of who else is here and their windows open who have editing rights
var iselectednexteditor = 1; 
var nanonymouseditors = 0; // number of anonymous editors
var countclientsconnected = 0; 
var chatname = "";         // special in case of Anonymous users (yes, this unnecessarily gets set every time we call recordEditorStatus)
var clientnumber = -1;     // allocated by twister for this window, so we can find it via django
var chatpeopletimes = { }; // last time each person made a chat message

// these actually get set by the server
var servernowtime = new Date(); 
var earliesteditor = servernowtime; 
var lasttouchedtime = undefined; 

var cachehidlookup = { }; // this itself is a cache of a cache

function cgiescape(text) {
    if (typeof text == 'number')
        return String(text); 
    if (typeof text != 'string')
        return "&lt;NONSTRING "+(typeof text)+"&gt;"; // should convert on server
    return (text ? text.replace(/&/g, '&amp;').replace(/</g, '&lt;') : "");
}

// some are implemented with tables, and some with span rows.  
function setTabScrollPosition(sTab, command) {
    divtab = '#output_' + sTab; 
    contenttab = '#output_' + sTab; 

    if ((sTab == 'console') || (sTab == 'sources')){
        divtab = '#output_' + sTab + ' div';
        contenttab = '#output_' + sTab + ' .output_content';
    }

    if (command == 'hide'){
        scrollPositions[sTab] = $(divtab).scrollTop();
    } else {
        if (command == 'bottom' || command == 'show'){
            scrollPositions[sTab] = $(contenttab).height()+$(divtab)[0].scrollHeight;
		}
        $(divtab).scrollTop(scrollPositions[sTab]);
    }
}

function showTextPopup(sLongMessage){
    $.modal('<pre class="popupoutput">'+cgiescape(sLongMessage)+'</pre>', 
            {overlayClose: true, 
                containerCss:{ borderColor:"#fff", height:"80%", padding:0, width:"90%", background:"#000", color:"#3cef3b" }, 
                overlayCss: { cursor:"auto" }
            });
}


function lparsehighlightcode(sdata, lmimetype){
	// sdata is already a JSON object
    var cachejson = sdata; 

/*    try 
    {
        cachejson = $.evalJSON(sdata);
    } 
    catch (err) 
    {
		alert( typeof(sdata) );
		alert( typeof(sdata['content']) );
        return { "objcontent": $('<pre class="popupoutput">Malformed json: ' + cgiescape(sdata) + "</pre>") }; 
    }
*/
    lmimetype = cachejson["mimetype"];  // the incoming value is incorrect because of failure to use closure and httpproxy.py isn't sending the value out properly (see line 489)
    if ((lmimetype != "text/html") || (cachejson["content"].length > 20000))
    {
        var res = [ ]; 
        res.push("<h2>mimetype: "+lmimetype+"</h2>"); 
        if (cachejson["encoding"] == "base64")
            res.push("<h2>Encoded as: "+cachejson["encoding"]+"</h2>"); 
        res.push('<pre>', cgiescape(cachejson["content"]), '</pre>'); 
        cachejson["objcontent"] = $(res.join("")); 
        return cachejson; 
    }
    // could highlight text/javascript and text/css

    var lineNo = 1; 
    var cpnumbers= ($('input#popuplinenumbers').attr('checked') ? $('<div id="cp_linenumbers"></div>') : undefined); 
    var cpoutput = $('<div id="cp_output"></div>'); 
    function addLine(line) 
    {
        if (cpnumbers)
            cpnumbers.append(String(lineNo++)+'<br>'); 
        var kline = $('<span>').css('background-color', '#fae7e7'); 
        for (var i = 0; i < line.length; i++) 
            cpoutput.append(line[i]);
        cpoutput.append('<br>'); 
    }
    highlightText(cachejson["content"], addLine, HTMLMixedParser); 
    cachejson["objcontent"] = $('<div id="cp_whole"></div>'); 
    if (cpnumbers)
        cachejson["objcontent"].append(cpnumbers); 
    cachejson["objcontent"].append(cpoutput); 
    return cachejson; 
}


function popupCached(cacheid, lmimetype){
    modaloptions = { overlayClose: true, 
                        overlayCss: { cursor:"auto" }, 
                        containerCss:{ borderColor:"#00f", "borderLeft":"2px solid black", height:"80%", padding:0, width:"90%", "text-align":"left", cursor:"auto" }, 
                        containerId: 'simplemodal-container' 
                    }; 

    var cachejson = cachehidlookup[cacheid]; 
    if (cachejson == undefined)
    {
        modaloptions['onShow'] = function() 
        { 
            $.ajax({type : 'POST', url  : $('input#proxycachedurl').val(), data: { cacheid: cacheid }, timeout: 10000, success: function(sdata) 
            {
                cachejson = lparsehighlightcode(sdata, lmimetype); 
                if (cachejson["objcontent"].length < 15000)  // don't cache huge things
                    cachehidlookup[cacheid] = cachejson; 

                var wrapheight = $('.simplemodal-wrap').height(); 
                $('.simplemodal-wrap #loadingheader').remove(); 
                $('.simplemodal-wrap').append(cachejson["objcontent"]); 
                $('.simplemodal-wrap').css("height", wrapheight + "px").css("overflow", "auto"); 
            }})
        }
        $.modal('<h1 id="loadingheader">Loading ['+cacheid+'] ...</h1>', modaloptions); 
    }
    else
        $.modal(cachejson["objcontent"], modaloptions); 
}


function clearOutput() {
    $('#output_console div').html('');
    $('#output_sources div').html('');
    $('#output_data table').html('');
    $('.editor_output div.tabs li.console').removeClass('new');
    $('.editor_output div.tabs li.data').removeClass('new');
    $('.editor_output div.tabs li.sources').removeClass('new');
	resetTabNumber('console');
	resetTabNumber('data');
	resetTabNumber('sources');
}

function getScrollPosition(sTab){
	//	Returns a tab's scrollTop value or 0, whichever's greater.
	//	Useful for finding out whether to scroll to the bottom of
	//	a tab when adding new content.
	oTab = $('#output_' + sTab);
	iTabHeight = $('.output_content', oTab).height();
	iTabScroll = $('.output_content', oTab).scrollTop();
	iContentHeight = 0;
	if($('.output_content', oTab).is('div')){
		$('.output_item', oTab).each(function(){ 
			iContentHeight = iContentHeight + $(this).outerHeight();
		});
	} else {
		$('.output_content tr', oTab).each(function(){ 
			iContentHeight = iContentHeight + $(this).outerHeight();
		});
	}
	if(iContentHeight > iTabHeight){
		if(iContentHeight == iTabHeight + iTabScroll) {
			return 0;
		} else {
			return (iContentHeight - iTabHeight - iTabScroll);
		}
	} else {
		return 0;
	}
}


//Write to console/data/sources
function writeToConsole(sMessage, sMessageType, iLine) 
{
    // if an exception set the class accordingly
    var sShortClassName = '';
    var sLongClassName = 'message_expander';
    var sExpand = '...more'

    var sLongMessage = undefined; 
    if (sMessageType == 'httpresponseheader') 
        sShortClassName = 'exception';

    if (sMessageType == 'exceptiondump') 
        sShortClassName = 'exception';

    var escsMessage = cgiescape(sMessage); 
    if (sMessageType == 'exceptionnoesc') {
        sShortClassName = 'exception';
        escsMessage = sMessage; // no escaping
    }
    else if (sMessage.length > 110) {
        sLongMessage = sMessage; 
        escsMessage = cgiescape(sMessage.replace(/^\s+|\s+$/g, "").substring(0, 100)); 
    }

	var iScrollStart = getScrollPosition('console');
	if(iScrollStart <= 0){
		setTabScrollPosition('console', 'bottom');
	}

    // create new item
    var oConsoleItem = $('<span></span>');
    oConsoleItem.addClass('output_item');
    oConsoleItem.addClass(sShortClassName);
    
    oConsoleItem.html(escsMessage); 

    if(sLongMessage != undefined) 
    {
        oMoreLink = $('<a href="#"></a>');
        oMoreLink.addClass('expand_link');
        oMoreLink.text(sExpand)
        oMoreLink.longMessage = sLongMessage;
        oConsoleItem.append(oMoreLink);
        oMoreLink.click(function() { showTextPopup(sLongMessage); });
    }

    // add clickable line number link
    if (iLine != undefined) 
    {
        oLineLink = $('<a href="#">Line ' + iLine + ' - </a>'); 
        oConsoleItem.prepend(oLineLink);
        oLineLink.click(function() { SelectEditorLine(iLine); }); 
    }
    
    //remove items if over max
    while ($('#output_console div.output_content').children().size() >= outputMaxItems) 
        $('#output_console div.output_content').children(':first').remove();

    //append to console
    $('#output_console div.output_content').append(oConsoleItem);
    $('.editor_output div.tabs li.console').addClass('new');
	incrementTabNumber('console');
	
	if(iScrollStart <= 0 && getScrollPosition('console') > 0){
		setTabScrollPosition('console', 'bottom');
	}

};



function writeToSources(sUrl, lmimetype, bytes, failedmessage, cached, cacheid, ddiffer, fetchtime) 
{
    //remove items if over max
    while ($('#output_sources div.output_content').children().size() >= outputMaxItems) 
        $('#output_sources div.output_content').children(':first').remove();

    // normalize the mimetypes
    if (lmimetype == undefined)
        lmimetype = "text/html";
    else if (lmimetype == "application/json")
        lmimetype = "text/json";

	var iScrollStart = getScrollPosition('sources');
	if(iScrollStart <= 0){
		setTabScrollPosition('sources', 'bottom');
	}

    //append to sources tab
    var smessage = [ ]; 
    var alink = '<a href="' + sUrl + '" target="_new">' + sUrl.substring(0, 100) + '</a>'; 
    if ((failedmessage == undefined) || (failedmessage == ''))
    {
        smessage.push('<span class="bytesloaded">', bytes, 'bytes loaded</span>, '); 
        if (lmimetype.substring(0, 5) != "text/") 
            smessage.push("<b>"+lmimetype+"</b>"); 

        // this is the orange up-arrow link that doesn't work because something wrong in the server, so hide it for now
        /*if (cacheid != undefined) {
            smessage.push('<a id="cacheid-'+cacheid+'" title="Popup html" class="cachepopup">&nbsp;&nbsp;</a>'); 
			smessage.push( cacheid );
		}*/
		
        if (cached == 'True')
            smessage.push('(from cache)'); 
    }
    else
        smessage.push(failedmessage); 
    if (ddiffer == "True")
        smessage.push('<span style="background:red"><b>BAD CACHE</b></span>, '); 
    if (fetchtime != undefined)
        smessage.push('<span class="">response time: ', Math.round(fetchtime*1000), 'ms</span>, '); 

    smessage.push(alink); 

    $('#output_sources div.output_content').append('<span class="output_item">' + smessage.join(" ") + '</span>')
    $('.editor_output div.tabs li.sources').addClass('new');
	incrementTabNumber('sources');
    
   	if(iScrollStart <= 0 && getScrollPosition('sources') > 0){
		setTabScrollPosition('sources', 'bottom');
	}
	
    if (cacheid != undefined)  
        $('a#cacheid-'+cacheid).click(function() { popupCached(cacheid, lmimetype); return false; }); 

}


function writeToData(aRowData) 
{
    while ($('#output_data table.output_content tbody').children().size() >= outputMaxItems) 
        $('#output_data table.output_content tbody').children(':first').remove();

	var iScrollStart = getScrollPosition('data');
	if(iScrollStart <= 0){
		setTabScrollPosition('data', 'bottom');
	}

    var oRow = $('<tr></tr>');
    
    for(var k in aRowData){
        oRow.append( $('<td>'+cgiescape(aRowData[k])+'</td>') )
    }

    $('#output_data table.output_content').append(oRow);  // oddly, append doesn't work if we add tbody into this selection
    $('.editor_output div.tabs li.data').addClass('new');
	incrementTabNumber('data'); 

	if(iScrollStart <= 0 && getScrollPosition('data') > 0){
		setTabScrollPosition('data', 'bottom');
	}
}

function writeToSqliteData(command, val1, lval2) 
{
    while ($('#output_data table.output_content tbody').children().size() >= outputMaxItems){
        $('#output_data table.output_content tbody').children(':first').remove();
	}	

	var iScrollStart = getScrollPosition('data');
	if(iScrollStart <= 0){
		setTabScrollPosition('data', 'bottom');
	}
	
    var trlast = $('#output_data table.output_content tr:last'); 
    if (!trlast.hasClass('progresstick'))
        trlast = undefined; 
	if (command == 'progresstick'){
        var pval = '<td><i>progress-tick: '+val1+'</i></td><td><i>elapsed seconds: '+lval2.toFixed(2)+'</i></td>'; 
        if (trlast)
            $(trlast).html(pval); 
        else
            $('#output_data table.output_content').append('<tr class="progresstick">'+pval+'</tr>'); 
    } else if (command == 'stillproducing'){
        var pval = '<td><i>producing-tick: '+val1+'</i></td><td><i>records: '+lval2+'</i></td>'; 
        if (trlast)
            $(trlast).html(pval); 
        else
            $('#output_data table.output_content').append('<tr class="progresstick">'+pval+'</tr>'); 
    }else{
        var row = [ ]; 
        row.push('<tr><td><b>'+cgiescape(command)+'</b></td>'); 
        if (val1){
            row.push('<td>'+cgiescape(val1)+'</td>');
        }
        if (lval2){
            for (var i = 0; i < lval2.length; i++){
                row.push('<td>'+cgiescape(lval2[i])+'</td>');
            }
        }
        row.push('</tr>'); 
        if (trlast)
            $(trlast).html($(row.join("")));  
        else
            $('#output_data table.output_content').append($(row.join("")));  
        incrementTabNumber('data');
    }
    
    $('.editor_output div.tabs li.data').addClass('new');
	if(iScrollStart <= 0 && getScrollPosition('data') > 0){
		setTabScrollPosition('data', 'bottom');
	}
}

function writeToChat(seMessage, sechatname){
   while ($('#output_chat .output_content tbody').children().size() >= outputMaxItems) 
        $('#output_chat .output_content tbody').children(':first').remove();

	var iScrollStart = getScrollPosition('chat');
	if(iScrollStart <= 0){
		setTabScrollPosition('chat', 'bottom');
	}

    var oRow = $('<tr><td>' + (sechatname ? sechatname + ": " : "") + seMessage + '</td></tr>');
    $('#output_chat .output_content').append(oRow);
	$('.editor_output .tabs .chat').addClass('new');
	incrementTabNumber('chat');

	if(iScrollStart <= 0 && getScrollPosition('chat') > 0){
		setTabScrollPosition('chat', 'bottom');
	}

    if (sechatname && (sechatname != chatname)){
       	// Currently highlights when there is more than a minute gap.
        if(
			(chatpeopletimes[sechatname] == undefined) || 
			((servernowtime.getTime() - chatpeopletimes[sechatname].getTime())/1000 > 60)
		){
            chatpeopletimes[sechatname] = servernowtime; 
            if (sTabCurrent != 'chat'){
                $('.editor_output .tabs .chat').addClass('chatalert');
			}
        }
     }
}



// *sTab* is the class of the li for the tab to show.
function showTab(sTab)
{
    setTabScrollPosition(sTabCurrent, 'hide'); 
    $('.editor_output .info').children().hide();
    $('.editor_output .controls').children().hide();        
    
    $('#output_' + sTab).show();
    $('#controls_' + sTab).show();
    sTabCurrent = sTab; 

    $('.editor_output div.tabs ul').children().removeClass('selected');
    $('.editor_output div.tabs li.' + sTab).addClass('selected');
    $('.editor_output div.tabs li.' + sTab).removeClass('new chatalert');
	resetTabNumber(sTab);

    setTabScrollPosition(sTab, 'show'); 
}



function writeExceptionDump(exceptiondescription, stackdump, blockedurl, blockedurlquoted) 
{
    if (stackdump) 
    {
        for (var i = 0; i < stackdump.length; i++) 
        {
            var stackentry = stackdump[i]; 
            sMessage = (stackentry.file !== undefined ? (stackentry.file == "<string>" ? stackentry.linetext : stackentry.file) : ""); 
            if (sMessage === undefined) {
                alert("sMessage is undefined in writeExceptionDump, internal error")
            }
            if (stackentry.furtherlinetext !== undefined) {
                sMessage += " -- " + stackentry.furtherlinetext;
            }
            linenumber = (stackentry.file == "<string>" ? stackentry.linenumber : undefined); 
            writeToConsole(sMessage, 'exceptiondump', linenumber); 
            if (stackentry.duplicates > 1) {
                writeToConsole("  + " + stackentry.duplicates + " duplicates", 'exceptionnoesc'); 
            }
        }
    }

    writeToConsole(exceptiondescription, 'exceptiondump'); 
}

//  Increments the number displayed at the top of the tab
function incrementTabNumber(tab){
	if(sTabCurrent != tab) {
		var $i = $('.tabs .' + tab + ' .unread');
		$i.show().text( Number($i.text()) + 1 );
	}
}

function resetTabNumber(tab){
	$('.tabs .' + tab + ' .unread').empty().hide();
}


//Setup Tabs
function setupTabs(){
    $('.editor_output .tabs a').bind('click', function(e){
    	e.preventDefault();
        showTab($(this).attr('href').replace('#output_', ''));
    }).eq(0).trigger('click');
}

