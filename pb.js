/**
 * Created by andreas on 17.07.16.
 */

var nextUrl="/getNext";
var newestUrl=undefined;
var currentUrl=undefined;
var lastCurrent=undefined;
var lastQuery=new Date();

function query(){
    var url=nextUrl+((newestUrl===undefined)?"":"?newest="+encodeURI(newestUrl));
    if (currentUrl) url+="&current="+encodeURI(currentUrl);
    if (lastCurrent) url+="&lastCurrent="+encodeURI(lastCurrent);
    lastQuery=new Date();
    $.ajax({
        url:url,
        success: function(data){
            currentUrl=data.url;
            if (data.newest) newestUrl=data.newest;
            if (data.current) lastCurrent=data.url;
            console.log("showing "+data.url);
            $('#img1').attr('src',data.url);
        },
        error: function(){
            window.setTimeout(query,timeTillQuery());
        }
    });
}

function timeTillQuery(){
    var now=new Date();
    var rt=lastQuery.getTime()+5000-now.getTime();
    if (rt <=0) rt=100;
    return rt;
}
$(document).on('ready',function(){
    //http://stackoverflow.com/questions/14425300/scale-image-properly-but-fit-inside-div
    $('#img1').on('load',function(){
        var css;
        var left=($(this).parent().width()-$(this).width())/2;
        var top=($(this).parent().height()-$(this).height())/2;
        $(this).css({left:left,top:top});
        $('#info').text($(this).attr('src').replace( /.*\//,''));
        window.setTimeout(query,timeTillQuery());
    });
    $('#img1').on('error',function(){
        window.setTimeout(query,timeTillQuery());
    });
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
