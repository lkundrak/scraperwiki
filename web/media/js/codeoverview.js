


function setupScraperOverview(short_name)
{
    $('.data_tab').click(function() 
    {
        // do nothing if already selected
        if ($(this).hasClass('selected')) 
            return;
        
        // make tab selected
        $('.data_tab').removeClass('selected'); // all
        $(this).addClass('selected');
    
        // show and hide
        $('.data_content').hide(); // all
        var tab_content_name = $(this).attr('id').replace('data_tab', 'data_content');
        var tablename = $(this).find("span.tablename").text(); 
        $('#' + tab_content_name).show();
    
        $("#downloadcsvtable").show(); 
        $("#downloadcsvtable").attr("href", $('#id_api_base').val() + "datastore/sqlite?format=csv&name=" + short_name 
                                                + "&query=select+*+from+`"+encodeURI(tablename)+"`"+"&apikey="+$('#id_apikey').val()); 
    }); 

    $('.sqlite_view_schema').click( function() 
    {
        $('#sqlite_schema').toggle(500); 
        $('.sqlite_view_schema').toggle(); 
    });
    
    
    $("#popupinteractivesqlite").click(function() 
    {
        var url = "{{settings.VIEW_URL}}{% url rpcexecute 'quickcheck_datastore' %}?src="+decodeURIComponent(short_name); 
        $.modal('<iframe width="100%" height="100%" src='+url+'></iframe>', 
        {
            overlayClose: true,
            containerCss: { borderColor:"#0ff", height:"80%", padding:0, width:"90%" }, 
            overlayCss: { cursor:"auto" }, 
            onShow: function() 
            {
                $('.simplemodal-wrap').css("overflow", "hidden"); 
                $('.simplemodal-wrap iframe').width($('.simplemodal-wrap').width()-2); 
                $('.simplemodal-wrap iframe').height($('.simplemodal-wrap').height()-2); 
            }
        }); 
    }); 

    $("#downloadcsvtable").hide(); 
    $('.sqlite_view_schema:last').hide(); 
    $('#sqlite_schema').hide(); 
    $('#data_tab_1').click();

     //scheduler
     //
     if ($('#spnRunInterval').length > 0) {
         $('#spnRunInterval').editable('admin/', {
                  indicator : 'Saving...',
                  tooltip   : 'Click to edit...',
                  cancel    : 'Cancel',
                  submit    : 'Save',
                  onblur: 'ignore',
                  data   : $('#hidScheduleOptions').val().replace('PLACEHOLDER', $('#spnRunIntervalInner').attr('rawInterval')),
                  type   : 'select',
                  event: 'dblclick',
                  placeholder: '',
                  submitdata : {short_name: short_name}
              });
      }

      $('#aEditSchedule').click(
           function(){
                sCurrent = $('#spnRunIntervalInner').html().trim();               
                $('#spnRunInterval').dblclick();
                $('#spnRunInterval select').val(sCurrent);
                return false;
           }
       );
}


    // load in the whole new page and snip out the piece (this is too easy)
function reload_scraper_contributors(redirect)
{
    $('#contributors_loading').show();
    $.ajax(
		{
			url:document.location,
			cache: false,
			type: 'GET', 
			success:function(htmlpage){
		        $("#scraper_contributors").html($(htmlpage).find("#scraper_contributors").html())
		        $("#header_inner").html($(htmlpage).find("#header_inner").html())
		        setupChangeEditorStatus(); 
		        $('#contributors_loading').hide();
			},
			error: function(jq, textStatus, errorThrown){
				if ( redirect ) {
					window.location.href = redirect;
					return false;
				}

				alert( textStatus );
				alert( errorThrown );
			}
		});

    // original action: 
    //    document.location.reload(true);
}


function reload_scraper_attachables(short_name, redirect)
{
    $('#attachables_loading').show();
    $.ajax(
        {
            url:document.location,
            cache: false,
            type: 'GET', 
            success:function(htmlpage){
                $("#scraper_attachables").html($(htmlpage).find("#scraper_attachables").html())
                $("#header_inner").html($(htmlpage).find("#header_inner").html())
                setupChangeAttachables(short_name); 
                $('#attachables_loading').hide();
            },
            error: function(jq, textStatus, errorThrown){
                if ( redirect ) {
                    window.location.href = redirect;
                    return false;
                }

                alert( textStatus );
                alert( errorThrown );
            }
        });

    // original action: 
    //    document.location.reload(true);
}

