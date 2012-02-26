
// Self contained functions that produce computations based on the CodeMirror1 codeeditor
function CM_cleanText(text)  { return text.replace(/\u00a0/g, " ").replace(/\u200b/g, ""); }
function CM_isBR(node)  { var nn = node.nodeName; return nn == "BR" || nn == "br"; }
function CM_nodeText(node)  { return node.textContent || node.innerText || node.nodeValue || ""; }
function CM_lineNumber(node, codeeditor)
{
    if (node == null)
        return 1; 
    if (node.parentNode != codeeditor.win.document.body)
        return -1; 
    var num = 1;
    while (node)
    {
        num++; 
        node = node.previousSibling; 
        while (node && !CM_isBR(node))
            node = node.previousSibling; 
    }
    return num;
}

function CM_newLines(from, to, codeeditor) 
{
    var lines = [ ];
    var text = [ ];
    for (var cur = (from ? from.nextSibling : codeeditor.editor.container.firstChild); cur != to; cur = cur.nextSibling)
    {
        if (!cur)  // a notable failure case, possibly when the lines we are copying have themselves been trimmed out
            return null; 
        
        if (CM_isBR(cur))
        {
            lines.push(CM_cleanText(text.join(""))); 
            text = [ ];
        }
        else
            text.push(CM_nodeText(cur)); 
    }
    lines.push(CM_cleanText(text.join(""))); 
    return lines; 
}


function MakeChainPatches(llchainpatches, codeeditor, lastundo)
{
    // send any edits up the line (first to the chat page to show we can decode it)
    var historystack = codeeditor.editor.history.history; 
    var lostundo = codeeditor.editor.history.lostundo; 

    var redohistorystack = codeeditor.editor.history.redoHistory; 
    var rdhL = redohistorystack.length - 1; 
    var ptime = (new Date()).getTime(); 
    while (lastundo != historystack.length + lostundo)
    {
        var chains; 
        var historypos; 
        if (lastundo < historystack.length + lostundo)
        {
            chains = historystack[lastundo - lostundo]; 
            historypos = lastundo - lostundo; 
            lastundo++; 
        }
        else if (rdhL >= 0)
        {
            chains = redohistorystack[rdhL]; 
            historypos = -1 - rdhL; 
            rdhL--; 
            lastundo--; 
        }
        else
            break; 

        var lchainpatches = [ ]; 
        for (var i = 0; i < chains.length; i++)
        {
            var chain = chains[i]; 
            var deletions = [ ]; 
            var insertlinenumber = CM_lineNumber(chain[0].from, codeeditor);
            for (var k = 0; k < chain.length; k++)
                deletions.push(chain[k].text);  // these values I think can be changed retrospectively to collapse an undo value

            var lines = CM_newLines(chain[0].from, chain[chain.length - 1].to, codeeditor); 
            var insertions; 
            if (lines != null)
            {
                insertions = [ ]; 
                for (var j = 0; j < lines.length; j++)
                    insertions.push(lines[j]); 
            }
            else
                insertions = null; 
            
            // duplicates that can happen with the final line (deletions[-1]==insertions[-1]) which we could trim out, but best to leave in 
            // in case it does overwrite the last change that was sent on that line but mismatched by unreliability of CM_newLines

            var chainpatch = { command:'typing', insertlinenumber:insertlinenumber, deletions:deletions, insertions:insertions, 
                               historypos:historypos, ptime:ptime }
            lchainpatches.push(chainpatch); 
        }
        
            // arrange for the chainpatches list (which is reversed) to add the upper ones first, because the line numbering 
            // is detected against the final version after this chainpatch group has been done, so upper ones have occurred
        lchainpatches.sort(function(a,b) {return b["insertlinenumber"] - a["insertlinenumber"]});  
        while (lchainpatches.length != 0)
            llchainpatches.push(lchainpatches.pop()); 
    }
    return historystack.length + lostundo; 
}



