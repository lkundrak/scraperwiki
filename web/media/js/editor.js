// Main module.  All references to codeeditor have been moved into editorcodemirror.js


var lastRev = null; 
var setupKeygrabs;     // function
var inRollback = false;


//	A duplicate of the usual function (in scraperwiki.js)
//	but with a few changes for the unusual Editor DOM layout
function newAlert(htmlcontent, level, actions){
	if(typeof(level) != 'string'){ level = 'error'; }
	$alert_outer = $('<div>').attr('id','alert_outer').addClass(level);
	$alert_inner = $('<div>').attr('id','alert_inner').html(htmlcontent);
	if(typeof(actions) == 'object'){
		console.log('actions is an object');
		var a = '<a href="' + actions.url + '"';
		if(typeof(actions.secondary) != 'undefined'){
			s += ' class="secondary"'
		}
		a += '>' + actions.text + '</a>';
		$alert_inner.append(a);
	}
	console.log(typeof(actions));
	$('<a>').attr('id','alert_close').bind('click', function(){ 
		$('#alert_outer').slideUp(250);
		$('body div.editor').animate({paddingTop:0}, 250);
	}).appendTo($alert_inner);
	$('body div.editor').prepend($alert_outer.prepend($alert_inner)).css('padding-top', $('#alert_outer').outerHeight());
}

