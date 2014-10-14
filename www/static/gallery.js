function setup_layout() {
	// $("body").append('<div id="gallery-root"></div>")');
	// var root = $("#gallery-root");

	// root.show("fast");
}

function load_folder_list() {
	// load folder list
	// on completion, generate thumbnails and entries
}

function open_gallery() {
	// if($("#gallery-root").length > 0) return;
	$("body").addClass("modal-open");
	setup_layout();
	load_folder_list();
}

function close_gallery() {
	$("#gallery-root").hide("fast", function() { $(this).remove(); });
}

function determine_thumbnail_size(content_width) {
	content_width -= 20;
	var candidates = [150, 125, 100];
	var thumb_width = 75;
	for(var i = 0; i < candidates.length; ++i) {
		if(content_width >= (candidates[i] + 10) * 5) {
			thumb_width = candidates[i];
			break;
		}
	}

	var columns = Math.floor(content_width / (thumb_width + 16));
	var margin = Math.floor(((content_width - (columns * thumb_width)) / columns) / 2);
	console.log("thumb_width", thumb_width, "columns", columns);
	return {"width": thumb_width + "px", "margin-right": margin + "px", "margin-left": margin + "px"};
}

var thumbnail_size = {}; 

function adjust_size() {
	var pane = $("#gallery-root .contents");
	thumbnail_size = determine_thumbnail_size(pane.width());
	$("#gallery-root .contents .entry").css(thumbnail_size);
	$("#gallery-root .sidebar .selected .entry").css({"width": thumbnail_size.width});
}

function attach_events_to_entry_buttons() {
	var template = $(".entry-template");
	template.find("a.pick-button").click(function() {
		var t
	});
}
