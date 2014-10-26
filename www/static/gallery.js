var folder_list;
var entries_list = {};
var current_folder;
var last_date_displayed = null;
var next_entry_to_display = 0;
var current_mode = null;
var current_image_index = 0;
var selected = [];
var current_image_width = 0, current_image_height = 0;
var flip_in_progress = false;

function show_gallery() {
	$("body").addClass("modal-open");
	$("#gallery-root").show();
	adjust_size();
}

function popup(message) {
	$("#gallery-root .popup").html(message).stop().clearQueue().fadeIn(200).fadeOut(1000);
}

function cleanup() {
	// cleanup div contents 
	selected = [];
	$("#gallery-root .selected-pictures .element").each(function() {
		if($(this).find("img").length > 0) {
			$(this).remove();
		}
	});
}

function check_shortcuts(e) {
	if(current_mode == "folders") {
		if(e.keyCode == 27) {
			close_gallery();
		}
	}
	if(current_mode == "entries") {
		if(e.keyCode == 27) {
			show_folder_list();
		}
		else if(e.keyCode == 37) {
			$("#prev-folder").click();
		}
		else if(e.keyCode == 39) {
			$("#next-folder").click();
		}
		else if(e.keyCode == 83) {
			$("#visibility").val("starred");
			load_folder(current_folder);
		}
		else if(e.keyCode == 69) {
			$("#visibility").val("everything");
			load_folder(current_folder);
		}
		else if(e.keyCode == 72) {
			$("#visibility").val("include-hidden");
			load_folder(current_folder);
		}
	}
	if(current_mode == "full") {
		if(e.keyCode == 27) {
			show_entries_list();
		}
		else if(e.keyCode == 37) {
			prev_image();
		}
		else if(e.keyCode == 39) {
			next_image();
		}
		else if(e.keyCode == 88 || e.keyCode == 72) { // x or h toggles hidden
			hide_image_full();
		}
		else if(e.keyCode == 83) { // s toggles stars
			star_image_full();
		}
		else if(e.keyCode == 80) { // p picks 
			pick_image_full();
		}
	}
}

function attach_events() {
	
	// always unbind before bind
	function bind(selector, event_name, func) {
		$(selector).unbind(event_name).bind(event_name, func);
	}
	
	// shortcuts
	bind(document, "keyup", check_shortcuts);
	
	// attach events to gallery elements
	bind(".folder-template a", "click", function() { load_folder($(this).data("folder")); });
	bind(".image-template .pick-button", "click", pick_image);
	bind(".image-template .hide-button", "click", hide_image);
	bind(".image-template .star-button", "click", star_image);
	bind("#to-folders", "click", show_folder_list);

	// window resize
	bind(window, 'resize', function() { adjust_size(); check_progressive_load(); });

	// visibility change: reload
	bind("select#visibility", "change", function() {
		load_folder(current_folder);
	});

	// scroll
	bind("#gallery-root .contents", "scroll", check_progressive_load);

	// swipe
	$("#gallery-root .contents .full").touchwipe({
		wipeLeft: next_image,
		wipeRight: prev_image,
		wipeUp: hide_image_full,
		wipeDown: star_image_full,
		min_move_x: 20,
		min_move_y: 20,
		preventDefaultEvents: true
	}).mouseup(show_entries_list);

	// load folder
	bind("select#folders", "change", function() { load_folder($(this).val()); });

	// folder navigation
	bind("#prev-folder", "click", function() { load_folder(folder_list[folder_list.indexOf(current_folder)-1]); });
	bind("#next-folder", "click", function() { load_folder(folder_list[folder_list.indexOf(current_folder)+1]); });

	bind("#publish-button", "click", function() {
		gallery_options['publish-callback'](selected);
		close_gallery(true);
	});
	bind("#cancel-button", "click", close_gallery);

	// exit confirmation
}

