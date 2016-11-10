// ExtraBox plugin.
(function($) {
  // Create ExtraBox object
  function ExtraBox(el, options) {
    // Default options for the plugin (configurable)
    this.defaults = {
      attribute: 'class'
    };
    // Combine default and options objects
    this.opts = $.extend({}, this.defaults, options);
    // Non-configurable variables
    this.$el = $(el);
    this.items = new Array();
  }

  // Separate functionality from object creation
  ExtraBox.prototype = {

    init: function() {
      var _this = this;
      $('option', this.$el).each(function(i, obj) {
        var $el = $(obj);
        $el.data('status', 'enabled');
        _this.items.push({
          attribute: $el.attr(_this.opts.attribute),
          $el: $el
        });
      });
    },
    disable: function(key) {
      $.each(this.items, function(i, item) {
        if (item.attribute == key) {
          item.$el.remove();
          item.$el.data('status', 'disabled');
        }
      });
    },
    enable: function(key) {
      var _this = this;
      $.each(this.items, function(i, item) {
        if (item.attribute == key) {

          var t = i + 1;
          while (true) {
            if (t < _this.items.length) {
              if (_this.items[t].$el.data('status') == 'enabled') {
                _this.items[t].$el.before(item.$el);
                item.$el.data('status', 'enabled');
                break;
              } else {
                t++;
              }
            } else {
              _this.$el.append(item.$el);
              item.$el.data('status', 'enabled');
              break;
            }
          }
        }
      });
    }
  };
  // The actual plugin - make sure to test
  // that the element actually exists.
  $.fn.extraBox = function(options) {
    if (this.length) {
      this.each(function() {
        var rev = new ExtraBox(this, options);
        rev.init();
        $(this).data('extraBox', rev);
      });
    }
  };
})(jQuery);

function saveMut(startup) {
  var protein = $("#proteininput").val();
  var aa1 = $("#selectsub").find("option:selected").text();
  var aa2 = $("#select2sub").find("option:selected").text();

  if (aa1 == '-' || startup) {
    $("#fakearea").val("");
    $("#selectbox .boxhead").fadeTo(500, 1);
  } else {
    $("#fakearea").val(protein + '.' + aa1 + aa2);
    $("#selectbox .boxhead").fadeTo(500, 0);
  }
}

function fixSelLink() {

  var n = 5

  var aa = $("#selectsub").find("option:selected").text().substring(0, 1);
  if ($("#select2sub").data("hidden")) {
    $("#select2sub").data("extraBox").enable($("#select2sub").data("hidden"));
  }
  $("#select2sub").data("extraBox").disable(aa);
  $("#select2sub").data("hidden", aa);

  if (aa != "-") {
    $('#select2sub').prop('disabled', false);
    $('#select2sub').removeClass('cursornormal');

  } else {
    $('#select2sub').prop('disabled', 'disabled');
    $('#select2sub').addClass('cursornormal');
  }

}

function fixSelects(seq) {

  // Print primary selects.
  var i = 0;
  $(".allaa option").remove();
  var options = jQuery.map((seq).split(""), function(n) {
    i++;
    return '<option value="sel' + i + '">' + n + i + '</option>';
  });

  options.unshift('<option value="sel0">-</option>');

  $(".allaa").append(options.join(""));
  stri = seq.length + "";
  $(".allaa").css("width", stri.length * 9 + 40);
  $(".fewaa").css("width", stri.length * 9 + 40);
  $("#select2sub").css("width", 47);

  $("#fakearea").val("");
  fixSelLink();

}

function proteinReceived(result) {

  // Get protein name from inpit field.
  if (result.inputfile) {
    var protName = $("#proteininput").val();
    protName = protName.substring(6, protName.length - 1);
    result.prot = protName;
    result.desc = 'chain ' + result.msg[0][0];
    result.seq = result.msg[0][1];
    result.known = {};
    result.doms = [];
    result.defs = [];
    result.inacs = [];
    $('#barbox').data('data-pdb', result.msg);
    $('#jid').val(result.userpath);
    $('#selectchaindiv').show();
    $('#chain').val(0);
    $('.first-switch').removeClass('first');
    for (var i = 0; i < result.msg.length; i++) {
      var chain = result.msg[i][0];
      $('#selectchain').append('<option value="' + i + '" id="' + chain + '">chain ' + chain + '</option>');
    }
  } else {
    var protName = $.trim($("#proteininput").val()).toUpperCase();
    $('#barbox').data('data-pdb', false);
    $('#selectchaindiv').hide();
    $('.first-switch').addClass('first');
  }

  // Print protein name and description.
  $(".proteininfo .proteinname").text(protName);
  var protID = (protName != result.prot) ? ' (<span class="mono">' + result.prot + '</span>)' : '';
  $(".proteininfo .proteinid").html(protID);
  $(".proteininfo .desc").text(result.desc);

  fixSelects(result.seq);

  $("#pwheel").removeClass("wheelon");

  $("#proteininput").stop();
  $("#selectbox").stop();
  $("#selectbox .boxhead").stop();

  // Show select box.
  $("#inputbox .boxhead").fadeTo(500, 0);
  $("#selectbox .boxhead").css('opacity', 1);
  $("#inputbox .boxhead .proteinname").removeClass('example');
  create2dBar(result);
  var svgHeight = fixBarMuts(result.known);
  $("#proteininput").animate({
    backgroundColor: '#C5E7F9',
    color: '#317CB5',
    borderTopRightRadius: 0,
    borderBottomRightRadius: 0,
  }, {
    duration: 500,
    queue: false,
    complete: function() {
      $("#selectbox").animate({
        width: 300,
      }, {
        duration: 500,
        queue: false,
      });
      if (result.nothuman) {
        var pheight = 305;
        $("#nothumanwarning").show(0);
      } else {
        var pheight = 250;
        $("#nothumanwarning").hide(0);
      }
      $("#protein").animate({
        height: pheight + svgHeight
      }, {
        duration: 300
      });
    }
  });
}

