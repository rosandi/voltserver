/* 
  Instrumentation apps
  YRAPP
*/

const ww= window.innerWidth;
const wh= window.innerHeight;

var runid;
var running=false;
var msrlen=100;
var avg=10;
var dt=1;
var chn=1;

var pline = [{x: [0],y: [0],type: 'scatter',name: 'V1'}, 
             {x: [0],y: [0],type: 'scatter',name: 'V2'},
             {x: [0],y: [0],type: 'scatter',name: 'V3'},
             {x: [0],y: [0],type: 'scatter',name: 'V4'},
             {x: [0],y: [0],type: 'scatter',name: 'V5'},
             {x: [0],y: [0],type: 'scatter',name: 'V6'}];

plotwidth=0.72*ww;
plotheight=0.8*wh;

var layout = {
  width: plotwidth,
  height: plotheight,
  autosize: false,
  margin: {
    l: 50,
    r: 50,
    b: 50,
    t: 40,
    pad: 4
  },
  yaxis: {range: [-0.1, 0.1],title: 'volt'},
  xaxis: {title: 'time'}
};

var plotdata=[pline[0]];
Plotly.newPlot('plotarea',plotdata,layout);

$.get('dt/1',function(resp){console.log(resp)});
$.get('avg/10',function(resp){console.log(resp)});


function getval(elid) {
    return document.getElementById(elid).value;
}

function setval(elid,val) {
    document.getElementById(elid).value=val;
}

function measure() {
    $.getJSON('isbusy',function(chkdat) {
        if(chkdat.status=='ready') {
            $.getJSON('msr/'+msrlen,function(data) {
                ln=data.lenght;
                nch=data.channels;
                dt=nch*data.msrtime/ln/1000.0; // time in mSec
                
                for(i=0;i<nch;i++) {
                    pline[i].x=[];
                    pline[i].y=[];
                }
                
                var k=0;
                for(i=0;i<ln;i++) {
                    for(j=0;j<nch;j++) {
                        pline[j].x.push(i*dt);
                        pline[j].y.push(data.x[k++]);                        
                    }
                }
                
                plotdata=[]
                for(i=0;i<nch;i++) plotdata.push(pline[i]);
                layout.xaxis= {range:[0,data.msrtime/1000.0], title: 'time (mSec)'}
                Plotly.newPlot('plotarea',plotdata,layout);
            })
        }
    });
}

function togglerun() {
    if(!running) {
      runid=setInterval(measure,500); /* slowdown, don't be too aggresive */
      running=true;
      $('#togglebtn').css({'background-color':'green'});
    }
    else {
        clearInterval(runid);
        running=false;
        $('#togglebtn').css({'background-color':'#555'});

    }
}

nping=0;
function ping() {
    cmd='ping/'+nping++;
    $.getJSON(cmd,function(data){
        setval("responsetext",data.msg);
    }); 
}

function sendcmd() {
    cmd=getval('cmdtext').replace(/ /g,'/');
    console.log(cmd);
    $.get(cmd,function(data){
        $('#longresponse').html(data.replace(/,/g,',<br>'));
    });
}

function apply() {
    msrlen=getval('len');
    avg=getval('avg');
    dt=getval('dt');
    chn=0;
    if(document.getElementById('ch1').checked) chn+=1;
    if(document.getElementById('ch2').checked) chn+=2;
    if(document.getElementById('ch3').checked) chn+=4;
    if(document.getElementById('ch4').checked) chn+=8;
    if(document.getElementById('ch5').checked) chn+=16;
    if(document.getElementById('ch6').checked) chn+=32;
    if(chn==0) {
        chn=1; // avoids nonsense
        document.getElementById('ch1').checked=true;
    }
    
    $.getJSON('avg/'+avg,function(resp){
        s='data length/block: '+msrlen+'<br>';
        s+=resp.msg+'<br>';
        console.log(resp.msg);
    });
    $.getJSON('dt/'+dt,function(resp){
        s+=resp.msg+'<br>';
        console.log(resp.msg);
    });
    $.getJSON('chn/'+chn,function(resp){
        s+=resp.msg;
        console.log(resp.msg);
        $('#longresponse').html(s);
    });
    
}

measure()