function show_folder_list() {
	current_mode = 'folders';
	$("#gallery-root .contents .folders").fadeIn('fast');
	$("#gallery-root .contents .entries").fadeOut('fast');
	$("#gallery-root .contents .full").fadeOut('fast');
}
function show_entries_list() {
	current_mode = 'entries';
	$("#gallery-root .contents .entries").fadeIn('fast');
	$("#gallery-root .contents .folders").fadeOut('fast');
	$("#gallery-root .contents .full").fadeOut('fast');
}
function show_full(on_complete) {
	current_mode = 'full';
	
	$("#gallery-root .contents .full").fadeIn('fast', on_complete);
	$("#gallery-root .contents .folders").fadeOut('fast');
	$("#gallery-root .contents .entries").fadeOut('fast');
}

function show_loading_indicator(elem) {
	elem.addClass("loading");
}

function hide_loading_indicator(elem) {
	elem.removeClass("loading");
}

function check_progressive_load() {
	var contents = $("#gallery-root .contents");
	if(current_mode == "entries" && contents.scrollTop() + contents.height() >= contents[0].scrollHeight - 50) {
		display_folder_entries();
	}
}

function is_visible(state) {
	var visibility = $("select#visibility").val();
	if(state == 0 && visibility != "include-hidden") return false;
	if(state != 2 && visibility == "starred") return false;
	return true;
}

function scale_size(image_width, image_height, content_width, content_height) {
	var width_over = image_width / content_width;
	var height_over = image_height / content_height;
	if(image_width <= content_width && image_height <= content_height)
		return {'width': image_width, 'height': image_height};
	// if(image_width / content_width <= image_height / content_height) 
	if(image_width * content_height <= image_height * content_width) {
		return {'width': Math.floor(image_width * content_height / image_height), 'height': content_height};
	}
	return {'width': content_width, 'height': Math.floor(image_height * content_width / image_width)};
}

function position_full_image(image_width, image_height) {
	var height = $(".selected-pictures").is(":visible") ? screen_info.height - 130 : screen_info.height;
	var size = scale_size(image_width, image_height, screen_info.width, height);
	var left = Math.floor((screen_info.width - size.width) / 2);
	var top = Math.floor((height - size.height) / 2);
	return {
		'left': left,
		'top': top,
		'width': size.width,
		'height': size.height
	};
}

function append_px(css) {
	return {'left': css.left + 'px',
		'top': css.top + 'px',
		'width': css.width + 'px',
		'height': css.height + 'px'
	};
}

function resize_current_image() {
	var img = $("img.current");
	img.css(append_px(position_full_image(current_image_width, current_image_height)));
}

function get_next_index(delta) {
	var index = current_image_index + delta;
	var entries = entries_list[current_folder];
	while(0 <= index && index < entries.length && !is_visible(entries[index].state))
		index += delta;
	if(index == entries.length) return -1;
	return index;
}

function preload_full_image(delta) {
	var index = get_next_index(delta);
	if(index != -1) {
		var entries = entries_list[current_folder];
		$("<img/>").attr("src", entries[index].file).load();

	}
}

function flip_image(direction) {
	if(flip_in_progress) return;
	var index = get_next_index(direction);
	if(index == -1) {
		show_entries_list();
		return;
	}
	flip_in_progress = true;

	var entry = entries_list[current_folder][index];
	var full = $("#gallery-root .contents .full");

	$("#loading-indicator").show();
	var tmpImage = new Image();
	
	tmpImage.src = entry.file;
	tmpImage.onload = function() {
		$("#loading-indicator").hide();
		var img = $("<img/>").attr("src", entry.file).addClass("new").css("opacity", 0.0);
		var position = position_full_image(tmpImage.width, tmpImage.height);
		position.left = position.left + direction * 100;
		img.css(append_px(position));
		full.append(img);

		var old_image = $("#gallery-root .contents .full .current");
		var new_image = $("#gallery-root .contents .full .new");
		new_image.animate({'left': position.left - direction * 100, 'opacity': 1.0}, 200);
		old_image.css('opacity', 1.0)
			.animate({'left': old_image.position().left - direction * 100, 'opacity': 0.0}, 200, 
					function() {
						old_image.remove();
						new_image.removeClass("new").addClass("current");
						current_image_index = index;
						current_image_width = tmpImage.width;
						current_image_height = tmpImage.height;
						
						if(next_entry_to_display <= current_image_index) {
							display_folder_entries();
						}
						flip_in_progress = false;
					});

	};
}

