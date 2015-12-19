function validateMail(addr) {
	if (addr.match(/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:[a-zA-Z]{2,4}|museum)$/)) {
		return true;
	} else {
		return false;
	}
}

function checkContactForm() {

	$('.form-response').hide();
	$('.error').hide();

	var errorMsg;
	var errorArr = [];

	if ($('.fname').val() == '') {
		errorMsg = 'Please fill in your name.';
		errorArr.push( $('.fname')[0] );
	} 
	if ($('.fmail').val() == '') {
		errorMsg = 'Please fill in your email address.';
		errorArr.push( $('.fmail')[0] );
	} 
	if ($('.ftitle').val() == '') {
		errorMsg = 'Please input a subject for your message.';
		errorArr.push( $('.ftitle')[0] );
	} 
	if ($('.fmsg').val() == '') {
		errorMsg = "You didn't write any message!"
		errorArr.push( $('.fmsg')[0] );
	}
	if (!errorMsg) {
		if (!validateMail( $('.fmail').val() )) {
			errorMsg = 'There is something wrong with your email.'
			errorArr.push( $('.fmail')[0] );
		} 
	}
	
	if (errorMsg) {
		var errorDur = 600;
		var errorPause = 1500;
		
		if (errorArr.length > 1) {
			errorMsg = "Please fill in all fields."
		}
		
		$('form#cont .error').text(errorMsg);
		$('form#cont .error').fadeIn({
			duration: errorDur, 
			queue: false,
			complete: function() {
				setTimeout(function () {
					$('form#cont .error').fadeOut({
						duration: errorDur, 
						queue: false,
					});
				}, errorPause);
			}
		});

		$(errorArr).animate({
			borderColor: '#CC0D37',
		}, {
			duration: errorDur,
			queue: false,
			complete: function() {
				setTimeout(function () {
					$(errorArr).animate({
						borderColor: '#EBEBEB'
					}, {
						duration: errorDur,
						queue: false,
					});
				}, errorPause);
			}
		});
		
	} else {	
		submitContactForm();
	}
}

function responseAjax(error, msg) {
	if (error) {
		var $responseElement = $('form#cont .error');
	} else {
		var $responseElement = $('form#cont .form-response');
		$('form#cont input[type="text"], form#cont textarea').val('');
	}
	$('.form-response').stop();
	$('.form-response').fadeOut(200, function(){
		$responseElement.text(msg);
		$responseElement.fadeIn(300);
	});
	
}

function submitContactForm() {

	$('.form-response').text('Sending email..');
	$('.form-response').fadeIn(200);

	$.ajax({
		url: "/json/contactmail/",
		data: {name: $('.fname').val(),
			   from: $('.fmail').val(),
			   topic: $('.ftitle').val(),
			   msg: $('.fmsg').val()},
		type: "POST",
		dataType: "json",
		cache: false,
		success: function (data) {
			responseAjax(data.error, data.response);
		},
		error: function (data) {
			responseAjax(true, 'You message failed. Try again.');
		}
	});
}

$(document).ready(function() {

	$('form#cont').submit(function(event) {
		checkContactForm();
		event.preventDefault();
	});
	
});
