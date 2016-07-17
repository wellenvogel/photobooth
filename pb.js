/**
 * Created by andreas on 17.07.16.
 */

var nextUrl="/getNext";
var currentUrl=undefined;
var lastCurrent=undefined;

function query(){
    var url=nextUrl+((currentUrl===undefined)?"":"?current="+encodeURI(currentUrl));
    if (currentUrl !== undefined && lastCurrent !== undefined){
        url+="&lastCurrent="+encodeURI(lastCurrent)
    }
    $.ajax({
        url:url,
        success: function(data){
            currentUrl=data.url;
            if (data.current && data.current == data.url) lastCurrent=data.current
            console.log("showing "+data.url);
            $('#img1').attr('src',data.url);
        }
    });
}
$(document).on('ready',function(){
    //http://stackoverflow.com/questions/14425300/scale-image-properly-but-fit-inside-div
    $('img').on('load',function(){
        var css;
        var left=($(this).parent().width()-$(this).width())/2;
        var top=($(this).parent().height()-$(this).height())/2;
        $(this).css({left:left,top:top});
    });
    window.setInterval(function(){
       query();
    },5000);
    query();
});
