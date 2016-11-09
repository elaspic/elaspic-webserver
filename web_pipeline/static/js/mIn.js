// AutoGrow plugin.
jQuery.fn.autoGrow = function() {
    return this.each(function() {
        var createMirror = function(textarea) {
            jQuery(textarea).after('<div class="autogrow-textarea-mirror"></div>');
            return jQuery(textarea).next('.autogrow-textarea-mirror')[0];
        }
        var sendContentToMirror = function (textarea) {
            mirror.innerHTML = String(textarea.value).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br />') + '.<br/>.';
            if (jQuery(textarea).height() != jQuery(mirror).height())
                jQuery(textarea).height(jQuery(mirror).height());
        }
        var growTextarea = function () {
            sendContentToMirror(this);
        }
        // Create a mirror
        var mirror = createMirror(this);
        mirror.style.display = 'none';
        mirror.style.wordWrap = 'break-word';
        mirror.style.whiteSpace = 'normal';
        mirror.style.padding = jQuery(this).css('padding');
        mirror.style.width = jQuery(this).css('width');
        mirror.style.fontFamily = jQuery(this).css('font-family');
        mirror.style.fontSize = jQuery(this).css('font-size');
        mirror.style.lineHeight = jQuery(this).css('line-height');
        // Style the textarea
        this.style.overflow = "hidden";
        if (this.rows < 5) {
            this.style.minHeight = "7em";
        } else {
            this.style.minHeight = this.rows+"em";
        }
        // Bind the textarea's event
        this.onkeyup = growTextarea;
        // Fire the event for text already present
        sendContentToMirror(this);
    });
};


function handleResults(result, ajaxRequests) {

  $("#validation div").remove();
  var validationArray = [];
  var validated = 0;
  var nothumancount = 0;

  if (!result) {
    var proteins = $("#proteinsinput").val().split("\n");
    for (var i = 0; i < proteins.length; i++) {
      if (proteins[i]) {
        validationArray.push('<div class="validating"></div>');
      } else {
        validationArray.push('<div class="empty"></div>');
      }
    }
  } else {
    for (var i = 0; i < result.r.length; i++) {
      // Line is empty.
      if (result.r[i].emsg == "EMP") {
        validationArray.push('<div class="empty"></div>');
        continue;
      }
      // Syntax error. (0)
      if (result.r[i].emsg == "SNX" || result.r[i].muterr == "SNX") {
        validationArray.push('<div class="error"></div>');
        continue;
      }
      // Protein not found (1) or mutation: out of bounds or wrong residue error. (5)
       if (result.r[i].emsg == "DNE" || result.r[i].muterr == "OOB") {
        validationArray.push('<div class="unknown"></div>');
        continue;
      }
      // Mutation does not fall inside a domain.
       if (result.r[i].emsg == "OOD" || result.r[i].muterr == "OOD") {
        validationArray.push('<div class="unknown"></div>');
        continue;
      }
      // Mutation: self error (2), or line is a duplicate (3) or synonym. (4)
      if (result.r[i].muterr == "SLF" || result.r[i].emsg == "DUP" || result.r[i].emsg == "SYN") {
        validationArray.push('<div class="warning"></div>');
        continue;
      }
      // Line is validated.
      validationArray.push('<div class="good"></div>');
      validated++;

      // Check if protein is human.
      if (result.r[i].nothuman) {
        nothumancount++;
      }
    }

    if (validated || result.e) {

      if (validated) {
        if (validated == 1) {
          var s = '';
          var ve = 's'
        } else {
          var s = 's';
          var ve = 've'
        }
        var validateHtml = "<div><h4>" + validated + " mutation" + s + " ha" + ve + " been correctly input.</h4>" +
                   "<p><b></b><i>To continue, input your email address (optional) and click Submit.</i></p></div>"
        $("#input_resp").html(validateHtml);
        $("#input_resp").show()
        $("#input_err").css('margin-top', '27px');
      } else {
        $("#input_resp").hide();
        $("#input_err").css('margin-top', '0px');
      }

      if (result.e.title) {
        var validateErr = "<div><h4>" + result.e.title + "</h4>";
        for (var i = 0; i < result.e.errors.length; i++) {
          if (result.e.header[i]) {
            validateErr += '<p><span class="ico ' + result.e.eclass[i] + '"></span>' + result.e.header[i]
            validateErr += '<span class="resp">' + result.e.errors[i].join(',&nbsp; ') + "</span></p>";
          }
        }
        validateErr += "</div>";
        $("#input_err").html(validateErr);
        $("#input_err").show()
      } else {
        $("#input_err").hide()
      }

    } else {
      $("#validation").html('<div class="empty"></div>');
      $("#input_resp").hide();
    }

    $("#fakearea").val(result.e.good.join(' '));
  }

  $("#validation").append(validationArray);

  if ($("#proteinsinput").val() == "") {
    $("#input_resp").hide();
    $("#input_err").hide()
  }

  if (ajaxRequests) {
    if (nothumancount) {
      $("#nothumanwarning").animate({height: 50}, {duration: 500});
    } else {
      $("#nothumanwarning").animate({height: 0}, {duration: 300});
    }
  }
}


