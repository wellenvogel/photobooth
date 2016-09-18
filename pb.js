/**
 * Created by andreas on 17.07.16.
 */

var nextUrl="/getNext";
var newestUrl=undefined;
var currentUrl=undefined;
var lastCurrent=undefined;

function query(){
    var url=nextUrl+((newestUrl===undefined)?"":"?newest="+encodeURI(newestUrl));
    if (currentUrl) url+="&current="+encodeURI(currentUrl);
    if (lastCurrent) url+="&lastCurrent="+encodeURI(lastCurrent);
    $.ajax({
        url:url,
        success: function(data){
            currentUrl=data.url;
            if (data.newest) newestUrl=data.newest;
            if (data.current) lastCurrent=data.url;
            console.log("showing "+data.url);
            $('#info').text(data.url.replace( /.*\//,''));
            $('#img1').attr('src',data.url);
        }
    });
}
$(document).on('ready',function(){
    //http://stackoverflow.com/questions/14425300/scale-image-properly-but-fit-inside-div
    $('#img1').on('load',function(){
        var css;
        var left=($(this).parent().width()-$(this).width())/2;
        var top=($(this).parent().height()-$(this).height())/2;
        $(this).css({left:left,top:top});
    });

    window.setInterval(function(){
       query();
    },5000);
    query();
    $('#img1').on('click',function() {
        if ($('#info').is(':visible')){
            $('#info').hide();
            return;
        }
        $('#info').show();
        window.setTimeout(function(){
            $('#info').hide();
        },15000);
    })
});
