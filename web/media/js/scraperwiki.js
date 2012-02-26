//	Avoids the 'event.layerX and event.layerY' warnings in Chrome
//	http://stackoverflow.com/questions/7825448/webkit-issues-with-event-layerx-and-event-layery
(function(){
    // remove layerX and layerY
    var all = $.event.props,
        len = all.length,
        res = [];
    while (len--) {
      var el = all[len];
      if (el != 'layerX' && el != 'layerY') res.push(el);
    }
    $.event.props = res;
}());

// Boilerplate to add CSRF protection headers, taken from https://docs.djangoproject.com/en/1.3/ref/contrib/csrf/
$(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

function trim(stringToTrim) {
	return stringToTrim.replace(/^\s+|\s+$/g,"");
}
function ltrim(stringToTrim) {
	return stringToTrim.replace(/^\s+/,"");
}
function rtrim(stringToTrim) {
	return stringToTrim.replace(/\s+$/,"");
}


function setupNavSearchBoxHint(){
    $('#nav_search_q').bind('focus', function() {
        if ($(this).val() == 'Search datasets') {
            $(this).val('');
            $(this).removeClass('hint');
        }
		$('#navSearch').addClass('focus');
    }).bind('blur', function() {
        if($(this).val() == '') {
            $(this).val('Search datasets');
            $(this).addClass('hint');
        }
		$('#navSearch').removeClass('focus');
    });
	if($('#nav_search_q').val() == ''){
		$('#nav_search_q').val('Search datasets').addClass('hint');
		$('#navSearch').removeClass('focus');
	}
}

function newCodeObject($a){
	if($a){	
		if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'New Code Object', $a.data('wiki_type')]); }
		url = '/' + $a.data('wiki_type') + 's/new/choose_template/?ajax=1';
		if ( $a.data('sourcescraper') ) {
			url += "&sourcescraper=" + $a.data('sourcescraper');
		}
		
		/*	
			NOTE:
			This actually causes a problem, if someone tries to create a new View
			(with a sourcescraper attribute) and then ALSO tries to save it into
			a vault. They end up being taken to a url like:
			/views/new/php?sourcescraper=ORIGINAL_SCRAPER/tovault/VAULT_ID/?name=NEW_VIEW
			which doesn't work. The View isn't created in the vault. Instead, it's
			created publically, and the sourcescraper name is taken to be:
			"ORIGINAL_SCRAPER/tovault/VAULT_ID/?name=NEW_VIEW"
			D'oh!!
		*/
		
		$.get(url, function(data){
	        $.modal('<div id="template_popup">'+data+'</div>', {
	            overlayClose: true, 
	            autoResize: true,
	            overlayCss: { cursor:"auto" },
				onOpen: function(dialog) {
					dialog.data.show();
					dialog.overlay.fadeIn(200);
					dialog.container.fadeIn(200);
				},
				onShow: function(dialog){
					$('#simplemodal-container').css('height', 'auto');
					$('#chooser_vaults h2', dialog.data).bind('click', function(e){
						if($(this).next().is(':visible')){
							$(this).children('input').attr('checked', false);
							$(this).nextAll('p').slideUp(250);
						} else {
							$(this).children('input').attr('checked', true);
							$(this).nextAll('p').slideDown(250, function(){
								$('#chooser_name_box').focus();
							});
						}
					});
					if($a.data('vault_id')){
						$('#chooser_vaults h2', dialog.data).trigger('click');
						$('select option[value$="/' + $a.data('vault_id') + '/"]', dialog.data).attr('selected', 'selected');
					}
					$('li a[href]', dialog.data).bind('click', function(e){
						if( ! $('#chooser_vaults h2 input').is(":visible")  ) {
							return;
						}

						if ( ! $('#chooser_vaults h2 input').is(":checked") ) {
							return;
						}

						e.preventDefault();
						if($('#chooser_vaults h2 input', dialog.data).is(':checked')){
							if($('#chooser_name_box', dialog.data).val() == ''){
								$('span.warning', dialog.data).remove();
								text = $('label', dialog.data).attr('title');
								$('#chooser_vaults p', dialog.data).eq(0).addClass('error').append('<span class="warning"><span></span>' + text + '</span>');
								$('#chooser_name_box', dialog.data).bind('keyup', function(){
									$('#chooser_vaults p.error', dialog.data).removeClass('error').children('span').remove();
									$(this).unbind('keyup');
								})
							} else {
								$(this).addClass('active');
								location.href = $('#chooser_vault').val().replace('/python/', '/' + $(this).attr('href').replace(/.*\//, '') + '/') + '?name=' + encodeURIComponent($('#chooser_name_box').val());								
							}
						}
					});
					function hide_javascript_crap(){
						$('li.javascript').removeClass('first').siblings().slideDown(200);
						$('#chooser_vaults', dialog.data).slideDown(200);
						$('#javascript', dialog.data).slideUp(200);
					}
					$('li.javascript a', dialog.data).bind('click', function(e){
						var userid = $(this).data('userid') || '';
						if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Javascript scrapers', 'Curious', userid]); }
						$(this).parent().addClass('first').prevAll().slideUp(200);
						$('#chooser_vaults', dialog.data).slideUp(200);
						$('#javascript', dialog.data).slideDown(200);
					});
					$('#javascript_meh', dialog.data).bind('click', function(e){
						var userid = $('li.javascript a', dialog.data).data('userid') || '';
						if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Javascript scrapers', 'Javascript, Meh', userid]); }
						hide_javascript_crap();
					});
					$('#i_heart_javascript').bind('click', function(e){
						var userid = $('li.javascript a', dialog.data).data('userid') || '';
						if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Javascript scrapers', 'I HEART JAVASCRIPT!', userid]); }
						$(this).unbind('click').html('Thanks!').addClass('smiley').animate({opacity:1}, 2000, hide_javascript_crap);
					});
				},
				onClose: function(dialog) {
					dialog.container.fadeOut(200);
					dialog.overlay.fadeOut(200, function(){
						$.modal.close();
					});
				}
	        });
	    });		
		
		
	} else {
		alert('no anchor element provided');
	}
}