function setupCodeOverview(short_name)
{
    //about
    $('#divAboutScraper').editable('admin/', {
             indicator : 'Saving...',
             tooltip   : 'Click to edit...',
             cancel    : 'Cancel',
             submit    : 'Save',
             type      : 'textarea',
             loadurl: 'raw_about_markup/',
             onblur: 'ignore',
             event: 'dblclick',
             submitdata : {short_name: short_name},
             placeholder: ''       
         });

    $('#aEditAboutScraper,#aEditAboutScraperNew').click(
        function(){
             $('#divAboutScraper').dblclick();
             var oHint = $('<div id="divMarkupHint" class="content_footer"><p><strong>You can use Textile markup to style the description:</strong></p><ul><li>*bold* / _italic_ / @code@</li><li>* Bulleted list item / # Numbered list item</li><li>"A link":http://www.data.gov.uk</li><li>h1. Big header / h2. Normal header</li></ul></div>');
             if ($('#divAboutScraper #divMarkupHint').length == 0)  // quick hack to avoid multiple copies of this till it's done properly with a hidden div
                 $('#divAboutScraper form').append(oHint);
             return false;
        }
    );

    //title
    $('#hCodeTitle').editable('admin/', {
			cssclass : 'editable',
			width : $('#hCodeTitle').width() + 30,
            indicator : 'Saving...',
            tooltip   : 'Double click to edit title',
            cancel    : 'Cancel',
            submit    : 'Save',
			before : function(value, settings){
				$('#aEditTitle').hide();
			},
			callback : function(value, settings){
				$('#aEditTitle').show();
			},
			onreset : function(value, settings){
				$('#aEditTitle').show();
			},
            onblur: 'ignore',
            event: 'dblclick',
            placeholder: '',             
            submitdata : {short_name: short_name}
         });
         
    $('#aEditTitle').click(
        function(){
             $('#hCodeTitle').dblclick();
             return false;
        }
    );

    // this is complex because editable div is not what you see (it's a comma separated field)
    $('#divEditTags').editable($("#adminsettagurl").val(), 
    {
        indicator : 'Saving...', tooltip:'Click to edit...', cancel:'Cancel', submit:'Save tags',
        onblur: 'ignore', event:'dblclick', placeholder:'',
        onedit: function() 
        {
            var tags = [ ]; 
            $("#divScraperTags ul.tags li a").each(function(i, el) { tags.push($(el).text()); }); 
            $(this).text(tags.join(", ")); 
        },
        onreset: function() { $('#divEditTagsControls').hide(); },
        callback: function(lis) 
        {
            $('#divScraperTags ul.tags').html(lis); 
            $('#divEditTagsControls').hide(); 
            $('#addtagmessage').css("display", ($("#divScraperTags ul.tags li a").length == 0 ? "block" : "none")); 
        }
    }); 
    $('#aEditTags,#aEditTagsFromEmpty').click(function()
    {
        $('#divEditTags').dblclick();
        $('#divEditTagsControls').show();
        return false;
    });
    $('#divEditTagsControls').hide();
    $('#addtagmessage').css("display", ($("#divScraperTags ul.tags li a").length == 0 ? "block" : "none")); 
}


function changeRoles(sdata, redirect_to_on_fail) {
    $.ajax(
		{
			url:$("#admincontroleditors").val(), 
			type: 'GET', 
			data:sdata, 
			success:function(result)
        	{
            	if (result.substring(0, 6) == "Failed")
                	$('#contributorserror').text(result).show(300);
            	else 
                	reload_scraper_contributors(redirect_to_on_fail); 
        	},
        	error:function(jq, textStatus, errorThrown)
        	{
            	$('#contributorserror').text("Connection failed: " + textStatus + " " + errorThrown).show(300);
        	}
		}
	); 	
}

