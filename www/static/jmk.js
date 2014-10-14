function slugify(str) {
	var unsafe = /[ \t$&+,:;=?@!\t"<>#%{}|\\^~\[\]`]/;
	var tokens = str.split(unsafe).filter(Boolean);
	return tokens.join("-");
}
function open_overlay() {
	$( '<div id="imagelightbox-overlay"></div>' ).appendTo( 'body' );
}
function close_overlay() {
	$('#imagelightbox-overlay').hide('fast', function() {
		$(this).remove();
	});
}
$(function() {
	
	$(".page-navigation").click(function() {
		document.location = $(this).attr("target");
	});
	$(".page-selector").change(function() {
		document.location = $(this).val();
	});
	$(".nested-comment").click(function() {
		$("#" + $(this).attr("target")).toggle('fast');
	});
	
	function update_height() {
		if($(this).hasClass("fixed-size")) return;
		$(this).height( 0 );
		var sh = this.scrollHeight;
		if(sh > 300) sh = 300;
		if(sh < 50) sh = 50;
		$(this).height( sh );
	}
	$("textarea").each(update_height);
	$("textarea").bind('input propertychange', update_height);
	$(".confirm").click(function() {
		return confirm("Proceed?");
	});
	function open_caption(target) {
		var note_id = target.find('img').data("note-id");
		console.log('note_id', note_id);
		var html = $("#" + note_id).html();
		console.log('html', html);
		if(html.length > 0) {
			console.log('append');
			$('<div id="imagelightbox-caption"><div class="inner"><div class="wrapper">' + html + '</div></div></div>').appendTo( 'body' );
			align_caption();
		}
	}
	function align_caption() {
		var caption = $("imagelightbox-caption");
		if(caption) {
			var img = $("#imagelightbox");
			$("#imagelightbox-caption").css({
				'left': img.css('left'), 
				'top': img.css('top'), 
				'width': img.css('width'),
				'height': img.css('height'), 
			});
		}
	}
	$(window).on( 'resize', align_caption );
	function close_caption(img) {
			$("#imagelightbox-caption").remove();
	}
	$(".lightbox-link").imageLightbox({
		quitOnImgClick: true,
		quitOnEnd: true,
		animationSpeed: 100,
		onStart: open_overlay,
		onEnd: close_overlay,
	});
	$(".lightbox-caption-link").imageLightbox({
		quitOnImgClick: true,
		quitOnEnd: true,
		animationSpeed: 100,
		onStart: open_overlay,
		onEnd: function() { close_overlay(); close_caption(); },
		onLoadStart: close_caption,
		onLoadEnd: open_caption
	});

	$("#gallery-trigger").click(function() {
		open_gallery(); 
		return false;
	});


});