function newUserMessage(url){
	
	if(url == undefined){
		alert('No message url specified');
	} else {
//    	if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Profile buttons', 'Send Message']); }
    	$.get(url, function(data){
	        $.modal('<div id="message_popup">'+data+'</div>', {
	            overlayClose: true, 
	            autoResize: true,
	            overlayCss: { cursor:"auto" },
				onOpen: function(dialog) {
					dialog.data.show();
					dialog.overlay.fadeIn(200);
					dialog.container.fadeIn(200);
				},
				onShow: function(dialog){
					$('#simplemodal-container').css('height', 'auto');
					$('h1', dialog.data).append(' to ' + $('.profilebio h3').text());
					$('textarea', dialog.data).focus();
					$(':submit', dialog.data).bind('click', function(e){
						e.preventDefault();
					//	var action = location.href + '/message/';
						var action = $('form', dialog.data).attr('action');
						var data = $('form', dialog.data).serialize();
						$.ajax({
							type: 'POST',
							url: action,
							data: data,
							success: function(data){
								if(data.status == 'ok'){
									if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Profile buttons', 'Send Message (message sent!)']); }
									$('h1', dialog.data).after('<p class="success">Message sent!</p>');
									$('form', dialog.data).remove();
									var t = setTimeout(function(){
										$('#simplemodal-overlay').trigger('click');
									}, 1000);
								} else {
									$('p.last', dialog.data).before('<p class="error">' + data.error + '</p>');
								}
							},
							dataType: 'json'
						});
					});
				},
				onClose: function(dialog) {
					dialog.container.fadeOut(200);
					dialog.overlay.fadeOut(200, function(){
						$.modal.close();
					});
				}
	        });
	    });
	}
}

