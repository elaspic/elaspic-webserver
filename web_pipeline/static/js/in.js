// AnyChange plugin.
(function ($) {
  $.fn.anyChange = function (cb) {
    return this.each(function () {
      if (typeof cb == "function") {
        new AnyChange(this, cb);
      }
    });
  };

  function AnyChange(inputElement, callback) {
    var eventsRemoved = false;
    if (inputElement.addEventListener) {
      inputElement.addEventListener("input", oninput, false); // all browsers except IE before version 9
      inputElement.addEventListener("textInput", textInput, false); // Google Chrome and Safari
      inputElement.addEventListener("textinput", textinput, false); // Internet Explorer from version 9
    } else {
      if (inputElement.attachEvent) {
        inputElement.attachEvent("onpropertychange", propertyChangeEvent); // Internet Explorer and Opera
      }
    }

    function oninput(event) {
      if (eventsRemoved === false) {
        inputElement.removeEventListener("textInput", textInput, false); // Google Chrome and Safari
        inputElement.removeEventListener("textinput", textinput, false); // Internet Explorer from version 9
        eventsRemoved = true;
      }

      callback.call(inputElement, event.target.value);
    }

    function textInput(event) {
      if (eventsRemoved === false) {
        inputElement.addEventListener("input", oninput, false); // all browsers except IE before version 9
        inputElement.addEventListener("textinput", textinput, false); // Internet Explorer from version 9
        eventsRemoved = true;
      }

      callback.call(inputElement, event.data);
    }

    function textinput(event) {
      if (eventsRemoved === false) {
        inputElement.addEventListener("input", oninput, false); // all browsers except IE before version 9
        inputElement.addEventListener("textInput", textInput, false); // Google Chrome and Safari
        eventsRemoved = true;
      }

      callback.call(inputElement, event.data);
    }

    function propertyChangeEvent(event) {
      if (event.propertyName.toLowerCase() == "value") {
        callback.call(inputElement, event.srcElement.value);
      }
    }
  }
})(jQuery);

function validate(m, s) {
  // Is valid substitution.
  if (/^[ACDEFGHIKLMNPQRSTVWY]{1}[1-9]{1}[0-9]*[ACDEFGHIKLMNPQRSTVWY]{1}$/.test(m.toUpperCase())) {
    // Mutation is in sequence length.
    if (parseInt(m.substr(1, m.length - 1)) <= s.length) {
      // Does not substitute with original.
      if (m.charAt(0) != m.charAt(m.length - 1)) {
        // Original is in sequence at right spot.
        if (m.charAt(0).toUpperCase() == s.charAt(parseInt(m.substr(1, m.length - 1)) - 1)) {
          return "sub";
        }
      }
    }
  } else {
    return "";
  }
}

function validateForm() {
  var noError = true;
  if ($("#fakearea").val() === "") {
    noError = false;
    if ($("#me").val() == "sIn") {
      if (!$("#selectbox").width()) {
        // No protein
        $("#submiterr").text("Please input a valid protein and select a mutation");
      } else {
        //. No mutation selected
        $("#submiterr").text("Please select a valid mutation");
      }
    } else if ($("#me").val() == "mIn") {
      $("#submiterr").text("Please input at least one protein with a valid mutation");
    }
  } else if ($("#notdomainwarning").is(":visible")) {
    // Selected mutation outside domain
    noError = false;
    $("#submiterr").text("Mutation must fall inside a domain");
  }
  if (noError) {
    if ($("#emailtext").val()) {
      if (
        !$("#emailtext")
          .val()
          .match(/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:[a-zA-Z]{2,4}|museum)$/)
      ) {
        noError = false;
        $("#submiterr").text("Please input a valid or no email address");
      }
    }
  }
  if (noError === false) {
    $("#submiterr").fadeIn("slow", function () {
      setTimeout(function () {
        $("#submiterr").fadeOut("slow");
      }, 2000);
    });
  }
  return noError;
}
