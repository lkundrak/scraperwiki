/* GENERAL FUNCTIONS */

$.fn.digits = function(){ 
    return this.each(function(){ 
        $(this).text( $(this).text().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,") ); 
    })
}

$.extend({
    keys: function(obj){
		// Usage:
		// var obj = {a: 1, b: 2, c: 3, d: 4, kitty: 'cat'}
		// alert($.keys(obj));    ->   a,b,c,d,kitty
        var a = [];
        $.each(obj, function(k){ a.push(k) });
        return a;
    }
})

function pluralise(thing,number,plural){
	if(plural == null){ plural = thing + 's'; }
    return (number == 1 ? thing : plural);
}

function htmlEscape(str){
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function safeString(str){
    return str.replace(/[^a-zA-Z0-9]+/g, '_').replace(/(^_|_$)/g, '');
}




/* SETUP FUNCTIONS */

function setupCodeOverview(short_name){
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

    $('a.edit_description').live('click', function(e){
		e.preventDefault();
        $('#divAboutScraper').dblclick();
        var oHint = $('<div id="divMarkupHint" class="content_footer"><p><strong>You can use Textile markup to style the description:</strong></p><ul><li>*bold* / _italic_ / @code@</li><li>* Bulleted list item / # Numbered list item</li><li>"A link":http://www.data.gov.uk</li><li>h1. Big header / h2. Normal header</li></ul></div>');
        if ($('#divAboutScraper #divMarkupHint').length == 0){
            $('#divAboutScraper form').append(oHint);
		}
    });

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
         
    $('#aEditTitle').bind('click', function(){
		$('#hCodeTitle').dblclick();
		return false;
    });
}

function setupCollaborationUI(){
	$('#privacy_status, #contributors').hide();
	$('#collaboration ul.buttons a, #header .privacystatus').bind('click', function(e){
		e.preventDefault();
		var href = $(this).attr('href');
		if($(href).is(':visible')){
			$('#privacy_status, #contributors').hide();
			$('#collaboration ul.buttons a[href="' + href + '"]').removeClass('selected');
		} else {
			$(href).show().siblings('#privacy_status, #contributors').hide();
			$('#collaboration ul.buttons a[href="' + href + '"]').addClass('selected').parent().siblings().children('a').removeClass('selected');
		}
		$('#privacy_status form').hide();
		$('#contributors .new_user_li, #contributors .error').remove();
		$('#privacy_status>p, #privacy_status>h4, #show_privacy_choices, #contributors a.add_user').show();
	});
	
	$('#show_privacy_choices').bind('click', function(){
        $('#privacy_status form').show();
        $('#privacy_status>p, #privacy_status>h4, #show_privacy_choices').hide();
    });

    $('#saveprivacy').bind('click', function(){
		$('input[name=privacy_status]:checked').hide().after('<img src="/media/images/load2.gif" width="16" height="16">').parents('tr').find('input, select').attr('disabled', true);
		if($('#current_vault_id').length){
			$.getJSON('/vaults/' + $('#current_vault_id').val() + '/removescraper/' + $('#scrapershortname').val() + '/' + $('input[name=privacy_status]:checked').val(), function(data) {
				if(data.status == 'ok'){
					reloadCollaborationUI('#privacy_status');
				} else {
					alert('Scraper could not be removed from vault: ' + data.error);
				}
			});
		} else {
			var sdata = { value: $('input[name=privacy_status]:checked').val() }
			$.ajax({url:$("#adminprivacystatusurl").val(), type: 'POST', data:sdata, success:function(result){
				if (result.substring(0, 6) == "Failed"){
	                alert(result); 
	            } else {
					reloadCollaborationUI('#privacy_status');
				}
			}});
		}
    }).hide();

	//	Handle clicks on the "make this public" and "make this protected" paragraphs
	$('#privacy_public, #privacy_protected, #privacy_private').bind('change', function(){
		$('#saveprivacy').trigger('click');
	});
	
	$('#move_to_vault').bind('change', function(){
		if($(this).val() == ''){
			$(this).next().attr('disabled','disabled');
		} else {
			$(this).next().attr('disabled',false);
			$(this).parents('td').prev().find('input:radio').attr('checked', true)
		}
	}).next().attr('disabled','disabled').bind('click', function(e){
		e.preventDefault();
		if(!$(this).is(':disabled')){
			$(this).val('Moving\u2026').attr('disabled','disabled').prev().attr('disabled','disabled');
			$(this).parents('td').prev().find('input:radio').hide().after('<img src="/media/images/load2.gif" width="16" height="16">').parents('tr').find('input, select').attr('disabled', true);
			$.getJSON($(this).prev().val(), function(data) {
				if(data.status == 'ok'){
					reloadCollaborationUI('#privacy_status');
				} else {
					alert('Scraper could not be moved to vault: ' + data.error);
				}
			});
		}
	});
	
	$('#collaboration a.add_user').bind('click', function(){
		var input = $('<input>').attr('id','username').attr('type','text').attr('class','text').bind('keydown', function(e){
			// handle Enter/Return key as a click on the Add button
			if((e.keyCode || e.which) == 13){
				$(this).next('a').trigger('click');
			}
		}).autocomplete({
			minLength: 2,
			source: function( request, response ) {
				$.ajax({
					url: $('#id_api_base').val() + "scraper/usersearch",
					dataType: "jsonp",
					data: {
						format:"jsondict", 
						maxrows:10, 
						searchquery:request.term
					},
					success: function( data ) {
						response( $.map( data, function( item ) {
							return {
								label: item.profilename + ' (' + item.username + ')',
								value: item.username
							}
						}));
					}
				});
			},
			select: function( event, ui ) {
				//  submit the name
				//  $(this).next('a').trigger('click');
			}
		});
	
		var confirm = $('<a>').text('Add!').bind('click', function(){			
			var $u = $(this).prev();
			$u.parents('ul').children('.error').slideUp(150);
			$('#collaboration .buttons li:eq(1) a').prepend('<img src="/media/images/load2.gif" width="16" height="16">');
			var sdata = { roleuser: $u.val(), newrole:'editor' }; 
	        $.ajax({
				url:$("#admincontroleditors").val(), 
				type: 'GET', 
				data:sdata, 
				success:function(result){
		            if (result.substring(0, 6) == "Failed") {
						$('#collaboration .buttons li:eq(1) img').remove();
		                $u.autocomplete("close").parents('ul').append('<li class="error">' + result + '</li>');
		            } else {
						reloadCollaborationUI('#contributors');
		            }
		        },
		        error:function(jq, textStatus, errorThrown)
		        {
					$('#collaboration .buttons li:eq(1) img').remove();
		            $u.autocomplete("close").parents('ul').append('<li class="error">Connection failed: ' + textStatus + ' ' + errorThrown + '</li>');
		        }
	        });
		});
		
		var li = $('<li>').hide().addClass("new_user_li").append('<label for="username">Username:</label>').append(input).append(confirm);
		
		$(this).slideUp(250).prev().append(li).children(':last').slideDown(250).find('#username').focus();
	
	});
	
	$('.demotelink').bind('click', function(){
		$(this).parents('ul').children('.error').slideUp(150);
		$('#collaboration .buttons li:eq(1) a').prepend('<img src="/media/images/load2.gif" width="16" height="16">');
        var sdata = { roleuser:$(this).parents("li:first").find("span").text(), newrole:'' }; 
		$.ajax({
			url:$("#admincontroleditors").val(), 
			type: 'GET', 
			data:sdata, 
			success:function(result){
	            if (result.substring(0, 6) == "Failed") {
					$('#collaboration .buttons li:eq(1) img').remove();
	                $u.autocomplete("close").parents('ul').append('<li class="error">' + result + '</li>');
	            } else {
					reloadCollaborationUI('#contributors');
	            }
	        },
	        error:function(jq, textStatus, errorThrown)
	        {
				$('#collaboration .buttons li:eq(1) img').remove();
	            $u.autocomplete("close").parents('ul').append('<li class="error">Connection failed: ' + textStatus + ' ' + errorThrown + '</li>');
	        }
        });
    });
	
}

function reloadCollaborationUI(auto_enable_tab){
	$("#collaboration").load(document.location + ' #collaboration>*', function(response, status, xhr){
		if (status == "error") {
			alert('There was an error refreshing the collaboration UI: ' + xhr.status + " " + xhr.statusText);
		} else {
			$("#header p").load(document.location + ' #header p>*', function(response, status, xhr){
				if (status == "error") {
					alert('There was an error refreshing the collaboration UI: ' + xhr.status + " " + xhr.statusText);
				}
			});
			setupCollaborationUI();
			if(auto_enable_tab){
				$(auto_enable_tab).show();
				$('ul.buttons li').eq($(auto_enable_tab).index() - 1).children().addClass('selected');
			}
		}
	});	
}

function setupScheduleUI(){
	$('#edit_schedule input').bind('change', function(){
		if($(this).is(':disabled')){
			alert('That button is disabled');
		} else {
			$.getJSON($(this).val(), function(data) {
				if(data.status == 'ok'){
					reloadScheduleUI();
				} else {
					alert('New schedule could not be saved: ' + data.error);
				}
			});
		}
	});
	
	$('.edit_schedule').bind('click', function(e){
		e.preventDefault();
		if($('#edit_schedule').is(':hidden')){
			$('#edit_schedule').show().prev().hide();
			$(this).addClass('cancel').text('Cancel');
		} else {
			$('#edit_schedule').hide().prev().show();
			$(this).removeClass('cancel').text('Edit');
		}
	});
	
	$('.schedule a.run').bind('click', function(e){
		e.preventDefault();
		$.getJSON($(this).attr('href'), function(data) {
			if(data.status == 'ok'){
				reloadScheduleUI();
			} else {
				alert('Could not run scraper: ' + data.error);
			}
		});
	});
}

function reloadScheduleUI(){
	$("td.schedule").load(document.location + ' td.schedule>*', function(response, status, xhr){
		if (status == "error") {
			alert('There was an error refreshing the schedule UI: ' + xhr.status + " " + xhr.statusText);
		} else {
			setupScheduleUI();
		}
	});
}




/* ONREADY FUNCTIONS */

$(function(){
    // globals 
    api_url = $('#id_api_base').val();
	sqlite_url = api_url + 'datastore/sqlite?'
	if($('#id_apikey').val() != ''){
		apikey = $('#id_apikey').val();
		sqlite_url += 'apikey=' + apikey + '&';
	} else {
		apikey = null;
	}
    short_name = $('#scrapershortname').val();
    data_tables = [];

    setupDataPreviews();	
	setupCollaborationUI();
	setupScheduleUI();
	
	$('li.share .embed a').bind('click', function(e){
		e.preventDefault();
		$(this).parents('.share_popover').fadeOut(400).prev().removeClass('hover');
		$('html').unbind('click');
        $('#add_view_to_site').modal({
            overlayClose: true, 
            autoResize: true,
            overlayCss: { cursor:"auto" },
			onShow: function(dialog){
				$('#simplemodal-container').css('height', 'auto');
				$("pre", dialog.data).snippet('html', {style:"vim", clipboard: "/media/js/ZeroClipboard.swf"});
			},
			onOpen: function(dialog) {
				dialog.data.show();
				dialog.overlay.fadeIn(200);
				dialog.container.fadeIn(200);
			},
			onClose: function(dialog) {
				dialog.container.fadeOut(200);
				dialog.overlay.fadeOut(200, function(){
					$.modal.close();
				});
			}
        });
	});
	
	$('li.share a, li.admin a, li.download a').each(function(){
		$(this).bind('click', function(){
			var $a = $(this).addClass('hover');
			var $p = $a.siblings('div');
			if($p.is(':visible')){
				$p.fadeOut(400);
				$a.removeClass('hover');
				$('html').unbind('click');
			} else {
				$p.fadeIn(150, function(){
					$('html').bind('click', function(e){
						if( $(e.target).parents().index($a.parent()) == -1 ) {
							if( $(e.target).parents().index($p) == -1 ) {
								$p.filter(':visible').fadeOut(400);
								$a.removeClass('hover');
								$('html').unbind('click');
							}
						}
					});
				});
			}
		});
	});
	
	$('#delete_scraper, #empty_datastore').bind('click', function(e){
		e.preventDefault();
		$(this).next().children(':submit').trigger('click');
	});
	
	$('.full_history a').bind('click', function(e){
		e.preventDefault();
		if(!$(this).is('.disabled')){ 
			$button = $(this).text('Loading\u2026');
			$.ajax({
				url: $button.attr('href'),
				success: function(data) {
					$('.history>div').empty().html(data).each(function(){
						$(".cprev").hide();     // hide these ugly titles for now
					    hideallshowhistrun(); 

					    $(".history_edit").each(function(i, el) { previewchanges_hide($(el)) });

					    $(".history_edit .showchanges").click(function() { previewchanges_show($(this).parents(".history_edit")); }); 
					    $(".history_edit .hidechanges").click(function() { previewchanges_hide($(this).parents(".history_edit")); }); 

					    $(".history_edit .history_code_border .otherlinenumbers").click(previewchanges_showsidecode); 
					    $(".history_edit .history_code_border .linenumbers").click(previewchanges_showsidecode); 

					    $(".history_run_event .showrunevent").click(function() { previewrunevent_show($(this).parents(".history_run_event")); }); 
					    $(".history_run_event .hiderunevent").click(function() { previewrunevent_hide($(this).parents(".history_run_event")); }); 

					    // if they put # and the run_id in the URL, open up that one
					    if (window.location.hash) {
					        var hash_run_event = $(window.location.hash);
					        if (hash_run_event.length != 0) {
					            previewrunevent_show(hash_run_event);
					            $('html, body').animate({
                                     scrollTop: $(hash_run_event).offset().top
                                 }, 200);
                                 if($(hash_run_event).children('.history_ran_fail').length){
                                     $(hash_run_event).css('border','4px solid #B75253');
                                 } else {
                                     $(hash_run_event).css('border','4px solid #278D2F');
                                 }
                                 
					        }
					    }
					});
					$button.text('Showing full history').addClass('disabled');
				},
				error: function(request, status, error){
					$button.text('Unable to load full history').addClass('disabled').css('cursor','help').attr('title',request.responseText)
				}
			});
		}
	});
	
	
	function show_new_tag_box(){
		$('div.tags').show();
		$('.new_tag').hide().next().show().find('input').focus();
	}
	
	function hide_new_tag_box(){
		$('li.new_tag_box input').animate({width:1}, 200, function(){
			$(this).css('width','auto').val('').parent().hide().prev().show();
			if( ! $('div.tags li').not('.new_tag, .new_tag_box').length ){
				$('div.tags').fadeOut();
			}
		});
	}
	
	$('.new_tag a, div.network .titlebar .tag a').bind('click', function(e){
		e.preventDefault();
		show_new_tag_box();
	});
	
	$('li.new_tag_box input').bind('keyup', function(event){
		var key = event.keyCode ? event.keyCode : event.which ? event.which : event.charCode;
		if(key == 13){
			var new_tag = $(this).val();
			var new_tag_array = new_tag.split(',');
			var tags = [ ]; 
	        $("div.tags ul li").not('.new_tag, .new_tag_box').each(function(i, el) { 
				tags.push($(el).children('a:first').text());
			});
			tags.push(new_tag);
			$.ajax({
				type: 'POST',
				url: $("#adminsettagurl").val(),
				data: {value: tags.join(",") + ','},
				success: function(data){
					var new_html = '';
					$.each(new_tag_array, function(i, t){
						new_html += '<li class="editable"><a href="/tags/' + encodeURIComponent(trim(t)) + '">' + trim(t) + '</a><a class="remove" title="Remove this tag">&times;</a></li>';
					});
					$('li.new_tag_box input').val('').parent().prev().before(new_html);
				}, error: function(){
					alert('Sorry, your tag could not be added. Please try again later.');
				},
				dataType: 'html',
				cache: false
			});
		}
	}).bind('focus', function(){
		if(typeof(new_tag_hider) != 'undefined'){ clearTimeout(new_tag_hider); }
		$(this).parent().addClass('focus');
	}).bind('blur', function(){
		new_tag_hider = setTimeout(function(){hide_new_tag_box();}, 1000);
		$(this).parent().removeClass('focus');
	}).next('.hide').bind('click', function(){
		hide_new_tag_box();
	});
	
	$('div.tags a.remove').live('click', function(e){
		e.preventDefault();
		$old_tag = $(this).parent();
		var tags = [ ]; 
        $("div.tags ul li").not('.new_tag, .new_tag_box').not($old_tag).each(function(i, el) { 
			tags.push($(el).children('a:first').text());
		});
		
		$.ajax({
			type: 'POST',
			url: $("#adminsettagurl").val(),
			data: {value: tags.join(", ")},
			success: function(data){
				$old_tag.remove();
				if( ! $('div.tags li').not('.new_tag, .new_tag_box').length ){
					$('div.tags').fadeOut();
				}
			}, error: function(){
				alert('Sorry, your tag could not be removed. Please try again later.');
			},
			dataType: 'html',
			cache: false
		});
	});
});

function setupTabFolding(){
	
	function make_more_link(){
        $('ul.data_tabs .clear').before(
            $('<li id="more_tabs" title="Show more tabs" style="display:none"><span id="more_tabs_number">0</span> more &raquo;<ul></ul></li>')
        );
    }
    function update_more_link(int){
        $('#more_tabs').show().find('#more_tabs_number').text(int);
    }

    make_more_link();

	var table_width = 748;
    var tabs_width = 0;
    var more_link_width = $('#more_tabs').outerWidth() + 10;
    var hidden_tabs = 0;

	$('.data_tab').not('#more_tabs, #more_tabs li').each(function(){
		tabs_width += $(this).outerWidth(true);
		if(tabs_width > table_width - more_link_width){
			$(this).appendTo('#more_tabs ul');
			hidden_tabs++;
            update_more_link(hidden_tabs);
		}
	});
}

$.fn.switchTab = function(){
	return this.each(function(){
		
		$('.data_tab.selected').removeClass('selected');
		$(this).addClass('selected');
		if($(this).is('#more_tabs li')){
			$('#more_tabs').addClass('selected');
		} else {
			$('#more_tabs').removeClass('selected');
		}
		
		var table_name = $(this).attr('id').replace('data_tab_', '');
		var $dp_div = $('#data_preview_'+table_name);
		
		if( $dp_div.is('.hidden')){		
			$dp_div.removeClass('hidden').siblings().addClass('hidden');
	        $("li.table_csv a").attr("href", $('#id_api_base').val() + "datastore/sqlite?format=csv&name=" + $('#scrapershortname').val() + "&query=select+*+from+`"+ encodeURI( $(".data_tab.selected .tablename").text() ) + "`" + "&apikey=" + $('#id_apikey').val());
	        $("li.table_json a").attr("href", $('#id_api_base').val() + "datastore/sqlite?format=json&name=" + $('#scrapershortname').val() + "&query=select+*+from+`"+ encodeURI( $(".data_tab.selected .tablename").text() ) + "`" + "&apikey=" + $('#id_apikey').val());
		}
    })
}

function setupTabClicks(){
	$('li.data_tab').live('click', function(){
		$(this).switchTab();
	});	
}

function getTableNames(callback){
	var url;
	url = sqlite_url + "format=jsondict&name="+short_name+"&query=SELECT%20name, sql%20FROM%20main.sqlite_master%20WHERE%20type%3D'table'%3B";
  
	$.ajax({
		type: 'GET',
		url: url,
		dataType: 'jsonp',
		cache: false,
		success: function(data){
		    var count_url, tables;
		    if (typeof(data) == 'object' && data.error) {
		        setDataPreviewWarning(data.error); 
		        $('#header span.totalrows').text("Datastore error");
		    } else if (data.length) {
		        tables = _.reduce(_.map(data, function(d) {
		            var t = {}
		            t[d.name] = d.sql;
		            return t;
		        }), function(dict, x) {
		              var k = _.keys(x)[0];
		              dict[k] = x[k];
		              return dict;
		        }, {});
		        callback(tables);
		    } else {
				if($('#id_wiki_type').val() == 'scraper'){
		        	setDataPreviewWarning("This " + $('#id_wiki_type').val() + " has no data", true);
		        	$('#header span.totalrows').text("No data");
				} else {
					$('div.data').remove();
				}
		    }
		}, error: function(jqXHR, textStatus, errorThrown){
		    setDataPreviewWarning("Sorry, we couldn\u2019t connect to the datastore");
		    $('#header span.totalrows').hide();
		}
	});
}

function setDataPreviewWarning(text, warningInHeader) {
	if(warningInHeader){
	    $('.data h3').text(text).parent().siblings('.download, .empty').hide();
	} else {
	    $('.data h3').text('Error loading datastore').parent().siblings('.download, .empty').hide().parent().after('<p class="sqliteconnectionerror">' + text + '</p>');
	}
    $('ul.data_tabs, #datapreviews').hide();
}

function getTableColumnNames(table_name, callback){
    qry = sqlite_url + "format=jsonlist&name="+short_name+"&query=SELECT%20*%20FROM%20%5B"+table_name+"%5D%20LIMIT%201"
	$.ajax({
		type: 'GET',
		url: qry,
		dataType: 'jsonp',
		cache: false,
		success: function(data){
		    if (data.error) {
		        setDataPreviewWarning(data.error); 
		        $('#header span.totalrows').text("Datastore error");
		    } else {
		    	callback(data.keys);
			}
		}
	});
}

function getTableRowCounts(tables, callback){
    var count_url;
    sub_queries = (_.map(tables, function(d) {
        return "(SELECT COUNT(*) FROM [" + d + "]) AS '"+ d + "'";
      })).join(',');
    count_url = sqlite_url + "format=jsonlist&name="+short_name+"&query=SELECT%20" + (encodeURIComponent(sub_queries));
	return $.ajax({
		type: 'GET',
		url: count_url,
		dataType: 'jsonp',
		cache: false,
		success: function(resp){
			if (resp.error) {
		        setDataPreviewWarning(resp.error); 
		        $('#header span.totalrows').text("Datastore error");
		    } else {
	        	var zipped = _.zip(resp.keys, resp.data[0]);
	        	callback(_.map(zipped, function(z){
	            	return {name: z[0], id: safeString(z[0]), count: z[1]};
	        	}));
			}
		}
	});
}

function setTotalRowCount(tables){
    values = _.map(tables, function(t){
        return t.count;
    });
    total_rows = _.reduce(values, function(m, v){
        return m + v;
    }, 0);
	var $span = $('<span>').text(total_rows).addClass('totalrows').insertBefore('.privacystatus');
    $span.digits();
    $span.append(total_rows > 1 ? ' records' : ' record');
}

function setDataPreview(table_name, table_schema, first_table){
    getTableColumnNames( table_name, function(column_names){
        $('#datapreviews').append(ich.data_preview({
            table_name: safeString(table_name),
            column_names: column_names
        }));
        var dt = $('#datapreviews #data_preview_' + safeString(table_name) + ' table').dataTable({
            "bProcessing": true,
            "bServerSide": true,
            "bDeferRender": true,
           	"bJQueryUI": true,
            "sPaginationType": "full_numbers",
            "sAjaxSource": $('#id_data_base').val() + encodeURIComponent(table_name) + '/',
            "sScrollX": "100%",
            "bStateSave": true,
            "bScrollCollapse": true,
            "sDom": '<"H"<"#schema_'+table_name+'">lfr>t<"F"ip>',
            "fnRowCallback": function( tr, array, iDisplayIndex, iDisplayIndexFull ) {
                $('td', tr).each(function(){
    				$(this).html(
    					$(this).html().replace(
    						/\.\.\. {{MOAR\|\|([^\|]+)\|\|([^\|]+)\|\|NUFF}}$/g,
    						' <a class="moar" href="/api/1.0/datastore/sqlite?format=jsondict&name=' + $('#scrapershortname').val() + '&query=select%20$1%20as%20%60moar%60%20from%20%60'+ table_name + '%60%20where%20rowid%3D$2&apikey=' + $('#id_apikey').val() + '">&hellip;more</a>'
    					).replace(
    						/((http|https|ftp):\/\/[a-zA-Z0-9-_~#:\.\?%&\/\[\]@\!\$'\(\)\*\+,;=]+)/g,
    						'<a href="$1">$1</a>'
    					)
    				);
                });
                return tr;
            }
        });
    	if(!first_table){
    		dt.parents('.datapreview').addClass('hidden');
    	}
        schema_html = ich.data_preview_schema({sql: table_schema});
        schema_html = highlightSql(schema_html);
        $('#schema_'+table_name).addClass('schema').html(schema_html).children('a').bind('click', schemaClick);
        data_tables.push(dt);
   });
}

function schemaClick(){
  var $a = $(this).text('Hide schema');
  var $p = $a.siblings('div');
  if($p.is(':visible'))
  {
    $p.fadeOut(400);
    $a.text('Show schema');
    $('html').unbind('click');
  }
  else
  {
    $p.fadeIn(150, function(){
				$('html').bind('click', function(e){
					if( $(e.target).parents().index($a.parent()) == -1 ) {
						if( $(e.target).parents().index($p) == -1 ) {
							$p.filter(':visible').fadeOut(400);
							$a.text('Show schema');
							$('html').unbind('click');
						}
					}
				});
			});
		}
	}

function highlightSql(html) {
	schema = html.find('.tableschema');
	sql = schema.text();
	sql = sql.replace(/(CREATE \w+) `(\w+)`/g,
		  '<span class="create">$1</span> `<span class="tablename">$2</span>`');
	sql = sql.replace(/`([^`]+)` (\w+)/g,
          '`<span class="column">$1</span>` <span class="type">$2</span>');
	schema.html(sql);
	return html;
}

function setupDataPreviews() {
	$('.data h3').text('Loading this ' + $('#id_wiki_type').val() + '\u2019s datastore\u2026');
	var tab_src = $('#data-tab-template').html();
	getTableNames(
		function(tables){
			var table_names = _.keys(tables);
			getTableRowCounts( table_names, function(r){
				setTotalRowCount(r);
				var tab_context = {tables: r}
				$('.data_tabs').html(ich.overview_data_tabs(tab_context)).find('i').each(function(i){
					$(this).append(' ' + pluralise('record', $(this).text()));
				});
				setupTabFolding();
				setupTabClicks();
				var i = 0;
				_.each(table_names, function(tn){
					setDataPreview(tn, tables[tn], (i ? false : true ));
					i++;
				});
				$('li.data_tab').eq(0).switchTab();
				$('.data h3').text('This ' + $('#id_wiki_type').val() + '\u2019s datastore');

			    $("li.table_csv a").attr("href", $('#id_api_base').val() + "datastore/sqlite?format=csv&name=" + $('#scrapershortname').val() + "&query=select+*+from+`"+ encodeURI( $(".data_tab.selected .tablename").text() ) + "`" + "&apikey=" + $('#id_apikey').val());
			    $("li.table_json a").attr("href", $('#id_api_base').val() + "datastore/sqlite?format=json&name=" + $('#scrapershortname').val() + "&query=select+*+from+`"+ encodeURI( $(".data_tab.selected .tablename").text() ) + "`" + "&apikey=" + $('#id_apikey').val());
			
				$('a.moar').live('click', function(e){
					e.preventDefault();
					var url = $(this).attr('href');
					$.ajax({
						type: 'GET',
						url: url,
						dataType: 'jsonp',
						success: function(data){
							$('<div>').attr('id', 'moar').text(data[0].moar).modal({
					            overlayClose: true, 
					            autoResize: true,
					            overlayCss: { cursor:"auto" },
								maxHeight: $(window).height() * 0.7,
								maxWidth: $(window).width() * 0.7,
								onOpen: function(dialog) {
									dialog.data.show();
									dialog.overlay.fadeIn(200);
									dialog.container.fadeIn(200);
								},
								onClose: function(dialog) {
									dialog.container.fadeOut(200);
									dialog.overlay.fadeOut(200, function(){
										$.modal.close();
									});
								}
					        });
						}
					});
				})
			
			}); 
		}
	);
}