$(document).ready(function() 
{
    // variable transmitted through the html
    var short_name = $('#short_name').val();
    var guid = $('#scraper_guid').val();
    var username = $('#username').val(); 
    var userrealname = $('#userrealname').val(); 
    var isstaff = $('#isstaff').val(); 
    var beta_user = $('#beta_user').val(); 
    scraperlanguage = $('#scraperlanguage').val(); 
    var scraper_owners = ( $('#scraper_owners').val().length != 0 ? $('#scraper_owners').val().split(';') : [] );
    var run_type = $('#code_running_mode').val();
    codemirror_url = $('#codemirror_url').val();
    var wiki_type = $('#id_wiki_type').val(); 
    var savecode_authorized = $('#savecode_authorized').val(); 
    
    texteditor = $('#texteditor').val(); 
    if (window.location.hash == "#plain")
        texteditor = "plain"; 
    if (navigator.userAgent.match(/iPad|iPhone|iPod/i) != null)
        texteditor = "plain"; 
    
    lastRev = $('#originalrev').val(); 
    var lastRevDateEpoch = ($('#originalrevdateepoch').val() ? parseInt($('#originalrevdateepoch').val()) : 0); 
    var lastRevUserName = $('#originalrevusername').val(); 
    var lastRevUserRealName = $('#originalrevuserrealname').val(); 
    var rollbackRev = $('#rollback_rev').val(); 

    if (rollbackRev != "") 
        inRollback = true;

    var lastupdaterevcall = null;   // timeout object
    function writeUpdateLastSavedRev() 
    {
        lastupdaterevcall = null; 
        if ((lastRev != "") && (lastRev != "unsaved") && (lastRev != "draft"))
        {
            if (inRollback) {
                prefix = "Rollback preview of ";
            } else {
                prefix = "Last edited";
                if (lastRev != $('#originalrev').val()) {
                    prefix = "Last saved";
                }
            }

            var twhen = new Date(lastRevDateEpoch * 1000);
            var tago = jQuery.timeago(twhen);
            $("#idlastrev").html('<span title="' + 
                    'By ' + lastRevUserRealName + ' (' + lastRevUserName + '), ' +
                    ' rev ' + String(lastRev) + ' \n' + 
                    'on ' + String(twhen) + '">' + prefix + ' ' + tago + '</span>');
            lastupdaterevcall = window.setTimeout(writeUpdateLastSavedRev, 60000);
        }
    }
    
    function updateLastSavedRev(rev, revdateepoch)
    {   
        lastRev = rev;
        lastRevDateEpoch = revdateepoch;
        lastRevUserName = username;
        lastRevUserRealName = userrealname;
        chainpatchnumber = 0; 
        nextchainpatchnumbertoreceive = 0; 
        receivechainpatchqueue.length = 0; 
        lastreceivedchainpatch = null; 
        chainpatches.length = 0; 
        inRollback = false;
        if (lastupdaterevcall != null)
            window.clearTimeout(lastupdaterevcall); 
        lastupdaterevcall = window.setTimeout(writeUpdateLastSavedRev, 50); 
        rollbackRev = "";
        $('#rollback_warning').hide();
    }
    lastupdaterevcall = window.setTimeout(writeUpdateLastSavedRev, 50); 

    var lastsavedcode  = ''; // used to tell if we should expect a null back from the revision log

    // runtime information
    var runID = ''; 
    var lxc = ''; 

    setupCodeEditor(); 
    setupMenu();
    setupTabs();
    setupToolbar();
    setupResizeEvents();
    setupOrbited();


    //add hotkey - this is a hack to convince codemirror (which is in an iframe) / jquery to play nice with each other
    //which means we have to do some seemingly random binds/unbinds
    function addHotkey(sKeyCombination, oFunction)
    {
        $(document).bind('keydown', sKeyCombination, function() { return false; });
        var cd = (codeeditor ? codeeditor.win.document : document); 
        $(cd).unbind('keydown', sKeyCombination);
        $(cd).bind('keydown', sKeyCombination, function(evt) { oFunction(); return false; }); 
    }

    setupKeygrabs = function()
    {
        if (navigator.userAgent.toLowerCase().indexOf("mac") != -1) 
        {
            addHotkey('meta+s', saveScraper); 
            addHotkey('meta+r', sendCode);
            addHotkey('meta+p', popupPreview); 
        }
        addHotkey('ctrl+s', saveScraper); 
        addHotkey('ctrl+r', sendCode);
        addHotkey('ctrl+p', popupPreview); 
    };

	//	Disable the backspace key on the Editor page
	//	I know! Naughty. 
	//	But users keep pressing delete without realising no input is focussed,
	//	causing them to lose all their changes. Which makes me sad :-(
	$(document).keydown(function(e) { 
		if (e.keyCode === 8) { 
			var element = e.target.nodeName.toLowerCase();
			if (element != 'input' && element != 'textarea') { return false; }
		}
	});

    //Setup Menu
    function setupMenu()
    {
        //$('#oldquickhelp').click(popupHelp); 
        $('#chat_line').bind('keypress', function(eventObject) 
        {
            var key = (eventObject.charCode ? eventObject.charCode : eventObject.keyCode ? eventObject.keyCode : 0);
            var target = eventObject.target.tagName.toLowerCase();
            if (key === 13 && target === 'input') 
            {
                eventObject.preventDefault();
                if (bConnected) 
                {
                    lasttypetime = new Date(); 
                    data = {"command":'chat', "guid":guid, "username":username, "text":$('#chat_line').val()};
                    sendjson(data); 
                    $('#chat_line').val(''); 
                }
                return false; 
            }
            return true; 
        })

        $('#id_urlquery').bind('keypress', function(eventObject) 
        {
            var key = (eventObject.charCode ? eventObject.charCode : eventObject.keyCode ? eventObject.keyCode : 0);
            var target = eventObject.target.tagName.toLowerCase();
            if (key === 13 && target === 'input') 
            {
                eventObject.preventDefault();
                sendCode(); 
                return false; 
            }
            return true; 
        })

        // somehow this system fails if you do a browser back button to the editor
        $('#id_urlquery').focus(function(){
            if ($(this).hasClass('hint')) {
                $(this).val('');
                $(this).removeClass('hint');
            }
        });
        $('#id_urlquery').blur(function() 
        {
            if(!$(this).hasClass('hint') && ($(this).val() == '')) {
                $(this).val('query_string');
                $(this).addClass('hint');
            }
        });
        $('#id_urlquery').blur();

        if (!savecode_authorized) 
            $(username ? '#protected_warning' : '#login_warning').show();
    }
    
    

    conn.onopen = function(code)
    {
        sChatTabMessage = 'Chat'; 
        $('.editor_output div.tabs li.chat a').html(sChatTabMessage + '<b class="unread"></b>');

        writeToChat('Connection opened: ' + (conn.readyState == conn.READY_STATE_OPEN ? 'Ready' : 'readystate=' + conn.readyState)); 
        bConnected = true; 

        // send the username and guid of this connection to twisted so it knows who's logged on
        data = { "command":'connection_open', 
                 "guid":guid, 
                 "username":username, 
                 "savecode_authorized":savecode_authorized, 
                 "userrealname":userrealname, 
                 "language":scraperlanguage, 
                 "scrapername":short_name, 
                 "originalrev":lastRev, 
                 "isstaff":isstaff };
        sendjson(data);
    }



    // read data back from twisted (called from editorqueues)
    receiveRecordMain = function(data){
		if (data.nowtime){
        	servernowtime = parseISOdate(data.nowtime); 
		}
        if (data.message_type == "console") {
            writeRunOutput(data.content);     // able to divert text to the preview iframe
        } else if (data.message_type == "sources") {
            writeToSources(data.url, data.mimetype, data.bytes, data.failedmessage, data.cached, data.cacheid, data.ddiffer, data.fetchtime)
        } else if (data.message_type == "editorstatus") {
            recordEditorStatus(data); 
        } else if (data.message_type == "chat") {
            writeToChat(cgiescape(data.message), data.chatname); 
        } else if (data.message_type == "saved") {
            writeToChat("<i>saved</i>", data.chatname);  
        } else if (data.message_type == "othersaved") {
            reloadScraper();
            writeToChat("<i>saved in another window</i>", data.chatname);  
        } else if (data.message_type == "requestededitcontrol") {
			var lasttypeseconds = (new Date() - lasttypetime)/1000;			
			if( scraper_owners.indexOf(data.username) == -1 && lasttypeseconds < 60 ){
				msg = "Sorry, you cannot steal control from " + chatname + " they last typed " + Math.round(lasttypeseconds) + " seconds ago. Try again in " + Math.round(60 - lasttypeseconds) + " seconds."
				data = {"command": 'chat', "guid": guid, "username": "Could not steal control", "text": msg};
                sendjson(data);
			} else {
				iselectednexteditor = loggedineditors.indexOf(data.username);
				changeAutomode('autoload');
				writeToChat("<b>requestededitcontrol: " + data.username + " stole editor control");
			}			
        } else if (data.message_type == "giveselrange") {
            //writeToChat("<b>selrange: "+data.chatname+" has made a select range: "+$.toJSON(data.selrange)+"</b>"); 
            makeSelection(data.selrange); // do it anyway
        } else if (data.message_type == "data") {
            writeToData(data.content);
        } else if (data.message_type == "sqlitecall") {
            writeToSqliteData(data.command, data.val1, data.lval2);
        } else if (data.message_type == "exception") {
            writeExceptionDump(data.exceptiondescription, data.stackdump, data.blockedurl, data.blockedurlquoted); 
        } else if (data.message_type == "executionstatus") {
            if (data.content == "startingrun") {
            	startingrun(data.runID, data.uml, data.chatname);
            } else if (data.content == "runcompleted") {
                var messageparts = [ ];
                if (data.elapsed_seconds != undefined)
                    messageparts.push(data.elapsed_seconds + " seconds elapsed"); 
                if (data.CPU_seconds)
                    messageparts.push(data.CPU_seconds + " CPU seconds used"); 
                if (data.exit_status)
                    messageparts.push("exit status " + data.exit_status); 
                if (data.term_sig_text)
                    messageparts.push("terminated by " + data.term_sig_text);
                else if (data.term_sig)
                    messageparts.push("terminated by signal " + data.term_sig);
                writeToConsole("Finished: "+messageparts.join(", "));
            } else if (data.content == "killsignal") {
                writeToConsole(data.message); 
            } else if (data.content == "runfinished") {
                endingrun(data.content, data.contentextra); 
            } else  {
                writeToConsole(data.content);
			}
        } else if (data.message_type == "httpresponseheader") {
            writeToConsole("Header:::", "httpresponseheader"); 
            writeToConsole(data.headerkey + ": " + data.headervalue, "httpresponseheader"); 
        } else if (data.message_type == "typing") {
            $('#lasttypedtimestamp').text(String(new Date())); 
        } else {
            writeToConsole(data.content, data.message_type); 
        }
    }


    //send code request run
    function sendCode() 
    {
        if (!$('.editor_controls #run').length || $('.editor_controls #run').attr('disabled'))
            return; 

        // protect not-ready case
        if ((conn == undefined) || (conn.readyState != conn.READY_STATE_OPEN)) 
        { 
            alert("Not ready, readyState=" + (conn == undefined ? "undefined" : conn.readyState)); 
            return; 
        }

        //send the data
        var code = getcodefromeditor(); 
        var urlquery = (!$('#id_urlquery').length || $('#id_urlquery').hasClass('hint') ? '' : $('#id_urlquery').val()); 
        data = {
            "command"   : "run",
            "guid"      : guid,
            "username"  : username, 
            "userrealname" : userrealname, 
            "beta_user" : beta_user, 
            "language"  : scraperlanguage, 
            "scrapername":short_name,
            "code"      : code,
            "urlquery"  : urlquery,
            "automode"  : $('input#automode').val()
        }

        $('.editor_controls #run').val('Sending');
        $('.editor_controls #run').unbind('click.run'); // prevent a second call to it

            // this is when running a named scraper, who's run is done back through django
        if (guid)
            autosavefunction(code, "editorstimulaterun"); 
            
            // this is when running a draft scraper
        else
        {
            sendjson(data);  // old way of running, directly into twister without stimulate_run
            autosavefunction(code, null); 
        }
    }

    function autosavefunction(code, stimulate_run)
    {
        var automode = $('input#automode').val(); 

            // saves back to django which in turn can stimulate a run in twister
        if (automode == 'autosave')
        {
            if (pageIsDirty)
                saveScraper(stimulate_run); 
            else if (lastsavedcode && (lastsavedcode != code) && codemirroriframe)
            {
                writeToChat("Page should have been marked dirty but wasn't: historysize="+codeeditorundosize()+"  savedundo="+savedundo); 
                saveScraper(stimulate_run); 
            }
            else if (stimulate_run == "editorstimulaterun")
                saveScraper("editorstimulaterun_nosave"); 
        }
            
            // save the scraper if draft mode and we have changed the title
            // see ticket 564
        /*else if (automode == 'draft')
        {
            if (shortNameIsSet())
                saveScraper(false); 
        }*/

        //else if (stimulate_run == "editorstimulaterun")
        //    saveScraper("editorstimulaterun_nosave"); 
    } 


    function changeAutomode(newautomode) 
    {
        $('input#automode').val(newautomode);

        lasttypetime = new Date(); 
        var automode = $('input#automode').val(); 
        if (automode == 'draft')
            ;
        // self demote from editing to watching
        else if (automode == 'autoload')
        {
            $('.editor_controls #watch_button_area').hide();
            setCodeMirrorReadOnly(true);
            $('.editor_controls #btnCommitPopup').attr('disabled', true); 
            $('.editor_controls #run').attr('disabled', true);
            $('.editor_controls #preview').attr('disabled', true);
        }
        writeToChat('Changed automode: ' + automode); 

        data = {"command":'automode', "automode":automode}; 
        if ((automode == "autoload") && (loggedineditors.length >= 3))
            data["selectednexteditor"] = loggedineditors[iselectednexteditor]; 
        sendjson(data); 
    }; 


    function parseISOdate(sdatetime) // used to try and parse an ISOdate, but it's highly irregular and IE can't do it
        {  return new Date(parseInt(sdatetime)); }

    function swtimeago(ctime, servernowtime)
    {
        var seconds = (servernowtime.getTime() - ctime.getTime())/1000; 
        return (seconds < 120 ? seconds.toFixed(0) + " seconds" : (seconds/60).toFixed(1) + " minutes"); 
    }

    function setwatcherstatusmultieditinguser()
    {
        if (iselectednexteditor >= loggedineditors.length)
            iselectednexteditor = 1; 
        var selectednexteditor = loggedineditors[iselectednexteditor]; 
        wstatus = '<a href="'+ $('input#userprofileurl').val().replace(/XXX/g, selectednexteditor) +'" target="_blank">'+selectednexteditor+'</a>'; 
        if (loggedineditors.length >= 3)
            wstatus += ' (<a class="plusone" title="Click to cycle through other watchers">+' + (loggedineditors.length-2) + '</a>)'; 
        wstatus += ' <a class="plusoneselect">is</a> watching'; 
        $('#watcherstatus').html(wstatus); 
        if (loggedineditors.length >= 3)
            $('#watcherstatus .plusone').click(function() { 
				iselectednexteditor += 1; setwatcherstatusmultieditinguser();
				$('#btnWatch').val('Let ' + loggedineditors[iselectednexteditor] + ' edit');
			}); 
        $('#watcherstatus .plusoneselect').click(transmitSelection); 
    }

    // when the editor status is determined it is sent back to the server
    function recordEditorStatus(data) 
    { 
        var boutputstatus = (lasttouchedtime == undefined); 
        //console.log($.toJSON(data)); 
        if (data.nowtime)
            servernowtime = parseISOdate(data.nowtime); 
        if (data.earliesteditor)
            earliesteditor = parseISOdate(data.earliesteditor); 
        if (data.scraperlasttouch)
            lasttouchedtime = parseISOdate(data.scraperlasttouch); 

        editingusername = (data.loggedineditors ? data.loggedineditors[0] : '');  // the first in the list is the primary editor
        loggedineditors = data.loggedineditors;  // this is a list
        loggedinusers = data.loggedinusers;      // this is a list
        nanonymouseditors = data.nanonymouseditors; 
        chatname = data.chatname;   // yes this is reset every time (though it's always the same)
        clientnumber = data.clientnumber; 
        countclientsconnected = data.countclients; 
        var automode = $('input#automode').val(); 

        if (data.message)
            writeToChat('<i>'+cgiescape(data.message)+'</i>'); 

        if (boutputstatus)  // first time
        {
            if (beta_user)
                writeToChat('<i>You are a beta_user</i>'); 
                
            stext = [ ]; 
            stext.push("Editing began " + swtimeago(earliesteditor, servernowtime) + " ago, last touched " + swtimeago(lasttouchedtime, servernowtime) + " ago.  You are client#"+clientnumber); 
            $('.editor_controls #run').attr('disabled', false);  // enable now we have identity (this gets disabled lower down if we lack the permissions)

            var othereditors = [ ]; 
            for (var i = 0; i < data.loggedineditors.length; i++) 
            {
                if (data.loggedineditors[i] != username)
                    othereditors.push(data.loggedineditors[i]); 
            }
            if (othereditors.length)
                stext.push((savecode_authorized ? "; Other editors: " : "; Editors: "), othereditors.join(", ")); 

            var otherusers = [ ]; 
            for (var i = 0; i < data.loggedinusers.length; i++) 
            {
                if (data.loggedinusers[i] != username)
                    otherusers.push(data.loggedinusers[i]); 
            }
            if (otherusers.length)
                stext.push((!savecode_authorized ? "; Other users: " : "; Users: "), otherusers.join(", ")); 

            if (nanonymouseditors - (username ? 0 : 1) > 0) 
                stext.push("; there are " + (nanonymouseditors-(username ? 0 : 1)) + " anonymous users watching"); 
            stext.push("."); 
            writeToChat(cgiescape(stext.join(""))); 
        }

        // draft editing nothing to do
        if (automode == 'draft') 
            return;

		// $('#watcher_alert').show().children('editor_name').text(editingusername);

        // you are the editing user
        if (username && (editingusername == username)){
			$('#run').show();
			$('#btnEdit').hide();
            $('.editor_controls #watch_button_area').toggle((loggedineditors.length != 1));
            if (loggedineditors.length >= 2){
				// Next relinquish will default to previous editor
				if (automode == 'autoload'){
					iselectednexteditor = loggedineditors.length -1; 
				}
		        setwatcherstatusmultieditinguser(); // sets links to call self
				$('#btnWatch').show();
            } else {
                $('#watcherstatus').html("");
				$('#btnWatch').hide();
			}
			$('#btnWatch').val('Let ' + loggedineditors[iselectednexteditor] + ' edit');
			
            if (automode == 'autoload'){
                setCodeMirrorReadOnly(false);
                changeAutomode('autosave'); 
                $('.editor_controls #run').attr('disabled', false);
                $('.editor_controls #preview').attr('disabled', false);
                $('.editor_controls #btnCommitPopup').attr('disabled', false); 
                if (rollbackRev != "") 
                {
                    $('.editor_controls #btnCommitPopup').val('Rollback'); 
                    $('#rollback_warning').show();
                }
                sendjson({"command":'automode', "automode":'autosave'}); 
            }
        }
        // you are not the editing user, someone else is
        else if (editingusername){
			$('#btnWatch, #run').hide();
			$('#btnEdit').show();
            $('#watcherstatus').html('<a href="'+$('input#userprofileurl').val().replace(/XXX/g, editingusername)+'" target="_blank">'+editingusername+'</a> <a class="plusoneselect">is</a> <a class="plusoneediting">editing</a>');
            if (username){
                $('#watcherstatus .plusoneediting, #btnEdit').bind('click', function() { sendjson({"command":'requesteditcontrol', "user":username}); });
			}
            $('#watcherstatus .plusoneselect').bind('click', transmitSelection); 

            if (automode != 'autoload'){
                $('.editor_controls #watch_button_area').hide();
                changeAutomode('autoload'); // watching
                setCodeMirrorReadOnly(true);
                $('.editor_controls #btnCommitPopup').attr('disabled', true); 
                $('.editor_controls #run').attr('disabled', true);
                $('.editor_controls #preview').attr('disabled', true);
                sendjson({"command":'automode', "automode":'autoload'}); 
            }
        }

        // you are not logged in and the only person looking at the scraper
        else
        {
			$('#btnWatch, #btnEdit').hide();
            $('#watcherstatus').text(""); 
            changeAutomode('autosave'); // editing
            $('.editor_controls #watch_button_area').hide();
            if (!savecode_authorized) 
            {
                // special case, if not authorized then we are internally
                // to this javascript an anonymous user, and want to be readonly
                setCodeMirrorReadOnly(true);
                $('.editor_controls #run').attr('disabled', true);
            } 
            else 
            {
                setCodeMirrorReadOnly(false);
                $('.editor_controls #run').attr('disabled', false);
            }
            $('.editor_controls #btnCommitPopup').attr('disabled', false); 
            $('.editor_controls #preview').attr('disabled', false);
            sendjson({"command":'automode', "automode":'autosave'}); 
        }
    }



              
        // message received from twister case
    function startingrun(lrunID, llxc, lchatname) 
    {
        //show the output area
        resizeControls('up');
        
        document.title = document.title + ' *'

        $('#running_annimation').show();
        runID = lrunID; 
        lxc = llxc; 

        //clear the tabs
        clearOutput();
        writeToConsole('Starting run ... ' + (isstaff ? " ["+lxc+"]" : "")); 
        writeToChat('<i>' + lchatname + ' runs scraper</i>'); 

        //unbind run button
        $('.editor_controls #run').unbind('click.run')
        $('.editor_controls #run').addClass('running').val('Stop');

        //bind abort button
        $('.editor_controls #run').bind('click.abort', function() 
        {
            sendjson({"command" : 'kill'}); 
            $('.editor_controls #run').val('Stopping');
            $('.editor_controls #run').unbind('click.abort');
            $('.editor_controls #run').bind('click.stopping', clearJunkFromQueue);
        });
    }
    
    function endingrun(content, contentextra) 
    {
        $('.editor_controls #run').removeClass('running').val('run');
        $('.editor_controls #run').unbind('click.abort');
        $('.editor_controls #run').unbind('click.stopping');
        $('.editor_controls #run').bind('click.run', sendCode);
        writeToConsole(content); 
        if (contentextra)
            writeToConsole("*** internalwarning: "+contentextra); 

        //change title
        document.title = document.title.replace('*', '');
    
        //hide annimation
        $('#running_annimation').hide();
        runID = ''; 
        lxc = ''; 

        // suppress any more activity to the preview frame
        if (draftpreviewwindow != undefined) 
        {
            if (draftpreviewwindow.document)
                draftpreviewwindow.document.close(); 
            draftpreviewwindow = undefined; 
        }

    }




    function reloadScraper()
    {
        $('.editor_controls #btnCommitPopup').val('Loading...').addClass('darkness');
        var oldcode = getcodefromeditor(); 
        var reloadajax = $.ajax({ url: $('input#editorreloadurl').val(), async: false, type: 'POST', data: { oldcode: oldcode }, timeout: 10000 }); 
        var reloaddata = $.evalJSON(reloadajax.responseText); 
        if (codemirroriframe)
            receiveChainpatchFromQueue(reloaddata.code)
        else
            $("#id_code").val(reloaddata.code); 
        updateLastSavedRev(reloaddata.rev, reloaddata.revdateepoch);
        if (reloaddata.selrange)
            makeSelection(reloaddata.selrange); 
        ChangeInEditor("reload"); 
        window.setTimeout(function() { $('.editor_controls #btnCommitPopup').val('save' + (wiki_type == 'scraper' ? ' scraper' : '')).removeClass('darkness'); }, 1100);  
    }; 


    function run_abort() 
    {
        runRequest = runScraper();
        $('.editor_controls #run').unbind('click.run');
        $('.editor_controls #run').addClass('running').val('Stop');
        $('.editor_controls #run').bind('click.abort', function() 
        {
            sendjson({"command" : 'kill'}); 
            $('.editor_controls #run').removeClass('running').val('run');
            $('.editor_controls #run').unbind('click.abort');
            writeToConsole('Run Aborted'); 
            $('.editor_controls #run').bind('click.run', run_abort);
            
            //hide annimation
            $('#running_annimation').hide();
            
            //change title
            document.title = document.title.replace(' *', '');
        });
    }
    
    
    //Setup toolbar
    function setupToolbar()
    {
        // actually the save button
        $('.editor_controls #btnCommitPopup').live('click', function()
        {
            saveScraper(false);  
            return false;
        });
        $('.editor_controls #btnCommitPopup').val('save' + (wiki_type == 'scraper' ? ' scraper' : '')); 

        // the fork button
        $('.editor_controls #btnForkNow').live('click', function()
        {
            window.open($('#fork_url_action').val()); 
            return false;
        });
        $('.editor_controls #btnForkNow').val('copy' + (wiki_type == 'scraper' ? ' scraper' : '')); 

        // the watch button
        $('.editor_controls #btnWatch').live('click', function()
        {
            changeAutomode('autoload');
            return false;
        });
 
        // close editor link (quickhelp link is target blank so no need for this)
        $('#aCloseEditor, #aCloseEditor1, .page_tabs a').click(function()
        {
            if (pageIsDirty && !confirm("You have unsaved changes, leave the editor anyway?"))
                return false; 
            bSuppressDisconnectionMessages = true; 
            sendjson({"command":'loseconnection'});  
			// Neither reset() nor close() is fast .... if (conn)  conn.reset(); 
            return true;
        });

        if (isstaff)
            $('#idlastrev').click(popupDiff); 
        $('.codepreviewer .revchange').click(function() 
        {
            var revchange = parseInt($(this).text()); 
            loadRevIntoPopup(revchange); 
        }); 

        $(window).unload(function()
        {
            bSuppressDisconnectionMessages = true; 
            writeToConsole('window unload'); 
            sendjson({"command":'loseconnection'}); 
            //if (conn)  conn.close();  
        });  
        $(window).bind('beforeunload', function() 
        { 
            bSuppressDisconnectionMessages = true; 
        }); 
        
        /*
        This fires when making a new scraper on some browsers (while doing the
        redirect), so need to prevent that case. Julian had this problem.

        $(window).bind('beforeunload', function() 
        { 
            if (pageIsDirty && !bSuppressDisconnectionMessages)
                return "You have unsaved changes, close the editor anyway?";
        });

        */


        if (wiki_type == 'view')
            $('.editor_controls #preview').bind('click.run', popupPreview);
        else
            $('.editor_controls #preview').hide();


        if (scraperlanguage == 'html')
            $('.editor_controls #run').hide();
        else
            $('.editor_controls #run').bind('click.run', sendCode);
    }

    function popupPreview() 
    {
        if ($('.editor_controls #preview').attr('disabled'))
            return; 

        var urlquery = (!$('#id_urlquery').length || $('#id_urlquery').hasClass('hint') ? '' : $('#id_urlquery').val()); 
        var viewurl = $('input#viewrunurl').val(); 
        var previewmessage = ''; 
        if (urlquery.length != 0) 
        {
            if (urlquery.match(/^[\w%_.;&~+=\-]+$/g)) 
                viewurl = viewurl + '?' + urlquery; 
            else
                previewmessage = ' [' + urlquery + '] is an invalid query string'; 
        }

        // draft case, we can't open the real URL, so we pipe the output from run into another window
        // XXX we could do it this way all the time if preferred, and maybe then merge Run/Preview buttons?
        if (short_name == "") {
            window.close("scraperwiki_preview_" + short_name);
            draftpreviewwindow = window.open(viewurl, "scraperwiki_preview_" + short_name);
            draftpreviewwindow.document.open();
            draftpreviewwindow.focus();
            // note that this could bypass this sendCode for HTML mode, as the
            // code removed by this commit did for the insecure popup window.
            // https://bitbucket.org/ScraperWiki/scraperwiki/changeset/63fbb9f04f58
            sendCode();
        } else {
            // non-draft case, we can open the real URL, so we do that after saving (so people can copy it)
            saveScraper(null,function() {
                w = window.open(viewurl, "scraperwiki_preview_" + short_name);
            }, false); // false - do request synchronously so popup is allowed
        }
    }

    function saveScraper(stimulate_run, callback, async)
    {
        var bSuccess = false;
        if (async == null) {
            // default to asynchronous saving
            async = true;
        }

        //if saving then check if the title is set (must be if guid is set)
        if(shortNameIsSet() == false)
        {
            var sResult = jQuery.trim(prompt('Please enter a title for your scraper'));
            if (sResult != false && sResult != '' && sResult != 'Untitled') 
            {
                $('#id_title').val(sResult);
                aPageTitle = document.title.split('|')
                document.title = sResult + ' | ' + aPageTitle[1]
                bSuccess = true;
            }
        }
        else
            bSuccess = true;

        if (!bSuccess)
            return; 

        atsavedundo = codeeditorundosize(); 

        var currentcode = getcodefromeditor(); 
        var sdata = {
                        title           : $('#id_title').val(),
                        commit_message  : "cccommit",   // could get some use out of this if we wanted to
                                                        // though earliesteditor||| is prepended to this message
                        sourcescraper   : $('#sourcescraper').val(),
                        fork            : $('#fork').val(),
                        wiki_type       : wiki_type,
                        guid            : guid,
                        language        : scraperlanguage,
                        code            : currentcode,
                        earliesteditor  : earliesteditor.toUTCString() // goes into the comment of the commit for grouping a series of commits done in same session
                    }

        if (stimulate_run)
        {
            sdata.stimulate_run = stimulate_run; 
            sdata.urlquery = (!$('#id_urlquery').length || $('#id_urlquery').hasClass('hint') ? '' : $('#id_urlquery').val()); 
            sdata.clientnumber = clientnumber; 
        }

        // on success
        $.ajax({ url:$('input#saveurl').val(), type:'POST', contentType:"application/json", dataType:"html", data:sdata, timeout: 10000, async: async, success:function(response) 
        {
            res = $.evalJSON(response);
            if (res.status == 'Failed')
            {
                alert("Save failed error message: "+res.message); 
                return; 
            }
            if (stimulate_run == "editorstimulaterun_nosave")
            {
                if (res.status != "notsaved")
                    writeToChat(response); 
                return; 
            }


            // 'A temporary version of your scraper has been saved. To save it permanently you need to log in'
            if (res.draft == 'True')
                $('#draft_warning').show();

            // server returned a different URL for the new scraper that has been created.  Now go to it (and reload)
            if (res.url && window.location.pathname != res.url)
            {
                window.location = res.url;
                return;   // without this it sends an erroneous saved signal up to twister
            }

            // ordinary save case.
            window.setTimeout(function() { $('.editor_controls #btnCommitPopup').val('save' + (wiki_type == 'scraper' ? ' scraper' : '')).removeClass('darkness'); }, 1100);  
            if (res.draft != 'True') 
            {
                if (res.rev == null)
                {
                    writeToChat("No difference (null revision number)"); 
                    $('.editor_controls #btnCommitPopup').val('No change'); 
                    if (lastsavedcode && (lastsavedcode != currentcode))
                        alert("Warning, the code repository thinks the code hasn't changed when the editor thinks it has, please try again"); 
                }
                else 
                {
                    updateLastSavedRev(res.rev, res.revdateepoch);
                    writeToChat("Saved rev number: " + res.rev); 
                    $('.editor_controls #btnCommitPopup').val('Saved').addClass('darkness'); 
                    if (bConnected)
                        sendjson({"command":'saved', "rev":res.rev}); 
                }
                lastsavedcode = currentcode; 
            }
            ChangeInEditor("saved"); 

			if(_gaq){
				_gaq.push(['_trackPageview', "/" + wiki_type + "s/" + $('#id_title').val() + "/saved/"]);
			}

            if (callback) {
                callback();
            }
        },
        error: function(jqXHR, textStatus, errorThrown)
        {
            var errmessage = "Response error: " + textStatus + "  thrown: " + errorThrown + "  text:" + jqXHR.responseText; 
            writeToChat(errmessage);
			newAlert('Sorry, something went wrong with the save. Try copying your code and reloading the page.');
            window.setTimeout(function() { $('.editor_controls #btnCommitPopup').val('save' + (wiki_type == 'scraper' ? ' scraper' : '')).removeClass('darkness'); }, 1100);  
        }});

        if (stimulate_run != "editorstimulaterun_nosave")
            $('.editor_controls #btnCommitPopup').val('Saving ...');
    }

    function setupResizeEvents()
    {
        $(window).resize(onWindowResize);

        $("#codeeditordiv").resizable(
        {
            handles: 's',   
            autoHide: false, 
            start: function(event, ui) 
            {
                var maxheight = $("#codeeditordiv").height() + $(window).height() - $("#outputeditordiv").position().top;

                $("#codeeditordiv").resizable('option', 'maxHeight', maxheight);

                //cover iframe
                var oFrameMask = $('<div id="framemask"></div>');
                oFrameMask.css({ position: 'absolute', top: 0, left:0, background:'none', zindex: 200, width: '100%', height: '100%' }); 
                $(".editor_code").append(oFrameMask); 
            },
            stop: function(event, ui)  
            { 
                resizeCodeEditor(); 
                $('#framemask').remove();
            }
        }); 

        // bind the double-click (causes problems with the jquery interface as it doesn't notice the mouse exiting the frame)
        // $(".ui-resizable-s").bind("dblclick", resizeControls);
    }

    function shortNameIsSet()
    {
        var sTitle = jQuery.trim($('#id_title').val());
        return sTitle != 'Untitled' && sTitle != '' && sTitle != undefined && sTitle != false;
    }



    function writeRunOutput(sMessage) 
    {
        writeToConsole(sMessage, 'console'); 
        if ((draftpreviewwindow != undefined) && (draftpreviewwindow.document != undefined)) {
            draftpreviewwindow.document.write(sMessage); 
       }
    }



        // share this with history.html through codeviewer.js, and start to bring in the diff technology from there
        // and also set the date for the revision
    var fetchedcache = { }; // cached code of different versions
    function cachefetch(cid, callback)
    {
        if (cid && (fetchedcache[cid] == undefined))
        {
            var url; 
            if (cid.substring(0, 4) == "?rev")
                url = $("#rawcodeurl").val()+cid; 
            else
                url = $("#diffsequrl").val()+cid; 
            $.ajax({url:url, success: function(sdata) 
            {
                fetchedcache[cid] = sdata; 
                callback(); 
            }}); 
        }
        else
            callback(); 
    }

    function loadRevIntoPopup(revchange)
    {
        var codepreviewerdiv = $('.simplemodal-wrap .codepreviewer'); 
        var currrev = parseInt(codepreviewerdiv.find('span.rev').text()); 
        var rev = parseInt(codepreviewerdiv.find('span.prevrev').text()); 
        var newrev = Math.max(0, Math.min(currrev, rev + revchange)); 
        codepreviewerdiv.find('span.prevrev').text(newrev); 
        var cidrev = "?rev="+newrev; 
        cachefetch(cidrev, function() 
        { 
            var wrapheight = $('.simplemodal-wrap').height(); 
            codepreviewerdiv.find('.outputlines').empty(); 
            codepreviewerdiv.find('.linenumbers').empty(); 
            highlightCode(fetchedcache[cidrev], Parser, codepreviewerdiv); 
            $('.simplemodal-wrap').css("height", wrapheight + "px").css("overflow", "auto"); 
        }); 
    }

    function popupDiff()
    {
        var rev = parseInt($("#idlastrev span").attr("title").replace("Revision: ", ""));
        var prevrev = rev - 1; 
        if (prevrev < 0)
            return; 
        modaloptions = { overlayClose: true, 
                         overlayCss: { cursor:"auto" }, 
                         containerCss:{ borderColor:"#00f", "borderLeft":"2px solid black", height:"80%", padding:0, width:"90%", "text-align":"left", cursor:"auto" }, 
                         containerId: 'simplemodal-container' 
                       }; 
        $('.codepreviewer').modal(modaloptions); 
        var codepreviewerdiv = $('.simplemodal-wrap .codepreviewer'); 
        codepreviewerdiv.find('span.prevrev').text(rev); 
        codepreviewerdiv.find('span.rev').text(rev); 
        loadRevIntoPopup(0); 
    }







    function onWindowResize() 
    {
        var maxheight = $("#codeeditordiv").height() + $(window).height() - $("#outputeditordiv").position().top; 
        if (maxheight < $("#codeeditordiv").height())
            $("#codeeditordiv").animate({ height: maxheight }, 100, "swing", resizeCodeEditor);
        resizeCodeEditor();
    }

	$('li.console, li.console a').bind('click', function(){
		if(_gaq){ _gaq.push(['_trackPageview', window.location.pathname + '/tab/console']); }
	});

	$('li.data, li.data a').bind('click', function(){
		if(_gaq){ _gaq.push(['_trackPageview', window.location.pathname + '/tab/data']); }
	});

	$('li.sources, li.sources a').bind('click', function(){
		if(_gaq){ _gaq.push(['_trackPageview', window.location.pathname + '/tab/sources']); }
	});

	$('li.chat, li.chat a').bind('click', function(){
		if(_gaq){ _gaq.push(['_trackPageview', window.location.pathname + '/tab/chat']); }
	});

	$('a.helplink').bind('click', function(){
		if(_gaq){ _gaq.push(['_trackPageview', window.location.pathname + '/tab/documentation']); }
	});
	
	
	

});
