jQuery.fn.verticalCarousel = function() {
	return this.each(function() {
	    var $el = $(this);
		var initialOffset = $el.position().top;
        var intervalSeconds = 5;
        var hiddenChildren = 0;
        var totalChildren = $el.children().length;

        $el.children().clone().appendTo($el);

        function move(){
            var remove = $el.children().eq(hiddenChildren).height();
            var currentOffset = $el.position().top;
            $el.animate({top: currentOffset - remove}, 500, function(){
                hiddenChildren += 1;
                if(hiddenChildren == totalChildren){
                    $el.css('top', initialOffset);
                    hiddenChildren = 0;
                }
            });
        }

        setInterval(move, intervalSeconds * 1000)
	});
}