function prev_image() {
	flip_image(-1);
}

function next_image() {
	flip_image(1);
}

function open_full() {
	var div = $(this).parent();
	div.find("img").css("visibility", "hidden");
	div.addClass("loading");

	current_image_index = $(this).data("index");
	var src = entries_list[current_folder][current_image_index].file;
	var full = $("#gallery-root .contents .full");
	var tmpImage = new Image();
	
	tmpImage.src = src;
	tmpImage.onload = function() {
		var img = $("<img/>")
			.attr("src", src)
			.addClass("current");
		current_image_width = tmpImage.width;
		current_image_height = tmpImage.height;
		full.html(img);
		resize_current_image();
		show_full(function() {
			div.find("img").css("visibility", "visible");
			div.removeClass("loading");
		});
		preload_full_image(1);
	}
}

function display_folder_entries() {
	var body = $("#gallery-root .contents .entries .body");
	var already_loaded = body.find('.image').length;
	var to_display = already_loaded + (screen_info.rows + 1) * screen_info.columns;
	var entries = entries_list[current_folder];
	var template = $(".image-template");
	var date_template = $(".date-template");

	while(next_entry_to_display < entries.length && already_loaded < to_display) {
		var index = next_entry_to_display;
		var entry = entries[next_entry_to_display];
		next_entry_to_display ++;

		if(!is_visible(entry.state)) continue;

		if(entry.date != last_date_displayed) {
			last_date_displayed = entry.date;
			date_template.clone().removeClass("date-template").html(last_date_displayed).appendTo(body);
		}

		var cloned = template.clone(true);
		cloned.removeClass("image-template").attr('id', 'entry-' + entry.pk);
		cloned.find('img').data('pk', entry.pk)
			.data("index", index)
			.data('full-url', entry.file)
			.attr('src', entry.thumbnail)
			.click(open_full);
		update_image_icons(cloned, entry.state);
		cloned.appendTo(body);
		already_loaded ++;
	}
}

function update_folder_navigation_buttons() {
	if(current_folder == folder_list[0]) 
		$("#prev-folder").attr('disabled', 'disabled');
	else
		$("#prev-folder").removeAttr('disabled');
	if(current_folder == folder_list[folder_list.length-1]) 
		$("#next-folder").attr('disabled', 'disabled');
	else
		$("#next-folder").removeAttr('disabled');
}

function load_folder(folder) {
	if(folder === undefined) return;
	$("select#folders").val(folder);
	var entries = $("#gallery-root .contents .entries");
	var body = $("#gallery-root .contents .entries .body");
	body.html("");

	function go() {
		next_entry_to_display = 0;
		current_folder = folder;
		update_folder_navigation_buttons();

		last_date_displayed = null;
		display_folder_entries();
	}

	if(!(folder in entries_list)) {
		show_loading_indicator(entries);
		show_entries_list();
		$.getJSON(gallery_options['list-images-endpoint'], {'folder': folder}, function(data) {
			hide_loading_indicator(entries);
			entries_list[folder] = data;
			go();
		});
	}
	else {
		show_entries_list();
		go();
	}
}