function setupChangeEditorStatus()
{
    // changing editor status
    $('#addneweditor a').live('click', function()
    {
        $('#addneweditor a').hide()
        $('#addneweditor span').show(); 
        $('#contributorserror').hide();
    }); 
    $('#addneweditor input.cancelbutton').live('click', function()
    {
        $('#addneweditor span').hide(); 
        $('#addneweditor a').show()
        $('#contributorserror').hide();
    }); 
    $('#addneweditor input.addbutton').live('click', function()
    {
        $('#contributorserror').hide();
        var thisli = $(this).parents("li:first"); 
        var sdata = { roleuser:$('#addneweditor input:text').val(), newrole:'editor' }; 
        $.ajax({url:$("#admincontroleditors").val(), type: 'GET', data:sdata, success:function(result)
	        {
           
	            if (result.substring(0, 6) == "Failed") {
	                $('#contributorserror').text(result).show(300);
	            } else {
	                reload_scraper_contributors(); 
	                $('#addneweditor span').hide(); 
	                $('#addneweditor a').show(); 
	            }
	        },
	        error:function(jq, textStatus, errorThrown)
	        {
	            $('#contributorserror').text("Connection failed: " + textStatus + " " + errorThrown).show(300);
	        }
        }); 
    }); 

    $('.detachbutton').live('click', function() 
    {
        $('#contributorserror').hide();
        var sdata = { roleuser:$(this).parents("li:first").find("span").text(), newrole:'' }; 
		changeRoles( sdata, '/dashboard/' );
    }); 

    $('.demotebutton').live('click', function() 
    {
        $('#contributorserror').hide();
        var sdata = { roleuser:$(this).parents("li:first").find("span").text(), newrole:'' }; 
		changeRoles( sdata );
    }); 
    $('.promotebutton').live('click', function() 
    {
        $('#contributorserror').hide();
        var sdata = { roleuser:$(this).parents("li:first").find("span").text(), newrole:'editor' }; 
		changeRoles( sdata );
    }); 


    if ($('#addneweditor input:text').length)
        $('#addneweditor input:text').autocomplete(
    {
        minLength: 2,
        open: function() {  $( this ).removeClass( "ui-corner-all" ).addClass( "ui-corner-top" ); }, 
        close: function() {  $( this ).removeClass( "ui-corner-top" ).addClass( "ui-corner-all" ); }, 
        //select: function(event, ui) { rewriteapiurl(); },
        source: function(request, response) 
        {
            var nolist = [ ]; 
            $("ul#contributorslist li span").each(function(i, el) { nolist.push($(el).text()); }); 
            $.ajax(
            {
                url: $('#id_api_base').val()+"scraper/usersearch",
                dataType: "jsonp",
                data: { format:"jsondict", maxrows:12, searchquery:request.term, nolist:nolist.join(" ") },
                success: function(data) 
                {
                    response($.map(data, function(item) { return  { label: item.username, desc: item.profilename, value: item.username }})); 
                }
            })
        },
        focus: function(event, ui)  { $( "#addneweditor input:text" ).val(ui.item.label);  return false; }
    })
    .data( "autocomplete" )._renderItem = function(ul, item) 
    {
        return $( "<li></li>" )
        .data( "item.autocomplete", item )
        .append( '<a><strong>' + item.desc + '</strong><br/><span>' + item.label + '</span></a>' )
        .appendTo(ul);
    };


    // Changing between public / protected(visible) / private

    $('#show_privacy_choices').live('click', function(){
        $('#privacy_status form').show();
        $('#privacy_status>h4, #privacy_status>p').hide();
    });

    $('#hide_privacy_choices').live('click', function() 
    {
        $('#privacy_status form').hide();
        $('#privacy_status>h4, #privacy_status>p').show();
    }); 

    $('#saveprivacy').live('click', function() 
    {
        var radio_value = $('input[name=privacy_status]:checked').val(); 
        var sdata = { value:radio_value }; 
        $.ajax({url:$("#adminprivacystatusurl").val(), type: 'POST', data:sdata, success:function(result)
        {
            if (result.substring(0, 6) == "Failed")
                alert(result); 
            else 
                reload_scraper_contributors(); 
        }}); 
    }).hide();

	$('#privacy_status :radio').change(function(){
		$('#saveprivacy').trigger('click');
	});
}
    