function getProteins(ajaxRequests) {

    var proteins = $("#proteinsinput").val().split("\n");
    if (ajaxRequests[ajaxRequests.length - 1]) {
        ajaxRequests[ajaxRequests.length - 1].abort();
    }

    // Add loading icons.
    handleResults(false);

    // Check proteins.
    if (proteins != "") {
    ajaxRequests[ajaxRequests.length] = $.ajax({
      url: "/json/getprotein/",
      data: {
        p: proteins.join(" "),
        m: 1,
        e: 1,
      },
      type: "GET",
      dataType: "json",
      cache: false,
      success: function (data) {

        handleResults(data, ajaxRequests);

      }
    });
    }

}
function setSelectionRange(input, selectionStart, selectionEnd) {
    if (input.setSelectionRange) {
        input.focus();
        input.setSelectionRange(selectionStart, selectionEnd);
    } else if (input.createTextRange) {
        var range = input.createTextRange();
        range.collapse(true);
        range.moveEnd('character', selectionEnd);
        range.moveStart('character', selectionStart);
        range.select();
    }
}


$(document).ready(function(){

  var ajaxRequests = new Array();

    if ($("#proteinsinput").val()) {
        getProteins(ajaxRequests);
    } else {
        handleResults(false);
    }

    // Autogrow protein input area.
    $("#proteinsinput").autoGrow();

    $("#pfile").ajaxfileupload({
        "action": "../json/uploadfile/",
        "params": {'filetype': 'prot'},
        "onComplete": function(response) {
            if (typeof response === 'string' || response instanceof String) {
                // Converts text to JSON if needed (Chrome).
                response = $.parseJSON($(response).text());
            }
            // Split file per line and remove spaces.
            if (response.error) {
                $("#uploaderr").show();
                $("#uploaderr").html(response.msg);
            } else {
                // Insert file text.
                $("#proteinsinput").val(response.msg);
                // Adjust input height.
                $("#proteinsinput").trigger( "keyup" );

                // Trigger input validation.
                getProteins(ajaxRequests);
            }
        }
    });

    $("#pfilelabel").click(function() {
        $("#uploaderr").hide();
        $("#pfile").click();
    });


    // Get protein on change.
    $("#proteinsinput").anyChange(function() {

        $("#uploaderr").hide();

        // Remove spaces.
        var allinput = $.map($("#proteinsinput").val().split("\n"), function(str, i) {
            if (i < 10000)
                return str.replace(/\s+/g, "").substring(0,65);
        });

        if (allinput.join("\n").length < $(this).val().length) {
            var currentPosition = this.selectionStart;
        }


        // Print output back if trimmed.
        if (allinput.join("\n").length < $(this).val().length) {
            var currentPosition = this.selectionStart;
            $("#proteinsinput").val(allinput.join("\n"));
            setSelectionRange(this, currentPosition - 1, currentPosition - 1);
        }

        getProteins(ajaxRequests);

    });

    // Example proteins.
    $(".example").click(function() {
        $("#uploaderr").hide();
        var example = ['CCM1.E567Q', 'O00522.E567A', 'KRIT1_HUMAN.E567F',
                       'HLA-DRB1.V209R', 'KRas2.I36M', 'ENSG00000133703.V8R',
                       'P68871.V35D', 'KIAA0145.S66T', '3PPJ.R575F',
                       'Q9Y2L6.G109S', 'EIF4E3.V130A',
                       'ROCK2.S264Y', 'Cx46.R133T'];
        $("#proteinsinput").val( example.join("\n") );
        $("#proteinsinput").trigger( "keyup" );
        getProteins(ajaxRequests);
    });

});