//	Creates a pretty orange Alert bar at the top of the window.
//	Uses the same HTML as web/templates/frontend/messages.html
//	htmlcontent (string) -> the textual content of the alert (can include html tags and entities)
//	level (string) -> either 'error' or 'info' (null is treated as error)
//	actions (array) -> array of buttons (each with a url/action, text and optional 'secondary' object)
//	duration (number/string) -> how long slide animation lasts (set to null for no animation)
function newAlert(htmlcontent, level, actions, duration, onclose){
	if(typeof(level) != 'string'){ level = 'error'; }
	$alert_outer = $('<div>').attr('id','alert_outer').addClass(level);
	$alert_inner = $('<div>').attr('id','alert_inner').html('<span class="message">' + htmlcontent + '</span>');
	if(typeof(actions) == 'object'){
		var $a = $('<a>').html(actions.text);
		if(typeof(actions.url) != 'undefined'){
			$a.attr('href', actions.url);
		}
		if(typeof(actions.secondary) != 'undefined'){
			$a.addClass('secondary');
		}
		if(typeof(actions.onclick) != 'undefined'){
			$a.bind('click', actions.onclick);
		}		
		$alert_inner.append($a);
	}
	$('<a>').attr('id','alert_close').bind('click', function(){
		if(typeof(onclose) != 'undefined'){
			onclose();
		}
		$('#alert_outer').slideUp(250);
		$('#nav_outer').animate({marginTop:0}, 250);
	}).appendTo($alert_inner);
	if(typeof(duration) == 'string' || typeof(duration) == 'number'){
		$('#nav_outer').animate({'marginTop': $alert_outer.outerHeight()}, duration);
		$alert_outer.hide().insertBefore($('#nav_outer'));
		$alert_outer.append($alert_inner).animate({
			height: "show",
			marginTop: "show",
		    marginBottom: "show",
		    paddingTop: "show",
		    paddingBottom: "show"
		}, { 
			step: function(now, fx){
				$('#nav_outer').css('margin-top', $(fx.elem).outerHeight());
			}, complete: function(){
				$('#nav_outer').css('margin-top', $('#alert_outer').outerHeight());
			},
			duration: duration
		});
	} else {
		$alert_outer.append($alert_inner).insertBefore($('#nav_outer'));
		$('#nav_outer').css('margin-top', $alert_outer.outerHeight());
	}
	
}

function openSurvey(){
	if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Developer survey', 'Open modal window']); }
	var url = 'http://sw.zarino.co.uk/';
	if($('#nav_inner .loggedin').length){
		regexp_username = new RegExp('/profiles/([^/]+)/');
		var url = url + '?username=' + $('#nav_inner .loggedin a').attr('href').replace(regexp_username, '$1');
	}
	$.modal('<h1 class="modalheader">ScraperWiki Developer Survey</h1><iframe src="' + url + '" height="500" width="500" style="border:0">', {
        overlayClose: true, 
        autoResize: true,
        overlayCss: { cursor:"auto" },
		onOpen: function(dialog) {
			dialog.data.show();
			dialog.overlay.fadeIn(200);
			dialog.container.fadeIn(200);
		},
		onShow: function(dialog){
			$('#simplemodal-container').css('height', 'auto');
		},
		onClose: function(dialog) {
			if($('#alert_close').length){
				$('#alert_inner .message').text('Thanks!').siblings('a').not('#alert_close').remove();
				var t = setTimeout(function(){
					$('#alert_close').trigger('click');
				}, 1000);
			}
			// developerSurveyDone();
			dialog.container.fadeOut(200);
			dialog.overlay.fadeOut(200, function(){
				$.modal.close();
			});
		}
    });
}

/* function developerSurveyDone(){
	setCookie("developerSurveyDone", '1', 365);
	if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Developer survey', 'Leave modal window']); }
}

function developerSurveySkipped(){
	setCookie("developerSurveySkipped", '1', 365);
	if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Developer survey', 'Ignore alert bar']); }
} */

function setCookie(c_name,value,exdays){
	var exdate = new Date();
	exdate.setDate(exdate.getDate() + exdays);
	var c_value = escape(value) + ((exdays==null) ? "" : "; expires="+exdate.toUTCString());
	document.cookie = c_name + "=" + c_value;
}

function getCookie(c_name){
	var i,x,y,ARRcookies = document.cookie.split(";");
	for (i=0;i<ARRcookies.length;i++){
		x = ARRcookies[i].substr(0,ARRcookies[i].indexOf("="));
		y = ARRcookies[i].substr(ARRcookies[i].indexOf("=")+1);
		x = x.replace(/^\s+|\s+$/g,"");
		if (x == c_name){
			return unescape(y);
		}
	}
}


