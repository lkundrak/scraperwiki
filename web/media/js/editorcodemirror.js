// editor window dimensions
var codeeditor = null;
var codemirroriframe = null; // the actual iframe of codemirror that needs resizing (also signifies the frame has been built)
var codeeditorreadonly = false; 
var codemirroriframeheightdiff = 0; // the difference in pixels between the iframe and the div that is resized; usually 0 (check)
var codemirroriframewidthdiff = 0;  // the difference in pixels between the iframe and the div that is resized; usually 0 (check)
var previouscodeeditorheight = 0; //$("#codeeditordiv").height() * 3/5;    // saved for the double-clicking on the drag bar
var draftpreviewwindow = null;

var texteditor; // plain or codemirror

var parsers = Array();
var stylesheets = Array();
var indentUnits = Array();
var parserConfig = Array();
var parserName = Array();
var codemirroroptions = undefined; 

var codemirror_url; 
var scraperlanguage; 

var pageIsDirty = true;

var atsavedundo = 0; // recorded at start of save operation
var savedundo = 0; 
var lastundo = 0;


   // called from editortabs.js
function SelectEditorLine(iLine)
{
    codeeditor.selectLines(codeeditor.nthLine(iLine), 0, codeeditor.nthLine(iLine + 1), 0); 
}

function getcodefromeditor()
{
    return (codeeditor ? codeeditor.getCode() : $('#id_code').val()); 
}

function codeeditorundosize()
{
    if (codemirroriframe)
    {
        var historysize = codeeditor.historySize(); 
        return historysize.undo + historysize.lostundo; 
    }
    return 1; 
}

//setup code editor
function setupCodeEditor()
{
    // destroy any existing codemirror, so we can remake it with right readonly state
    if (codeeditor) 
    {
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

    if ($("#codemirrorversion").val().substr(0, 1) == "2")
    {
        writeToChat("Using Codemirror 2 !!!"); 
        codemirroroptions = {
            mode: {name: "python", version: 2, singleLineStringErrors: false},
            lineNumbers: true,
            indentUnit: 4,
            indentUnit: indentUnits[scraperlanguage],
            readOnly: expectedreadonly, 
            tabMode: "shift",
            lineWrapping: true, 
            matchBrackets: true
        };
        codeeditor = CodeMirror.fromTextArea(document.getElementById("id_code"), codemirroroptions); 
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


