
function highlightCode(code, Parser, previewerdiv)
{
    var lineNo = 1; 
    var output = previewerdiv.find('.outputlines'); 
    var numbers = previewerdiv.find('.linenumbers'); 
 
    function addLine(line) 
    {
        numbers.append(String(lineNo++)+'<br>'); 
        for (var i = 0; i < line.length; i++) 
            output.append(line[i]);
        output.append('<br>')
    }
    highlightText(code, addLine, Parser); 
}

function highlightOtherCode(code, othercode, matcheropcodes, Parser, previewerdiv)
{
    var output = previewerdiv.find('.outputlines'); 
    var numbers = previewerdiv.find('.linenumbers'); 
    var othernumbers = previewerdiv.find('.otherlinenumbers'); 
    output.text(""); 
    numbers.text(""); 
    othernumbers.text(""); 

    // syntax highlight the two versions of the code
    var codelines = [ ]
    var othercodelines = [ ]
    highlightText(code, function(line) { codelines.push(line) }, Parser); 
    highlightText(othercode, function(line) { othercodelines.push(line) }, Parser); 

    var flinepadding = 2; 
    var fequallines = 0; 
    for (var k = 0; k < matcheropcodes.length; k++)
    {
        var mc = matcheropcodes[k];  // set from get_opcodes from http://docs.python.org/library/difflib.html
        var tag = mc[0]; i1 = mc[1]; i2 = mc[2]; j1 = mc[3]; j2 = mc[4]; 
        if (tag == "equal")
        {
            var li1 = (i1 == 0 ? 0 : i1 + flinepadding); 
            var li2 = (i2 == codelines.length ? i2 : i2 - flinepadding);
            var preveclass = ''; 
            for (var i = i1; i < i2; i++)
            {
                var eclass = 'equal'; 
                if ((i >= li1) && (i < li2))
                {
                    eclass =  'fequal'; 
                    fequallines++; 
                }

                // put in expander area
                if ((eclass != preveclass) && (eclass == 'fequal'))
                {
                    numbers.append('<span class="expander">.<br></span>'); 
                    othernumbers.append('<span class="expander">.<br></span>'); 
                    output.append('<span class="expander">...<br></span>');
                }
                preveclass = eclass; 

                // the <br> needs to be inside the span so it can hide with it
                numbers.append('<span class="'+eclass+'">'+String(i+1)+'<br></span>'); 
                othernumbers.append('<span class="'+eclass+'">'+String(i-i1+j1+1)+'<br></span>'); 

                var fline = $('<span class="'+eclass+'"/>'); 
                var line = codelines[i]; 
                for (var m = 0; m < line.length; m++) 
                    fline.append(line[m]);
                fline.append('<br>'); 
                output.append(fline);
            }
        }

        else
        {
            for (var i = i1; i < i2; i++)
            {
                numbers.append('<span class="insert">'+String(i+1)+'<br></span>'); 
                othernumbers.append('<span class="insert">+<br></span>'); 

                var fline = $('<span class="insert"/>')
                var line = codelines[i]; 
                for (var m = 0; m < line.length; m++) 
                    fline.append(line[m]);
                fline.append('<br>'); 
                output.append(fline);
            }

            for (var j = j1; j < j2; j++)
            {
                numbers.append('<span class="delete">-<br></span>'); 
                othernumbers.append('<span class="delete">'+String(j+1)+'<br></span>'); 

                var fline = $('<span class="delete"/>')
                var line = othercodelines[j]; 
                for (var m = 0; m < line.length; m++) 
                    fline.append(line[m]);
                fline.append('<br>'); 
                output.append(fline);
            }
        }
    }
    return fequallines; 
}