// incoming patches
function recordOtherTyping(chainpatch, codeeditor)
{
    var mismatchlines = [ ]; 
    var linehandle = codeeditor.nthLine(chainpatch["insertlinenumber"]); 

    // change within a single line
    if ((chainpatch["deletions"].length == 1) && (chainpatch["insertions"].length == 1))
    {
        var linecontent = codeeditor.lineContent(linehandle); 
        var deletestr = chainpatch["deletions"][0]; 
        var insertstr = chainpatch["insertions"][0]; 
        if (linecontent != deletestr)
            mismatchlines.push({linenumber:chainpatch["insertlinenumber"], linecontent:linecontent, deletestr:deletestr}); 

        codeeditor.setLineContent(linehandle, insertstr); 
        var ifront = 0; 
        while ((ifront < deletestr.length) && (ifront < insertstr.length) && (deletestr.charAt(ifront) == insertstr.charAt(ifront)))
            ifront++; 
        if (ifront < insertstr.length)
        {
            var iback = insertstr.length - 1; 
            while ((iback > ifront) && (iback - insertstr.length + deletestr.length > 0) && (deletestr.charAt(iback - insertstr.length + deletestr.length) == insertstr.charAt(iback)))
                iback--; 
            codeeditor.selectLines(linehandle, ifront, linehandle, iback+1); 
        }

        else 
            codeeditor.selectLines(linehandle, ifront, codeeditor.nextLine(linehandle), 0); 
    }

    // change across multiple lines
    else
    {
        var insertions = chainpatch["insertions"]; 
        var deletions = chainpatch["deletions"]; 

        // apply the patch
        var nlinehandle = linehandle; 
        var il = 0; 
        while ((il < deletions.length - 1) && (il < insertions.length))
        {
            var linecontent = codeeditor.lineContent(nlinehandle); 
            if (linecontent != deletions[il])
                mismatchlines.push({linenumber:chainpatch["insertlinenumber"]+il, linecontent:linecontent, deletestr:deletions[il]}); 
            codeeditor.setLineContent(nlinehandle, insertions[il]); 
            nlinehandle = codeeditor.nextLine(nlinehandle); 
            il++; 
        }
        if (il == insertions.length)
        {
            while (il < deletions.length)
            {
                var linecontent = codeeditor.lineContent(nlinehandle); 
                if (linecontent != deletions[il])
                    mismatchlines.push({linenumber:chainpatch["insertlinenumber"]+il, linecontent:linecontent, deletestr:deletions[il]}); 
                codeeditor.removeLine(nlinehandle); 
                il++; 
            }
            nlinehandle = codeeditor.prevLine(nlinehandle); 
        }
        else
        {
            var linecontent = codeeditor.lineContent(nlinehandle); 
            if (linecontent != deletions[il])
                mismatchlines.push({linenumber:chainpatch["insertlinenumber"]+il, linecontent:linecontent, deletestr:deletions[il]}); 
            codeeditor.setLineContent(nlinehandle, insertions.slice(il).join("\n"));  // all remaining lines replace the last line
            while (il++ < insertions.length - 1)
                nlinehandle = codeeditor.nextLine(nlinehandle); 
        }
        
        // find the selection range
        var ifront = 0; 
        var iback; 
        if (insertions.length != 0)
        {
            while ((ifront < insertions[0].length) && (ifront < deletions[0].length) && (insertions[0].charAt(ifront) == deletions[0].charAt(ifront)))
                ifront++; 
            
            // sometimes the last line is duplicated, so knock it out
            var finsertstr = insertions[insertions.length-1]; 
            var fdeletestr = deletions[deletions.length-1]; 
            if ((finsertstr == fdeletestr) && (insertions.length >= 2) && (deletions.length >= 2))
            {
                nlinehandle = codeeditor.prevLine(nlinehandle); 
                finsertstr = insertions[insertions.length-2]; 
                fdeletestr = deletions[deletions.length-2]; 
            }
            
            iback = finsertstr.length - 1; 
            while ((iback > 0) && (iback - finsertstr.length + fdeletestr.length > 0) && (fdeletestr.charAt(iback - finsertstr.length + fdeletestr.length) == finsertstr.charAt(iback)))
                iback--; 
            if (iback >= finsertstr.length - 1)
            {
                nlinehandle = codeeditor.nextLine(nlinehandle); 
                iback = 0; 
            }
        }
        else 
        {
            nlinehandle = codeeditor.nextLine(nlinehandle); 
            iback = 0; 
        }
        
        codeeditor.selectLines(linehandle, ifront, nlinehandle, iback); 
    }
    return mismatchlines; 
}