function stopFetch(ajaxRequests) {

  $("#uploaderr").hide();
  $("#protein").animate({
    height: 120
  }, {
    duration: 500
  });
  $("#inputbox .boxhead .proteinname").addClass('example');
  $("#selectbox").animate({
    width: 0,
  }, {
    duration: 500,
    queue: false,
    complete: function() {
      $("#proteininput").animate({
        backgroundColor: '#fff',
        color: '#444',
        borderTopRightRadius: 5,
        borderBottomRightRadius: 5,
      }, {
        duration: 500,
        queue: false
      });
      $("#inputbox .boxhead").fadeTo(500, 1);
      $("#nothumanwarning").hide(0);
    }
  });

  $("#pwheel").text("");
  $("#pwheel").removeClass("wheelerr");
  $("#pwheel").removeClass("wheelon");
  $('#selectchain option').remove();
  $('#inacbox').hide();

  if (ajaxRequests[ajaxRequests.length - 1]) {
    ajaxRequests[ajaxRequests.length - 1].abort();
  }

}


function getProtein(protein, ajaxRequests) {


  stopFetch(ajaxRequests);

  var trimmedProtein = $.trim(protein);

  if (trimmedProtein != "" && trimmedProtein.substring(0, 6) != '<file=') {
    $("#pwheel").addClass("wheelon");

    ajaxRequests[ajaxRequests.length] = $.ajax({
      url: "/json/getprotein/",
      data: {
        p: trimmedProtein,
        n: 1,
        s: 1,
        d: 1,
        k: 1,
      },
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(data) {
        if (data.r[0].error) {
          $("#pwheel").text("Symbol not recognized.");
          $("#pwheel").removeClass("wheelon");
          $("#pwheel").addClass("wheelerr");
        } else {
          proteinReceived(data.r[0])
        }
      }
    });

  } else {
    $("#error").text("Error: No data entered");
    $("#pwheel").removeClass("wheelon");
  }
}


$(document).ready(function() {

  // Create ajax request array.
  var ajaxRequests = new Array();

  // Set proteininput previous data if applicable.
  if ($("#proteininput").val()) {
    $("#proteininput").attr("data-prev", $("#proteininput").val());
  }
  saveMut(true);

  // Get protein if saved with browser.
  if ($("#proteininput").val() != "") {
    getProtein($("#proteininput").val(), ajaxRequests);
  }

  // Get protein on change.
  $("#proteininput").anyChange(function() {
    $('#chain').val("");
    $("#fakearea").val("");
    var newMut = $.trim($("#proteininput").val());
    $("#proteininput").val(newMut);
    if (newMut != $("#proteininput").attr("data-prev")) {
      $("#proteininput").attr("data-prev", newMut);
      getProtein(newMut, ajaxRequests);
    }
  });

  $("#pfile").ajaxfileupload({
    "action": "../json/uploadfile/",
    "params": {
      'filetype': 'pdb'
    },
    "onStart": function() {
      stopFetch(ajaxRequests);
    },
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
        $('#proteininput').val('<file=' + response.inputfile + '>');
        proteinReceived(response);
      }
    }
  });

  $("#pfilelabel").click(function() {
    $("#uploaderr").hide();
    $("#pfile").click();
  });

  // Example proteins.
  $(".example").click(function() {
    $("#proteininput").val($(".example").html());
    getProtein($("#proteininput").val(), ajaxRequests);
  });

  // Make extraBox plugin possible.
  $("#select2sub").extraBox({
    attribute: "id"
  });

  // Update sequence on change.
  $("select").bind("keyup", function() {
    $(this).change();
  });
  $('#selectchain').change(function() {
    var chainid = $(this).find("option:selected").val();
    obj = {
      known: {},
      doms: [],
      defs: [],
      inacs: []
    };

    obj.seq = $('#barbox').data('data-pdb')[chainid][1];

    $(".proteininfo .desc").text($(this).find("option:selected").text());

    fixSelects(obj.seq);

    create2dBar(obj);

    $("#fakearea").val("");
    $('#chain').val(chainid);

  });
  $(".allaa").change(function() {
    fixSelLink();
    fixBarMut();
    saveMut();
  });
  $(".fewaa").change(function() {
    fixBarMut();
    saveMut();
  });

  // Tooltips.
  $(document).click(function() {
    $('.tooltip, .muttooltip').hide();
  });
  $('.tclose').click(function() {
    var tooltip = 't' + $(this).attr('id').substr(2);
    $('.tooltip#' + tooltip).hide();
  });
  $('.tooltip, .muttooltip').click(function(e) {
    e.stopPropagation();
  });
  var lastHelp;
  $('.help').click(function(e) {
    e.stopPropagation();
    var tooltip = 't' + $(this).attr('class').split(' ')[1];
    if (!$(this).hasClass('dgwtf')) {
      $('.muttooltip').hide();
      var offTop = $(this).offset().top - $('.tooltip#' + tooltip).height() - 14;
      var offLeft = $(this).offset().left - 156;
    } else {
      var offTop = $(this).offset().top - 10;
      var offLeft = $(this).offset().left + 30;
    }

    $('.tooltip#' + tooltip).css('top', offTop + 'px').css('left', offLeft + 'px');
    // Ensure show if same tooltip.
    if (lastHelp == this) {
      $('.tooltip#' + tooltip).toggle(0);
    } else {
      $('.tooltip#' + tooltip).show(0);
    }
    lastHelp = this;
  });

});