$(function(){
	
	/* regexp_baseurl = new RegExp('(https?://[^/]+).*');
	if(document.referrer.replace(regexp_baseurl, '$1') == document.URL.replace(regexp_baseurl, '$1')){
		survey_alert_slide = null;
	} else {
		survey_alert_slide = 250;
	}
	
	if(typeof(getCookie('developerSurveyDone')) != 'undefined' || typeof(getCookie('developerSurveySkipped')) != 'undefined'){
		// console.log('You&rsquo;ve either skipped or completed the survey');
	} else {
		newAlert('Help us make ScraperWiki even better for you!', null, {'onclick': openSurvey, 'text': 'Take our speedy survey'}, survey_alert_slide, developerSurveySkipped);
		if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Developer survey', 'Alert shown']); }
	} */
	
	$('#divMenu ul li.survey a').bind('click', function(e){
		e.preventDefault();
		openSurvey();
		if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Developer survey', 'Open modal window']); }
	});
	
    setupNavSearchBoxHint();

    $('a.editor_view, div.network .view a, a.editor_scraper, a.add_to_vault ').click(function(e) {
		e.preventDefault();
		newCodeObject($(this));
    });
	
	function developer_show(){
		$('#intro_developer, #intro_requester, #blob_requester').fadeOut(500);
		$('#more_developer_div').fadeIn(500);
		$('#blob_developer').animate({left: 760}, 500, 'easeOutCubic').addClass('active');
	}
	
	function developer_hide(){
		$('#intro_developer, #intro_requester, #blob_requester').fadeIn(500);
		$('#more_developer_div').fadeOut(500);
		$('#blob_developer').animate({left: 310}, 500, 'easeOutCubic').removeClass('active');
	}
	
	function requester_show(){
		$('#intro_developer, #intro_requester, #blob_developer').fadeOut(500);
		$('#more_requester_div').fadeIn(500);
		$('#blob_requester').animate({left: 10}, 500, 'easeOutCubic').addClass('active');
	}
	
	function requester_hide(){
		$('#intro_developer, #intro_requester, #blob_developer').fadeIn(500);
		$('#more_requester_div').fadeOut(500);
		$('#blob_requester').animate({left: 460}, 500, 'easeOutCubic').removeClass('active');
	}
	
	$('#blob_developer').css('cursor', 'pointer').bind('click', function(e){
		e.preventDefault();
	    if($(this).is('.active')){
	        developer_hide();
	    } else {
	        developer_show();
			if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Homepage buttons', 'Developer - find out more']); }
	    }
	});
	
	$('#blob_requester').css('cursor', 'pointer').bind('click', function(e){
		e.preventDefault();
	    if($(this).is('.active')){
	        requester_hide();
	    } else {
	        requester_show();
			if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Homepage buttons', 'Requester - find out more']); }
	    }
	});
	
	$('#more_developer, #intro_developer').css('cursor', 'pointer').bind('click', function(e){
		e.preventDefault();
		developer_show();
		if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Homepage buttons', 'Developer - find out more']); }
	});

	$('#more_requester, #intro_requester').css('cursor', 'pointer').bind('click', function(e){
		e.preventDefault();
		requester_show();
		if(typeof _gaq !== 'undefined'){ _gaq.push(['_trackEvent', 'Homepage buttons', 'Requester - find out more']); }
	});

	$('#more_developer_div .back').bind('click', function(e){
		e.preventDefault();
		developer_hide();
	});	
	
	$('#more_requester_div .back').bind('click', function(e){
		e.preventDefault();
		requester_hide();
	});
	
	
	
	
	$('a.submit_link').each(function(){
		id = $(this).siblings(':submit').attr('id');
		$(this).addClass(id + '_link')
	}).bind('click', function(e){
		e.preventDefault();
		$(this).siblings(':submit').trigger('click');
	}).siblings(':submit').hide();
	
	$('#fourohfoursearch').val($('body').attr('class').replace("scrapers ", "").replace("views ", ""));
	
	
	
	$('div.vault_usage_popover').each(function(i,el){
		//	This centres the Usage Popover underneath the Usage progressbar
		var popo = $(this);
		var prog = $(this).prevAll('.usage').children('.progressbar');
		var anchor = prog.position().left + (0.5 * prog.outerWidth());
		popo.css('left', anchor - (popo.outerWidth() / 2) );
	});
	
	$('body.vaults .usage').bind('click', function(e){
		var $a = $(this).addClass('hover');
		var $p = $a.siblings('div.vault_usage_popover');
		if($p.is(':visible')){
			$p.fadeOut(400);
			$a.removeClass('hover');
			$('html').unbind('click');
		} else {
			$p.fadeIn(150);
			$('html').bind('click', function(e){
				if( $(e.target).parents().index($a) == -1 ) {
					if( $(e.target).parents().index($p) == -1 ) {
						$p.filter(':visible').fadeOut(400);
						$a.removeClass('hover');
						$('html').unbind('click');
					}
				}
			});
		}
	});
	
	
	
	
	$('div.vault_users_popover').each(function(i,el){
		//	This centres the Users Popover underneath the Users toolbar button
		var popo = $(this);
		var link = $(this).prevAll('.vault_users');
		var anchor = link.position().left + (0.5 * link.outerWidth());
		popo.css('left', anchor - (popo.outerWidth() / 2) );
	});
	
	$('body.vaults a.vault_users').bind('click', function(e){
		var $a = $(this).addClass('hover');
		var $p = $a.siblings('div.vault_users_popover');
		if($p.is(':visible')){
			$p.fadeOut(400, function(){
				$p.find('li.new_user_li, li.error').remove();
				$p.children('a.add_user').show();
			});
			$a.removeClass('hover');
			$('html').unbind('click');
		} else {
			$p.fadeIn(150);
			$('html').bind('click', function(e){
				if( $(e.target).parents().index($a) == -1 ) {
					if( $(e.target).parents().index($p) == -1 ) {
						if( $(e.target).parents().index($('.ui-autocomplete')) == -1 ) {
							if($(e.target).not('[class*="ui-"]').length){
								// they didn't click on the users link or the popover or the autocomplete
								$p.filter(':visible').fadeOut(400, function(){
									$p.find('li.new_user_li, li.error').remove();
									$p.find('a.add_user').show();
								});
								$a.removeClass('hover');
								$('html').unbind('click');
							}
						}
					}
				}
			});
		}
	});
	
	$('body.vaults a.add_user').bind('click', function(){
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
				//	submit the name
				//	$(this).next('a').trigger('click');
			}
		});
	
		var confirm = $('<a>').text('Add!').bind('click', function(){
			var closure = $(this).prev();
			closure.parents('ul').children('.error').slideUp(150);
			var username = closure.val();
			var vault_id = closure.parents('div').find('a.add_user').attr('rel');
			var url = '/vaults/' + vault_id + '/adduser/' + username + '/';
			$.getJSON(url, function(data) {
				if(data.status == 'ok'){
					closure.autocomplete("close").parents('ul').next('a').slideDown(150);
					closure.updateUserCount(1).parent().before( data.fragment ).remove();
				} else if(data.status == 'fail'){
					closure.autocomplete("close").parents('ul').append('<li class="error">' + data.error + '</li>');
				}
			});
		});
		var li = $('<li>').hide().addClass("new_user_li").append('<label for="username">Username:</label>').append(input).append(confirm);
		$(this).slideUp(250).prev().append(li).children(':last').slideDown(250).find('#username').focus();
	});
	
	$('body.vaults a.user_delete').live('click', function(e){
		e.preventDefault();
		var url = $(this).attr('href');
		var closure = $(this);
		$.ajax({
			url: url,
			dataType: 'json',
			success: function(data) {
				if(data.status == 'ok'){
					closure.updateUserCount(-1).parent().slideUp(function(){
						$(this).remove();
					});
				} else if(data.status == 'fail'){
					closure.parents('ul').append('<li class="error">Error: ' + data.error + '</li>');
				}
			}, 
			error: function(data){
				closure.parents('ul').append('<li class="error">There was an error loading the json delete action</li>');
			}
		});
	});
	
	jQuery.fn.updateUserCount = function(increment) {
		//	Must be called from an element within <div class="vault_header"></div>
		return this.each(function() {
		    var $el = $(this);
			var number_of_users = Number($el.parents('.vault_header').find('.vault_users_popover li').not('.new_user_li').length) + increment;
			if(number_of_users == 1){
				x_users = '1 member';
			} else {
				x_users = number_of_users + ' members';
			}
			$el.parents('.vault_header').find('.x_users').text(x_users);
		});
	}
	
	$('body.vaults .transfer_ownership a').bind('click', function(e){
		e.preventDefault();
		$(this).next('span').show().children(':text').focus();
		$('span', this).show();
	});
	
	$('body.vaults .transfer_ownership input:text').autocomplete({
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
			// submit the name
			$(this).next('input').attr('disabled',false);
		}
	}).next().bind('click', function(){
		var url = $(this).parent().prev().attr('href') + $(this).prev().val() + '/';
		var button = $(this).val('Transferring\u2026');
		$.ajax({
			url: url,
			dataType: 'json',
			success: function(data) {
				if(data.status == 'ok'){
					window.location.reload();
				} else if(data.status == 'fail'){
					button.after('<em class="error">Error: ' + data.error + '</em>');
					button.val('Transfer!');
				}
			}, 
			error: function(data){
				button.after('<em class="error">Error: ' + data.error + '</em>');
				button.val('Transfer!');
			}
		});
	}).attr('disabled', true);
	
	if($('#alert_outer').length && (!$('#alert_close').length)){
		$('<a>').attr('id','alert_close').bind('click', function(){ 
			$('#alert_outer').slideUp(250);
			$('#nav_outer').animate({marginTop:0}, 250);
		}).appendTo('#alert_inner');
		$('#nav_outer').css('margin-top', $('#alert_outer').outerHeight());
	}
	
	$('#compose_user_message').bind('click', function(e){
		e.preventDefault();
		newUserMessage($(this).attr('href'));
	});
	
	if($('#compose_user_message').length && window.location.hash == '#message'){
		$('#compose_user_message').trigger('click');
	}
	
	
	$('#liberatesomedata').bind('click', function(e){
		e.preventDefault();
		var viewurl = $(this).attr('href');
		$.ajax({
			url: viewurl,
			dataType: 'jsonp',
			success: function(data){
				var div = $('<div id="liberate_popup">');
				div.append('<h1>Liberate some data!</h1>');
				div.append('<h2 class="vote">Vote for other people&rsquo;s suggestions&hellip;</h2>');
				div.append('<ul></ul>');
				
				function populate_list(data, viewurl){
					if(data.length){
						$('ul', div).empty();
						$.map(data, function(val, i){
							var li = $('<li>');
							li.append('<span class="place">#' + (i+1) + '</span>');
							li.append('<a href="' + val.url + '" class="url">' + val.url.replace(/https?:\/\//i, "") + '</strong>');
							li.append('<span class="why">' + val.why + '</span>');
							$('<span class="vote" title="Vote for this">Vote</span>').bind('click', function(){
								$(this).addClass('loading').unbind('click');
								$.ajax({
									url: viewurl + '?vote=' + encodeURIComponent(val.url),
									dataType: 'jsonp',
									success: function(data){
										populate_list(data, viewurl);
									}
								});
							}).appendTo(li);
							$('ul', div).append(li);
						});	
					} else {
						$('ul', div).html('<li><span class="place">?</span> <span class="url">No suggestions yet</span> <span class="why">Why not suggest a dataset below?</span></li>');
					}
				}
				
				populate_list(data, viewurl);	
				
				var form = $('<form>');
				
				$('<h2 class="suggest">&hellip;Or suggest something new</h2>').appendTo(form);
				$('<p class="url"><label for="url">At what URL can we find the data?</label><input type="text" id="url" /></p>').appendTo(form);
				$('<p class="why"><label for="why">Why do you want it liberated?</label><input type="text" id="why" /></p>').appendTo(form);
				$('<p class="submit"><input type="submit" value="Liberate this data!" /></p>').bind('click', function(e){
					e.preventDefault();
					$.ajax({
						url: viewurl + '?add=' + encodeURIComponent($('#url').val()) + '&why=' + encodeURIComponent($('#why').val()),
						dataType: 'jsonp',
						success: function(data){
							populate_list(data, viewurl);
							$('#why, #url').val('');
							$('h2.suggest').nextAll('p').animate({"height": "hide", "marginTop": "hide", "marginBottom": "hide", "paddingTop": "hide", "paddingBottom": "hide"},{
							duration: 250,
							step: function(now, fx) {
							    $.modal.setPosition();
							}});
						}
					});
				}).appendTo(form);
				div.append(form);
				
				
				$.modal(div, {
		            overlayClose: true, 
		            autoResize: true,
		            overlayCss: { cursor:"auto" },
					onOpen: function(dialog) {
						dialog.data.show();
						dialog.overlay.fadeIn(200);
						dialog.container.fadeIn(200);
					},
					onShow: function(dialog){
						$('#simplemodal-container').css('height', 'auto');
						$('h2.suggest', dialog.data).bind('click', function(){
							if($(this).next().is(':visible')){
								$(this).nextAll('p').animate({"height": "hide", "marginTop": "hide", "marginBottom": "hide", "paddingTop": "hide", "paddingBottom": "hide"},{
								duration: 250,
								step: function(now, fx) {
								    $.modal.setPosition();
								}});
							} else {
								$(this).nextAll('p').animate({"height": "show", "marginTop": "show", "marginBottom": "show", "paddingTop": "show", "paddingBottom": "show"},{
								duration: 250,
								step: function(now, fx) {
								    $.modal.setPosition();
								}});
							}
						});
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
		
	});
	
	
});