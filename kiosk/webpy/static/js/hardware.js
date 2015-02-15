var potPin = 0;

//Control an output pin on the GPIO
function controlOutput(pin,val){
	$.get('/outputControl/?pin='+pin+'&val='+val)
}

//Control the blink speed of a blinking light
function controlBlink(pin,sec){
	$.get('/blinkControl/?pin='+pin+'&sec='+sec)
}

//Control an output pin on the Alamode
function controlAMOutput(pin,val){
	$.get('/alamodeControl/digitalWrite/?pin='+pin+'&val='+val)
}

//Read an analog input from the Alamode into element with given id
function readAMAnalogInput(pin,id){
	$.get('/alamodeControl/analogRead/?pin='+pin, function(data) {
  		$(id).text(data);
	});
}

//Function to get continuous readings from the potentiometer
$(function() {
    var timer = null, interval = 500;

    $("#startPot").click(function() {
      if (timer !== null) return;
      timer = setInterval(function () {
          $.get('/alamodeControl/analogRead/?pin='+potPin, function(data) {
  				$("#potDisp").text(data);
			});
      }, interval); 
    });

    $("#stopPot").click(function() {
    	$("#potDisp").text('---');
      	clearInterval(timer);
      	timer = null;
    });
});