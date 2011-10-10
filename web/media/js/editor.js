


$(document).ready(function() {

    // editor window dimensions
    var codeeditor = null;
    var codemirroriframe = null; // the actual iframe of codemirror that needs resizing (also signifies the frame has been built)
    var codeeditorreadonly = false; 
    var codemirroriframeheightdiff = 0; // the difference in pixels between the iframe and the div that is resized; usually 0 (check)
    var codemirroriframewidthdiff = 0;  // the difference in pixels between the iframe and the div that is resized; usually 0 (check)
    var previouscodeeditorheight = 0; //$("#codeeditordiv").height() * 3/5;    // saved for the double-clicking on the drag bar
    var draftpreviewwindow = null;

    // variable transmitted through the html
    var short_name = $('#short_name').val();
    var guid = $('#scraper_guid').val();
    var username = $('#username').val(); 
    var userrealname = $('#userrealname').val(); 
    var isstaff = $('#isstaff').val(); 
    var beta_user = $('#beta_user').val(); 
    var scraperlanguage = $('#scraperlanguage').val(); 
    var run_type = $('#code_running_mode').val();
    var codemirror_url = $('#codemirror_url').val();
    var wiki_type = $('#id_wiki_type').val(); 
    var savecode_authorized = $('#savecode_authorized').val(); 
    
    var texteditor = $('#texteditor').val(); 
    if (window.location.hash == "#plain")
        texteditor = "plain"; 
    
    var lastRev = $('#originalrev').val(); 
    var lastRevDateEpoch = ($('#originalrevdateepoch').val() ? parseInt($('#originalrevdateepoch').val()) : 0); 
    var lastRevUserName = $('#originalrevusername').val(); 
    var lastRevUserRealName = $('#originalrevuserrealname').val(); 
    var rollbackRev = $('#rollback_rev').val(); 

    var inRollback = false;
    if (rollbackRev != "") 
        inRollback = true;

    var lastupdaterevcall = null; 
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

    var lastsavedcode   = ''; // used to tell if we should expect a null back from the revision log

    // runtime information
    var runID = ''; 
    var uml = ''; 

    var parsers = Array();
    var stylesheets = Array();
    var indentUnits = Array();
    var parserConfig = Array();
    var parserName = Array();
    var codemirroroptions = undefined; 

    var pageIsDirty = true;

    var atsavedundo = 0; // recorded at start of save operation
    var savedundo = 0; 
    var lastundo = 0;

    var receiverecordcall = null; 
    var receiverecordqueue = [ ]; 
    var receivechatqueue = [ ]; 
    var receivechainpatchqueue = [ ]; // coming in
    var receivechainpatchcall = null; // or function or "waitingforonchange", "doingothertyping"

    var lasttypetime = new Date(); 
    var chainpatches = [ ];   // stack going out
    var chainpatchnumber = 0; // counts them going out 

    var nextchainpatchnumbertoreceive = 0; 
    var lastreceivedchainpatch = null; 

    setupCodeEditor(); 
    setupMenu();
    setupTabs();
    setupToolbar();
    setupResizeEvents();
    setupOrbited();
    

    // keep delivery load of chain patches down and remove excess typing signals
    function sendChainPatches()
    {
        if (chainpatches.length > 0)
        {
            var chainpatch = chainpatches.shift(); 
            //writeToChat("-- "+$.toJSON(chainpatch)); 
            if (bConnected)
                sendjson(chainpatch); 
        }
        // clear out the ones that are pure typing messages sent in non-broadcast mode
        while ((chainpatches.length > 0) && (chainpatches[0].insertlinenumber == undefined))
            chainpatches.shift(); 

        if (chainpatches.length > 0)
            window.setTimeout(sendChainPatches, 2); 
    }

    // called from editortabs.js
    SelectEditorLine = function(iLine)
    {
        codeeditor.selectLines(codeeditor.nthLine(iLine), 0, codeeditor.nthLine(iLine + 1), 0); 
    }


    function ChangeInEditor(changetype) 
    {
        lasttypetime = new Date(); 
        var lpageIsDirty; 
        if (codemirroriframe)
        {
            var historysize = codeeditor.historySize(); 
            var automode = $('input#automode').val(); 
    
            if (changetype == "saved")
                savedundo = atsavedundo
            if (changetype == "reload")
                savedundo = historysize.undo + historysize.lostundo; 
            if ((changetype == "reload") || (changetype == "initialized"))
                lastsavedcode = codeeditor.getCode(); 
            if (changetype == "initialized")
                lastundo = 0; 
    
            var lpageIsDirty = (historysize.undo + historysize.lostundo != savedundo); 
        }
        else
            lpageIsDirty = (changetype == "edit"); 

        if (pageIsDirty != lpageIsDirty)
        {
            pageIsDirty = lpageIsDirty; 
            if ((lastRev != "") && (lastRev != "unsaved") && (lastRev != "draft") && (!inRollback)) {
                $('.editor_controls #btnCommitPopup').attr('disabled', !pageIsDirty); 
            } else {
                $('.editor_controls #btnCommitPopup').attr('disabled', false); 
            }
        }

        if (changetype != 'edit')
            return; 
        if (automode != 'autosave')
            return; 
        
        // if patches are coming in of we are waiting for a timeout then don't send any patches back 
        // as this can create a ping-pong effect between two windows of the same editing user
        if (receivechainpatchcall != null)
            return; 
        
        // make outgoing patches (if there is anyone to receive them)
        if (codemirroriframe && (countclientsconnected != 1))
        {
            var llchainpatches = [ ];
            lastundo = MakeChainPatches(llchainpatches, codeeditor, lastundo); 
            for (var i = 0; i < llchainpatches.length; i++)
            {
                var chainpatch = llchainpatches[i]; 
                chainpatch['chainpatchnumber'] = chainpatchnumber;
                chainpatch['chatname'] = chatname;
                chainpatch['rev'] = lastRev; 
                chainpatch['clientnumber'] = clientnumber; 
                if (chainpatch['insertions'] != null)
                    chainpatches.push(chainpatch); 
                else
                    writeToChat("<i>Chain patch failed to be generated</i>"); // still advance chainpatchnumber so all the watchers can get out of sync accordingly
                chainpatchnumber++; 
            }
            if (nextchainpatchnumbertoreceive >= 0)
                nextchainpatchnumbertoreceive = chainpatchnumber; 
        }
        
        // plain text area case not coded for
        else 
        {
            chainpatches.push({"command":'typing', "chainpatchnumber":chainpatchnumber, "rev":lastRev, "clientnumber":clientnumber}); 
            chainpatchnumber++; 
            if (nextchainpatchnumbertoreceive >= 0)
                nextchainpatchnumbertoreceive = chainpatchnumber; 
        }
        
        if (chainpatches.length > 0)
            sendChainPatches(); 
    }



    //setup code editor
    function setupCodeEditor()
    {
        // destroy any existing codemirror, so we can remake it with right readonly state
        if (codeeditor) {
            codeeditor.toTextArea("id_code"); 
            codeeditor = null;
            codemirroriframe = null;  // this only gets set once again when we know the editor has been initialized
        }

        // set other things readonly or not
        $('#id_title').attr("readonly", (codeeditorreadonly ? "yes" : ""));

        // just a normal textarea
        if (texteditor == "plain")
        {
            $('#id_code').keypress(function() { ChangeInEditor("edit"); }); 
            setupKeygrabs();
            resizeControls('first');
            $('#id_code').attr("readonly", (codeeditorreadonly ? "yes" : ""));
            setCodeeditorBackgroundImage(codeeditorreadonly ? 'url(/media/images/staff.png)' : 'none');
            return;
        }

        // codemirror
        parsers['python'] = ['../contrib/python/js/parsepython.js'];
        parsers['php'] = ['../contrib/php/js/tokenizephp.js', '../contrib/php/js/parsephp.js', '../contrib/php/js/parsephphtmlmixed.js' ];
        parsers['ruby'] = ['../../ruby-in-codemirror/js/tokenizeruby.js', '../../ruby-in-codemirror/js/parseruby.js'];
        parsers['html'] = ['parsexml.js', 'parsecss.js', 'tokenizejavascript.js', 'parsejavascript.js', 'parsehtmlmixed.js']; 
        parsers['javascript'] = ['tokenizejavascript.js', 'parsejavascript.js']; 

        stylesheets['python'] = [codemirror_url+'contrib/python/css/pythoncolors.css', '/media/css/codemirrorcolours.css'];
        stylesheets['php'] = [codemirror_url+'contrib/php/css/phpcolors.css', '/media/css/codemirrorcolours.css'];
        stylesheets['ruby'] = ['/media/ruby-in-codemirror/css/rubycolors.css', '/media/css/codemirrorcolours.css'];
        stylesheets['html'] = [codemirror_url+'/css/xmlcolors.css', codemirror_url+'/css/jscolors.css', codemirror_url+'/css/csscolors.css', '/media/css/codemirrorcolours.css']; 
        stylesheets['javascript'] = [codemirror_url+'/css/jscolors.css', '/media/css/codemirrorcolours.css']; 

        indentUnits['python'] = 4;
        indentUnits['php'] = 4;
        indentUnits['ruby'] = 2;
        indentUnits['html'] = 4;
        indentUnits['javascript'] = 4;

        parserConfig['python'] = {'pythonVersion': 2, 'strictErrors': true}; 
        parserConfig['php'] = {'strictErrors': true}; 
        parserConfig['ruby'] = {'strictErrors': true}; 
        parserConfig['html'] = {'strictErrors': true}; 
        parserConfig['javascript'] = {'strictErrors': true}; 

        parserName['python'] = 'PythonParser';
        parserName['php'] = 'PHPHTMLMixedParser'; // 'PHPParser';
        parserName['ruby'] = 'RubyParser';
        parserName['html'] = 'HTMLMixedParser';
        parserName['javascript'] = 'JSParser';

        // allow php to access HTML style parser
        parsers['php'] = parsers['html'].concat(parsers['php']);
        stylesheets['php'] = stylesheets['html'].concat(stylesheets['php']); 

        // track what readonly state we thought we were going to, in case it
        // changes mid setup of CodeMirror
        var expectedreadonly = codeeditorreadonly;

        codemirroroptions = {
            parserfile: parsers[scraperlanguage],
            stylesheet: stylesheets[scraperlanguage],
            path: codemirror_url + "js/",
            domain: document.domain, 
            textWrapping: true,
            lineNumbers: true,
            indentUnit: indentUnits[scraperlanguage],
            readOnly: expectedreadonly, // cannot be changed once started up
            undoDepth: 200,  // defaults to 50.  
            undoDelay: 300,  // (default is 800)
            tabMode: "shift", 
            disableSpellcheck: true,
            autoMatchParens: true,
            width: '100%',
            parserConfig: parserConfig[scraperlanguage],
            enterMode: "flat",    // default is "indent" (which I have found buggy),  also can be "keep"
            electricChars: false, // default is on, the auto indent whe { is typed (annoying when doing html)
            reindentOnLoad: false, 
            onChange: function ()  { ChangeInEditor("edit"); },  // (prob impossible to tell difference between actual typing and patch insertions from another window)
            //noScriptCaching: true, // essential when hacking the codemirror libraries

            // this is called once the codemirror window has finished initializing itself
            initCallback: function() 
            {
                codemirroriframe = codeeditor.frame // $("#id_code").next().children(":first"); (the object is now a HTMLIFrameElement so you have to set the height as an attribute rather than a function)
                codemirroriframeheightdiff = codemirroriframe.height - $("#codeeditordiv").height(); 
                codemirroriframewidthdiff = codemirroriframe.width - $("#codeeditordiv").width(); 
                setupKeygrabs();
                resizeControls('first');
                ChangeInEditor("initialized"); 

                // set up other readonly values, after rebuilding the CodeMirror editor
                setCodeeditorBackgroundImage(expectedreadonly ? 'url(/media/images/staff.png)' : 'none');

                if (expectedreadonly) {
                    $('.editor_controls #btnCommitPopup').hide();
                    $('.editor_controls #btnForkNow').show();
                } else {
                    $('.editor_controls #btnCommitPopup').show();
                    $('.editor_controls #btnForkNow').hide();
                }

                // our readonly state was changed under our feet while setting
                // up CodeMirror; force a resetup of CodeMirror again
                if (expectedreadonly != codeeditorreadonly) 
                {
                    var lcodeeditorreadonly = codeeditorreadonly; 
                    codeeditorreadonly = expectedreadonly;  // set it back 
                    setCodeMirrorReadOnly(lcodeeditorreadonly);
                }
            } 
        };

        // now puts it in a state of building where codeeditor!=null and codemirroriframe==null
        codeeditor = CodeMirror.fromTextArea("id_code", codemirroroptions); 
    }



    function setCodeMirrorReadOnly(val) 
    {
        if (codeeditorreadonly == val) 
            return;
        codeeditorreadonly = val;
        writeToChat('set codemirror editor to ' + (codeeditorreadonly ? "readonly" : "editable")); 

            // this rebuilds the entire code editor again!!!
        window.setTimeout(setupCodeEditor, 1); 
    }

    function setCodeeditorBackgroundImage(lcodeeditorbackgroundimage)
    {
        if (codemirroriframe) // also signifies the frame has been built
            codeeditor.win.document.body.style.backgroundImage = lcodeeditorbackgroundimage; 
        else
            $('#id_code').css("background-image", lcodeeditorbackgroundimage); 
    }

    //add hotkey - this is a hack to convince codemirror (which is in an iframe) / jquery to play nice with each other
    //which means we have to do some seemingly random binds/unbinds
    function addHotkey(sKeyCombination, oFunction)
    {
        $(document).bind('keydown', sKeyCombination, function() { return false; });
        var cd = (codeeditor ? codeeditor.win.document : document); 
        $(cd).unbind('keydown', sKeyCombination);
        $(cd).bind('keydown', sKeyCombination, function(evt) { oFunction(); return false; }); 
    }

    function setupKeygrabs()
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

        // context sensitive detection (not used at the moment)
    function popupHelp()
    {
        // establish what word happens to be under the cursor here (and maybe even return the entire line for more context)
        var cursorpos = codeeditor.cursorPosition(true); 
        var cursorendpos = codeeditor.cursorPosition(false); 
        var line = codeeditor.lineContent(cursorpos.line); 
        var character = cursorpos.character; 

        var ip = character; 
        var ie = character;
        while ((ip >= 1) && line.charAt(ip-1).match(/[\w\.#]/g))
            ip--; 
        while ((ie < line.length) && line.charAt(ie).match(/\w/g))
            ie++; 
        var word = line.substring(ip, ie); 

        while ((ip >= 1) && line.charAt(ip-1).match(/[^'"]/g))
            ip--; 
        while ((ie < line.length) && line.charAt(ie).match(/[^'"]/g))
            ie++; 
        if ((ip >= 1) && (ie < line.length) && line.charAt(ip-1).match(/['"]/g) && (line.charAt(ip-1) == line.charAt(ie)))
            word = line.substring(ip, ie); 
        if (word.match(/^\W*$/g))
            word = ""; 

        var quickhelpparams = { language:scraperlanguage, short_name:short_name, wiki_type:wiki_type, username:username, line:line, character:character, word:word }; 
        if (cursorpos.line == cursorendpos.line)
            quickhelpparams["endcharacter"] = cursorendpos.character; 

        $.modal('<iframe width="100%" height="100%" src='+$('input#quickhelpurl').val()+'?'+$.param(quickhelpparams)+'></iframe>', 
        {
            overlayClose: true,
            containerCss: { borderColor:"#ccc", height:"80%", padding:0, width:"90%" }, 
            overlayCss: { cursor:"auto" }, 
            onShow: function() 
            {
                $('.simplemodal-wrap').css("overflow", "hidden"); 
                $('.simplemodal-wrap iframe').width($('.simplemodal-wrap').width()-2); 
                $('.simplemodal-wrap iframe').height($('.simplemodal-wrap').height()-2); 
            }
        }); 
    }

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
        $('.editor_output div.tabs li.chat a').html(sChatTabMessage);

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


    //read data back from twisted
    ReceiveRecordJ = function(jdata)
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
        
        receiveRecord(jdata);
        if (receiverecordqueue.length + receivechatqueue.length >= 1)
            receiverecordcall = window.setTimeout(function() { receiveRecordFromQueue(); }, 1); 
    }

    //read data back from twisted
    function receiveRecord(data) {
          if (data.nowtime)
             servernowtime = parseISOdate(data.nowtime); 
			
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

// this should popup something if there has been no activity for a while with a count-down timer that eventually sets the editinguser down and
// self-demotes to autoload with the right value of iselectednexteditor selected
writeToChat("<b>requestededitcontrol: "+data.username+ " has requested edit control but you have last typed " + (new Date() - lasttypetime)/1000 + " seconds ago"); 

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
              if (data.content == "startingrun")
                startingrun(data.runID, data.uml, data.chatname);
              else if (data.content == "runcompleted") {
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
              } else if (data.content == "killsignal")
                writeToConsole(data.message); 
              else if (data.content == "runfinished") 
                endingrun(data.content, data.contentextra); 
              else 
                writeToConsole(data.content); 

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
        var code = (codeeditor ? codeeditor.getCode() : $('#id_code').val())
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
                var historysize = codeeditor.historySize(); 
                writeToChat("Page should have been marked dirty but wasn't: historysize="+historysize.undo+"  savedundo="+savedundo); 
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
            wstatus += ' (<a class="plusone">+' + (loggedineditors.length-2) + '</a>)'; 
        wstatus += ' <a class="plusoneselect">is</a> watching'; 
        $('#watcherstatus').html(wstatus); 
        if (loggedineditors.length >= 3)
            $('#watcherstatus .plusone').click(function() { iselectednexteditor += 1; setwatcherstatusmultieditinguser() }); 
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

        // you are the editing user
        if (username && (editingusername == username))
        {
            $('.editor_controls #watch_button_area').toggle((loggedineditors.length != 1));

            if (loggedineditors.length >= 2)
                setwatcherstatusmultieditinguser(); // sets links to call self
            else
                $('#watcherstatus').html(""); 

            if (automode == 'autoload')
            {
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
        else if (editingusername)
        {
            $('#watcherstatus').html('<a href="'+$('input#userprofileurl').val().replace(/XXX/g, editingusername)+'" target="_blank">'+editingusername+'</a> <a class="plusoneselect">is</a> <a class="plusoneediting">editing</a>'); 
            if (username)
                $('#watcherstatus .plusoneediting').click(function() { sendjson({"command":'requesteditcontrol', "user":username}); }); 
            $('#watcherstatus .plusoneselect').click(transmitSelection); 

            if (automode != 'autoload')
            {
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


    // code shared with reload code so we can use same system to suppress edited messages from codemirror
    function receiveChainpatchFromQueue(reloadedcode)
    {
        // handle bail out conditions
        if (reloadedcode == null)
        {
            if (nextchainpatchnumbertoreceive == -1)
                receivechainpatchqueue.length = 0; 
            var chainpatch = (receivechainpatchqueue.length != 0 ? receivechainpatchqueue.shift() : null); 
            if ((chainpatch != null) && ((chainpatch.chainpatchnumber != nextchainpatchnumbertoreceive) || (chainpatch.rev != lastRev)))
            {
                    // this will be handled some other time (for someone joining in as we are already in full flow)
                writeToChat('<i>'+chainpatch.chatname+' typed something but this window is not synchronized to receive it</i>'); 
                nextchainpatchnumbertoreceive = -1; 
                receivechainpatchqueue.length = 0; 
                chainpatch = null; 
            }
            if (chainpatch == null)
            {
                receivechainpatchcall = null; 
                $('li#idtopcodetab a').removeClass("othertypingalert").css("background-color", "#ffffff");
                return; 
            }
        }

            // the callback into the onchange function appears to happen in same thread without a timeout 
            // so we have to suppress the re-edits with this flag here.
            // some callbacks into onchange are deferred, so it is unpredictable and hard to detect 
            // (unless we were going to watch the patches being created and compare them to the one we committed to tell the difference between typing)
            // so we're going to use a few second delay to suppress messages going through and highlight with an chatalert colour on the tab
            // which will help see stuff when it appears to go wrong.  
        $('li#idtopcodetab a').addClass("othertypingalert").css("background-color", "#ffff87"); // backgroundcolour setting by class doesn't work
        if ((reloadedcode != null) && (receivechainpatchcall != null))
            window.clearTimeout(receivechainpatchcall); 
        receivechainpatchcall = "doingothertyping"; 
        if (reloadedcode == null)
        {
            var mismatchlines = recordOtherTyping(chainpatch, codeeditor);  

            // log the mismatch cases, which look like they are coming from the unreliability of 
            // CM_newLines where the lines are changed prior to the next undo stack commit
            // therefore the set of patches are actually inconsistent, usually between immediate successor patches, 
            // so we have the previous patch and the ptime difference to verify this
            if (mismatchlines.length != 0)
            {
                writeToChat("Mismatches "+$.toJSON(mismatchlines)); 
                writeToChat("chainpatch " + $.toJSON(chainpatch)); 
                if (lastreceivedchainpatch)
                    writeToChat("prevchainpatch " + $.toJSON(lastreceivedchainpatch)); 
            }
            nextchainpatchnumbertoreceive++;  // next value expected
            chainpatchnumber = nextchainpatchnumbertoreceive; 
            lastreceivedchainpatch = chainpatch; 
        }
        else
            codeeditor.setCode(reloadedcode); 
        receivechainpatchcall = window.setTimeout(function() { receiveChainpatchFromQueue(null); }, (((reloadedcode == null) && (receivechainpatchqueue.length != 0)) ? 10 : 5000));  
    }

              

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
        writeToConsole('Starting run ... ' + (isstaff ? " [on "+lxc+"]" : "")); 
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
            writeToConsole("internalwarning: "+contentextra); 

        //change title
        document.title = document.title.replace('*', '');
    
        //hide annimation
        $('#running_annimation').hide();
        runID = ''; 
        uml = ''; 

        // suppress any more activity to the preview frame
        if (draftpreviewwindow != undefined) 
        {
            if (draftpreviewwindow.document)
                draftpreviewwindow.document.close(); 
            draftpreviewwindow = undefined; 
        }

    }


    function makeSelection(selrange)
    {
        if (codemirroriframe)
        {
            var linehandlestart = codeeditor.nthLine(selrange.startline + 1); 
            var linehandleend = (selrange.endline == selrange.startline ? linehandlestart : codeeditor.nthLine(selrange.endline + 1)); 
            codeeditor.selectLines(linehandlestart, selrange.startoffset, linehandleend, selrange.endoffset); 
        }
    }

    function transmitSelection()
    {
        var curposstart = codeeditor.cursorPosition(true); 

        var curposend = codeeditor.cursorPosition(false); 
        var selrange = { startline:codeeditor.lineNumber(curposstart.line)-1, startoffset:curposstart.character, 
                         endline:codeeditor.lineNumber(curposend.line)-1, endoffset:curposend.character }; 
        sendjson({"command":'giveselrange', "selrange":selrange, "username":username}); 
    }

    function reloadScraper()
    {
        $('.editor_controls #btnCommitPopup').val('Loading...').addClass('darkness');
        var oldcode = (codeeditor ? codeeditor.getCode() : $("#id_code").val()); 
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
        $('.editor_controls #btnForkNow').val('fork' + (wiki_type == 'scraper' ? ' scraper' : '')); 

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

        if (codemirroriframe)
        {
            var historysize = codeeditor.historySize(); 
            atsavedundo = historysize.undo + historysize.lostundo; 
        }
        else
            atsavedundo = 1; 

        var currentcode = (codeeditor ? codeeditor.getCode() : $("#id_code").val()); 
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
            alert('Sorry, something went wrong with the save, please try copying your code and then reloading the page. Technical details: ' + textStatus);
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






    //resize code editor
   function resizeCodeEditor()
   {
       if (codemirroriframe)
       {
            //resize the iFrame inside the editor wrapping div
            codemirroriframe.height = (($("#codeeditordiv").height() + codemirroriframeheightdiff) + 'px');
            codemirroriframe.width = (($("#codeeditordiv").width() + codemirroriframewidthdiff) + 'px');
    
            //resize the output area so the console scrolls correclty
            iWindowHeight = $(window).height();
            iEditorHeight = $("#codeeditordiv").height();
            iControlsHeight = $('.editor_controls').height();
            iCodeEditorTop = parseInt($("#codeeditordiv").position().top);
            iOutputEditorTabs = $('#outputeditordiv .tabs').height();
            iOutputEditorDiv = iWindowHeight - (iEditorHeight + iControlsHeight + iCodeEditorTop) - 30; 
            $("#outputeditordiv").height(iOutputEditorDiv + 'px');   
            //$("#outputeditordiv .info").height($("#outputeditordiv").height() - parseInt($("#outputeditordiv .info").position().top) + 'px');
            $("#outputeditordiv .info").height((iOutputEditorDiv - iOutputEditorTabs) + 'px');
            //iOutputEditorTabs
        }
        else
        {
            $("#id_code").css("height", ($("#codeeditordiv").height()-10) + 'px'); 
            $("#id_code").css("width", ($("#codeeditordiv").width()-8) + 'px'); 
        }
    }


    //click bar to resize
    function resizeControls(sDirection) 
    {
        if (sDirection == 'first')
            previouscodeeditorheight = $(window).height() * 3/5; 
        else if (sDirection != 'up' && sDirection != 'down')
            sDirection = 'none';

        //work out which way to go
        var maxheight = $("#codeeditordiv").height() + $(window).height() - ($("#outputeditordiv").position().top + 5); 
        if (($("#codeeditordiv").height() + 5 <= maxheight) && (sDirection == 'none' || sDirection == 'down')) 
        {
            previouscodeeditorheight = $("#codeeditordiv").height();
            $("#codeeditordiv").animate({ height: maxheight }, 100, "swing", resizeCodeEditor); 
        } 
        else if ((sDirection == 'first') || (sDirection == 'none') || ((sDirection == 'up') && ($("#codeeditordiv").height() + 5 >= maxheight)))
            $("#codeeditordiv").animate({ height: Math.min(previouscodeeditorheight, maxheight - 5) }, 100, "swing", resizeCodeEditor); 
    }

    function onWindowResize() {
        var maxheight = $("#codeeditordiv").height() + $(window).height() - $("#outputeditordiv").position().top; 
        if (maxheight < $("#codeeditordiv").height()){
            $("#codeeditordiv").animate({ height: maxheight }, 100, "swing", resizeCodeEditor);
        }
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