function load_folder_list() {
	// load folder list
	// on completion, generate thumbnails and entries
	var folders = $("#gallery-root .contents .folders");
	folders.html("");
	show_loading_indicator(folders);
	show_folder_list();

	$.getJSON(gallery_options['list-folders-endpoint'], function(data) {
		hide_loading_indicator(folders);

		var template = $(".folder-template");

		folder_list = [];

		var folders_select = $("select#folders");
		folders_select.html("");

		for(var i = 0; i < data.length; ++i) {

			var cloned = template.clone(true);
			cloned.removeClass("folder-template");
			cloned.find("a").data("folder", data[i].folder);
			cloned.find(".text").html(data[i].folder);
			cloned.find(".imgcnt").html(data[i].images);
			cloned.find("img").attr("src", data[i].thumbnail);
			cloned.appendTo(folders);

			folder_list.push(data[i].folder);

			folders_select.append($("<option/>").val(data[i].folder).text(data[i].folder));
		}
	});
}



function open_gallery() {
	// if($("#gallery-root").length > 0) return;

	cleanup();
	attach_events();
	show_gallery();

	load_folder_list();
}

function close_gallery(no_check) {
	if(selected.length == 0 || no_check || confirm("선택된 사진이 있습니다. 정말 닫으시겠어요?")) {
		$("body").removeClass("modal-open");
		$("#gallery-root").hide("fast");
		hide_selected();
	}
}

function update_screen_info(content_width, content_height) {
	content_width -= 20;
	var width_shrinken = content_width - 20;
	var candidates = [150, 125, 100];
	var thumb_width = 75;
	for(var i = 0; i < candidates.length; ++i) {
		if(width_shrinken >= (candidates[i] + 10) * 5) {
			thumb_width = candidates[i];
			break;
		}
	}

	var columns = Math.floor(width_shrinken / (thumb_width + 16));
	var margin = Math.floor(((width_shrinken - (columns * thumb_width)) / columns) / 2);
	var rows = Math.floor(content_height / (thumb_width + margin));
	return {"css": {"width": thumb_width + "px", "margin-right": margin + "px", "margin-left": margin + "px"},
		      "columns": columns,
					"rows": rows, 
					"width": content_width,
				  "height": content_height};
}

var screen_info = {}; 

function adjust_size() {
	// resize thumbnails
	var pane = $("#gallery-root .contents");
	screen_info = update_screen_info(pane.width(), pane.height());
	$("#gallery-root .contents .folder").css(screen_info.css);
	$("#gallery-root .contents .image").css(screen_info.css);

	// resize full images
	if(current_mode == "full") {
		resize_current_image();
	}
}

function hide_selected() {
	$(".selected-pictures").fadeOut('fast').animate({'height': '0px'}, 'fast', resize_current_image);
	$(".folders").css({"padding-bottom": "0px"});
	$(".entries").css({"padding-bottom": "0px"});
}
function show_selected() {
	$(".selected-pictures").fadeIn('fast').animate({'height': '130px'}, 'fast', resize_current_image);
	$(".folders").css({"padding-bottom": "130px"});
	$(".entries").css({"padding-bottom": "130px"});
}

function search_selected(pk) {
	for(var i = 0; i < selected.length; ++i)
		if(selected[i].pk == pk) {
			return i;
		}
	return -1;
}

function pick_image() {
	var image = $(this).parent().parent();
	var img = image.find("img");
	var index = img.data("index");
	var pk = img.data("pk");
	var entry = entries_list[current_folder][index];
	pick_image_impl(pk, entry);
}

function pick_image_full() {
	var entry = entries_list[current_folder][current_image_index];
	pick_image_impl(entry.pk, entry);
}

function pick_image_impl(pk, entry) {
	if(search_selected(pk) != -1) return;
	show_selected();
	selected.push(entry);
	var cloned = $(".element-template").clone().removeClass("element-template");
	cloned.find("img")
		.data("pk", entry.pk)
		.attr("src", entry.thumbnail)
		.css({"width": "100px", "cursor": "pointer"})
		.click(function() {
			selected.splice(search_selected(pk), 1);
			cloned.remove();

			if($(".selected-pictures img").length == 0) {
				hide_selected();
			}
		});
	cloned.appendTo(".selected-pictures");
	popup("사진을 선택 목록에 추가했습니다.");
}