function setupChangeAttachables(short_name)
{
    // adding and removing attachables
    $('#addnewattachable a').click(function()
    {
        $('#addnewattachable a').hide()
        $('#addnewattachable span').show(); 
        $('attachableserror').hide();
    }); 
    $('#addnewattachable input.cancelbutton').click(function()
    {
        $('#addnewattachable span').hide(); 
        $('#addnewattachable a').show()
        $('attachableserror').hide();
    }); 
    $('#addnewattachable input.addbutton').click(function()
    {
        $('#attachablesserror').hide();
        var sdata = { attachable:$('#addnewattachable input:text').val(), action:'add' }; 
        $.ajax({url:$("#admincontrolattachables").val(), type: 'POST', data:sdata, success:function(result)
        {
           
            if (result.substring(0, 6) == "Failed") {
                $('#attachableserror').text(result).show(300);
            } else {
                reload_scraper_attachables(); 
                $('#addnewattachable span').hide(); 
                $('#addnewattachable a').show(); 
            }
        },
        error:function(jq, textStatus, errorThrown)
        {
            $('#attachableserror').text("Connection failed: " + textStatus + " " + errorThrown).show(300); 
        }}); 
    }); 

    $('#databaseattachablelist .removebutton').click(function() 
    {
        $('#attachableserror').hide();
        var sdata = { attachable:$(this).parents("li:first").find("span").text(), action:'remove' }; 
        $.ajax({url:$("#admincontrolattachables").val(), type: 'POST', data:sdata, success:function(result)
        {
           
            if (result.substring(0, 6) == "Failed") {
                $('#attachableserror').text(result).show(300);
            } else {
                reload_scraper_attachables(); 
                $('#addnewattachable span').hide(); 
                $('#addnewattachable a').show(); 
            }
        },
        error:function(jq, textStatus, errorThrown)
        {
            $('#attachableserror').text("Connection failed: " + textStatus + " " + errorThrown).show(300); 
        }}); 
    }); 
    
    if ($('#addnewattachable input:text').length)
        $('#addnewattachable input:text').autocomplete(
    {
        minLength: 2,
        open: function() {  $( this ).removeClass( "ui-corner-all" ).addClass( "ui-corner-top" ); }, 
        close: function() {  $( this ).removeClass( "ui-corner-top" ).addClass( "ui-corner-all" ); }, 
        //select: function(event, ui) { rewriteapiurl(); },
        source: function(request, response) 
        {
            var nolist = [ short_name ]; 
            $("ul#databaseattachablelist li span").each(function(i, el) { nolist.push($(el).text()); }); 
            $.ajax(
            {
                url: $('#id_api_base').val()+"scraper/search",
                dataType: "jsonp",
                data: { format:"jsondict", maxrows: 12, searchquery: request.term, quietfields:'description', nolist:nolist.join(" ") },
                success: function(data) 
                {
                    response($.map(data, function(item) { return  { label: item.short_name, desc: item.title, value: item.short_name }})); 
                }
            })
        },
        focus: function(event, ui)  { $( "#detail #id_name" ).val(ui.item.label);  return false; }
    }) 
    .data( "autocomplete" )._renderItem = function(ul, item) 
    {
        return $( "<li></li>" )
        .data( "item.autocomplete", item )
        .append( '<a><strong>' + item.desc + '</strong><br/><span>' + item.label + '</span></a>' )
        .appendTo(ul);
    };
}

function move_to_vault(){
	$('#move_to_vault').bind('change', function(){
		if($(this).val() == ''){
			$(this).next().attr('disabled','disabled');
		} else {
			$(this).next().attr('disabled','');
		}
		console.log($(this).val());
	}).next().attr('disabled','disabled').bind('click', function(e){
		e.preventDefault();
		if($(this).is(':disabled')){
			// do nothing
			console.log('naughty');
		} else {
			$(this).val('Moving\u2026').attr('disabled','disabled').prev().attr('disabled','disabled');
			$.getJSON($(this).prev().val(), function(data) {
				console.log(data);
				if(data.status == 'ok'){
					$('#scraper_contributors').load(location.href + ' #scraper_contributors>*', function(){
						$('#current_vault_link').animate({backgroundColor:'#ffff99'}, 100, function(){
							$(this).animate({backgroundColor:'#F4F8FB'}, 100, function(){
								$(this).animate({backgroundColor:'#ffff99'}, 100, function(){
									$(this).animate({backgroundColor:'#F4F8FB'}, 100, function(){
										$(this).animate({backgroundColor:'#ffff99'}, 100, function(){
											$(this).animate({backgroundColor:'#F4F8FB'}, 1000);
										});
									});
								});
							});
						});
						move_to_vault();
					});
				} else {
					$(this).parent().after('<p class="error">Ooops! ' + data.error + '</p>');
				}
			});
		}
	});
}

$(function(){
	move_to_vault();
});