function update_image_icons(image, state) {
	if(state == 0) {
		image.find(".is-hidden").removeClass("glyphicon-eye-open").addClass("glyphicon-eye-close");
	}
	else {
		image.find(".is-hidden").removeClass("glyphicon-eye-close").addClass("glyphicon-eye-open");
	}

	if(state == 2) {
		image.find(".is-starred").removeClass("glyphicon-star-empty").addClass("glyphicon-star");
	}
	else {
		image.find(".is-starred").removeClass("glyphicon-star").addClass("glyphicon-star-empty");
	}
}

function star_image_full() {
	var entry = entries_list[current_folder][current_image_index];
	var image = $("#entry-" + entry.pk);
	var pk = entry.pk;
	var target_state = entry.state == 2 ? 1 : 2;
	update_entry_state(image, current_image_index, pk, entry, target_state);
	popup(target_state == 2 ? "별을 추가했습니다." : "별을 지웠습니다.");
	if(!is_visible(target_state)) {
		next_image();
	}
}

function star_image() {
	var image = $(this).parent().parent();
	var img = image.find("img");
	var index = img.data("index");
	var pk = img.data("pk");
	var entry = entries_list[current_folder][index];
	var target_state = entry.state == 2 ? 1 : 2;

	update_entry_state(image, index, pk, entry, target_state);
	popup(target_state == 2 ? "별을 추가했습니다." : "별을 지웠습니다.");
}

function hide_image_full() {
	var entry = entries_list[current_folder][current_image_index];
	var image = $("#entry-" + entry.pk);
	var pk = entry.pk;
	var target_state = entry.state == 0 ? 1 : 0;
	update_entry_state(image, current_image_index, pk, entry, target_state);
	popup(target_state == 0 ? "이미지를 숨겼습니다." : "숨김 속성을 껐습니다.");
	if(!is_visible(target_state)) {
		next_image();
	}
}

function hide_image() {
	var image = $(this).parent().parent();
	var img = image.find("img");
	var index = img.data("index");
	var pk = img.data("pk");
	var entry = entries_list[current_folder][index];
	var target_state = entry.state == 0 ? 1 : 0;

	update_entry_state(image, index, pk, entry, target_state);
	popup(target_state == 0 ? "이미지를 숨겼습니다." : "숨김 속성을 껐습니다.");
}

function update_entry_state(image, index, pk, entry, target_state) {
	var visibility = $("select#visibility").val();

	$.ajax({
		'url': gallery_options['set-image-state-endpoint'], 
		'data': {'pk': pk, 'state': target_state}, 
		'success': function(data) {
			if(data != "ok") { 
				alert("oops!");
				return;
			}

			entry.state = target_state;

			if(!is_visible(target_state)) {
				image.hide('fast', function() { 
					image.remove(); 
					check_progressive_load();
				});
			}
			else {
				update_image_icons(image, target_state);
			}
		}});
}

// function star_image() {
// 	var image = $(this).parent().parent();
// 	var is_starred = image.find(".is-starred").hasClass("glyphicon-star");
// 	var target_state = is_starred ? 1 : 2;
// 	var pk = image.find("img").data("pk");
// 	var visibility = $("select#visibility").val();
// 
// 	$.ajax({
// 		'url': gallery_options['set-image-state-endpoint'], 
// 		'data': {'pk': pk, 'state': target_state}, 
// 		'success': function(data) {
// 			if(data != "ok") alert("oops!");
// 			if(target_state == 1 && visibility == "starred") {
// 				image.hide('fast', function() { 
// 					image.remove(); 
// 					check_progressive_load();
// 				});
// 			}
// 			else {
// 				update_image_icons(image, target_state);
// 			}
// 		}});
// }


