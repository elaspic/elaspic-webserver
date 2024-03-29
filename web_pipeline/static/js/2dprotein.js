function rainbow(numOfSteps, step) {
  // This function generates vibrant, "evenly spaced" colours (i.e. no clustering). This is ideal for creating easily distinguishable vibrant markers in Google Maps and other apps.
  // Adam Cole, 2011-Sept-14
  // HSV to RBG adapted from: http://mjijackson.com/2008/02/rgb-to-hsl-and-rgb-to-hsv-color-model-conversion-algorithms-in-javascript
  var r, g, b;
  var h = step / numOfSteps;
  var i = ~~(h * 6);
  var f = h * 6 - i;
  var q = 1 - f;
  switch (i % 6) {
    case 0:
      r = 1;
      g = f;
      b = 0;
      break;
    case 1:
      r = q;
      g = 1;
      b = 0;
      break;
    case 2:
      r = 0;
      g = 1;
      b = f;
      break;
    case 3:
      r = 0;
      g = q;
      b = 1;
      break;
    case 4:
      r = f;
      g = 0;
      b = 1;
      break;
    case 5:
      r = 1;
      g = 0;
      b = q;
      break;
  }
  var c =
    "#" +
    ("00" + (~~(r * 255)).toString(16)).slice(-2) +
    ("00" + (~~(g * 255)).toString(16)).slice(-2) +
    ("00" + (~~(b * 255)).toString(16)).slice(-2);
  return c;
}

function blue_rainbow(numOfSteps, step) {
  var switches = 4;
  var r, g, b;
  var h = step / numOfSteps;
  var i = ~~(h * switches);
  var f = h * switches - i;
  var q = 1 - f;
  switch (i % switches) {
    case 0:
      r = f * 0.6 + 0.2;
      g = 0.2;
      b = 1;
      break;
    case 1:
      r = 0.8;
      g = f * 0.6 + 0.2;
      b = 1;
      break;
    case 2:
      r = q * 0.6 + 0.2;
      g = 0.8;
      b = 1;
      break;
    case 3:
      r = f * 0.8;
      g = 0.8;
      b = q * 0.8 + 0.2;
      break;
  }
  var c =
    "#" +
    ("00" + (~~(r * 255)).toString(16)).slice(-2) +
    ("00" + (~~(g * 255)).toString(16)).slice(-2) +
    ("00" + (~~(b * 255)).toString(16)).slice(-2);
  return c;
}

var barSize = 868;
var mutDescSize = 70;
var mutLineSize = 2;

function create2dBar(protein) {
  $(".protein2d .domain").remove();
  $(".protein2d .domain-bg").remove();
  $(".dominacs div").remove();

  var border = 1;

  var psize = protein.seq.length;

  $(".protein2d .enddesc").text(psize);

  // Draw domains
  var domaindefs = [];
  var i;
  var pxsize, pxstart;
  for (i = 0; i < protein.doms.length; i++) {
    var domStart = parseInt(protein.defs[i].split(":")[0]);
    var domEnd = parseInt(protein.defs[i].split(":")[1]);
    domaindefs.push([domStart, domEnd]);

    pxsize = ((domEnd - domStart) / psize) * barSize;
    pxstart = (domStart / psize) * barSize - border;

    var dname, dpopup;

    if (protein.doms[i].length * 7 < pxsize) {
      dname = protein.doms[i];
      dpopup = "";
    } else if (14 < pxsize) {
      dname = protein.doms[i].substring(0, Math.max(parseInt(pxsize / 7) - 2, 0)) + "..";
      dpopup = protein.doms[i];
    } else {
      dname = "";
      dpopup = protein.doms[i];
    }

    var divtitle = thisPage == "sIn" ? "" : 'title="Click to open Pfam description." ';

    var style = ' style="width: ' + pxsize + "px; left: " + pxstart + 'px;"';
    var data =
      ' data-start="' + domStart + '" data-end="' + domEnd + '" data-text="' + dpopup + '"';

    var domain =
      "<div " + divtitle + 'class="domain popup"' + style + data + ">" + dname + "</div>";
    domain += '<div class="domain-bg"' + style + data + "></div>";

    $(".protein2d").append(domain);
  }

  // Draw interactions.
  if (protein.inacs) {
    var protCount = protein.inacs.length;
    for (var j = 0; j < protCount; j++) {
      var color = blue_rainbow(protCount, j);
      for (i = 0; i < protein.inacs[j].aa.length; i++) {
        var aa = protein.inacs[j].aa[i];
        // Hide interfaces outside domains.
        var in_domain = false;
        for (var k = 0; k < domaindefs.length; k++) {
          if (aa >= domaindefs[k][0] && aa <= domaindefs[k][1]) {
            in_domain = true;
            break;
          }
        }
        if (!in_domain) {
          continue;
        }
        pxsize = (1 / psize) * barSize;
        var center1px = (pxsize - 1) / 2;
        pxstart = (aa / psize) * barSize - center1px - 0.5;
        var height = Math.min(38 / protCount, 10);
        var top = j * height;
        var inac = '<div style="width:' + pxsize + "px; left:" + pxstart + "px;";
        inac += "height: " + height + "px; background-color: " + color + ";";
        inac += "top: " + (36 + top) + 'px;" class="aa' + aa + '"';
        inac +=
          ' data-pid="' +
          protein.inacs[j].pid +
          '" data-prot="' +
          protein.inacs[j].prot +
          '"></div>';
        $(".dominacs").append(inac);
      }
    }
  }

  $(".popup").hover(
    function () {
      showHover(this);
      $(".tooltip2d").show();
    },
    function () {
      $(".tooltip2d").hide();
    }
  );

  if (thisPage == "sIn") {
    $(".domain, .dombar, .domclick").unbind("click");
    $(".domain, .dombar, .domclick").click(function (e) {
      var seqsize = parseInt($(".enddesc").text());
      var mutnum = Math.round(((e.pageX - $(".protein2d").offset().left) / barSize) * seqsize);
      mutnum = Math.max(Math.min(mutnum, seqsize), 1);
      setBarMut(mutnum);
    });
  } else {
    $(".domain").unbind("click");
    $(".domain").click(function () {
      linkPfam($(this));
    });
  }
  fixBarMut();
}

function setBarMut(num) {
  var oldMut = $("#select2sub").find("option:selected").text();
  $("#selectsub").val("sel" + num);
  fixSelLink();
  if ($("#yourSelect option[value='" + oldMut + "']").length > 0) {
    $("#select2sub").val(oldMut);
  }
  fixBarMut();
  saveMut();
}

function fixBarMut() {
  var aa = $("#selectsub").find("option:selected").text().substring(0, 1);
  var num = $("#selectsub").find("option:selected").text().substring(1);
  // Draw mutation.
  if (aa != "-") {
    var pxMutnum = (parseInt(num) / parseInt($(".enddesc").text())) * barSize - mutLineSize / 2;
    var pxmutdesc = pxMutnum - mutDescSize / 2 + mutLineSize / 2;
    $(".barmutation").css("left", pxMutnum + "px");
    $(".barmutdesc").css("left", pxmutdesc + "px");
    $(".barmutdesc").text(aa + num + $("#select2sub").find("option:selected").text());
    $(".barmutation").show();
    $(".barmutdesc").show();
  } else {
    $(".barmutation").hide();
    $(".barmutdesc").hide();
  }

  // Highlight domain if mutation is in it.
  var inDomain = false;
  $(".protein2d")
    .children(".domain-bg")
    .each(function () {
      var start = $(this).attr("data-start");
      var end = $(this).attr("data-end");
      if (num >= parseInt(start) && num <= parseInt(end)) {
        $(this).addClass("current");
        inDomain = true;
      } else {
        $(this).removeClass("current");
      }
    });

  // Display not-in-domain warning message.
  if (inDomain || aa == "-" || $("#barbox").data("data-pdb")) {
    $("#notdomainwarning").hide();
  } else {
    $("#notdomainwarning").show();
  }

  // Summarize affected protein interactions.
  $(".inacsummary div").remove();

  var inac;
  var $inacs = $(".protein2d .aa" + num);

  var columns = 2;

  var steps = Math.ceil($inacs.length / 2);

  // This adds protein interaction data
  function _loopFunction() {
    if (count % steps === i) {
      inac =
        '<div><div class="inaccolor" style="background-color:' +
        $(this).css("background-color") +
        ';"></div>';
      inac +=
        '<a class="click2" target="_blank" href="http://www.uniprot.org/uniprot/' +
        $(this).attr("data-pid") +
        '">' +
        $(this).attr("data-prot") +
        "</a></div>";
      $(".inacsummary").append(inac);
    }
    count += 1;
  }

  for (var i = 0; i < steps; i++) {
    var count = 0;
    $inacs.each(_loopFunction);
  }
  if (inac) {
    $("#inacbox").show();
    $("#inacbox").css("height", Math.min(40 + steps * 20, 140) + "px");
    $("#inacbox .inacsummary").css("height", Math.min(10 + steps * 20, 110) + "px");
  } else {
    $("#inacbox").hide();
  }
}

function getY(i, svgdata) {
  var h = 100;
  var distanceisno = 20;
  var noleft =
    svgdata[i - 1] === undefined || svgdata[i - 1].x + distanceisno < svgdata[i].x ? true : false;
  var noright =
    svgdata[i + 1] === undefined || svgdata[i + 1].x - distanceisno > svgdata[i].x ? true : false;
  if ((noright && noleft) || svgdata.length < 5) {
    return 1;
  } else if (svgdata.length < 10) {
    return i % 2 ? 20 : 1;
  } else if (svgdata.length < 30) {
    return i % 3 ? (i % 2 ? 20 : 50) : 1;
  } else {
    return (i % Math.floor(svgdata.length / 10)) * 40;
  }
}

var lastMutTooltip;

function fixBarMuts(muts) {
  $(".barmutations").html("");
  $(".protsvg").html("");

  var svg = d3.select(".protsvg");
  var i;
  var n = 100;
  var w = 920,
    h = 100,
    svgHeight = 0,
    posLeft = -25,
    labelBox,
    links;

  var svgdata = [];

  for (var key in muts) {
    // Add vertical line.
    var pxMutnum = (parseInt(key) / parseInt($(".enddesc").text())) * barSize - mutLineSize / 2;
    $(".barmutations").append('<div class="line"></div>');
    $(".barmutations .line").last().css("left", pxMutnum);
    // Add to data array to be drawn.
    svgdata.push({
      x: pxMutnum - posLeft + 1,
      y: 100,
      text: muts[key][0][0]["m"],
      data: muts[key],
    });
    // console.log(key);
    // console.log(muts[key][0][0]['m']);
  }

  for (i = 0; i < svgdata.length; i++) {
    svgdata[i].y = getY(i, svgdata);
  }

  svgdata.sort(function (a) {
    return -a.x;
  });

  function draw() {
    labelBox.attr("transform", function (d) {
      return (
        "translate(" +
        Math.min(Math.max(20, d.labelPos.x), w - 20) +
        " " +
        Math.max(Math.min(d.labelPos.y - 5, svgHeight - 10), 5) +
        ")"
      );
    });
    links
      .attr("x1", function (d) {
        return d.anchorPos.x;
      })
      .attr("y1", function (d) {
        return d.anchorPos.y;
      })
      .attr("x2", function (d) {
        return Math.min(Math.max(20, d.labelPos.x), w - 20);
      })
      .attr("y2", function (d) {
        return Math.max(Math.min(d.labelPos.y - 5, svgHeight - 10), 5);
      });
  }
  var pgravity = 0.05;
  var labelForce = d3
    .force_labels()
    .linkDistance(function (d, i) {
      if (svgdata.length < 5) {
        svgHeight = Math.max(svgHeight, (h * 4) / 10);
        pgravity = 0.02;
      } else if (svgdata.length < 10) {
        svgHeight = Math.max(svgHeight, (h * 7) / 10);
        pgravity = 0.02;
      } else if (svgdata.length < 30) {
        pgravity = 0.03;
        svgHeight = Math.max(svgHeight, (h * 10) / 10);
      } else {
        svgHeight = Math.max(svgHeight, h * (svgdata.length / 20));
      }
      return getY(i, svgdata);
    })
    .size([w, 1000])
    .gravity(0.05)
    .nodes([])
    .links([])
    .charge(-70);
  console.log("Drawn " + svgdata.length + " mutations.");

  var anchors = svg.selectAll(".anchor").data(svgdata);
  var labels = svg.selectAll(".labels").data(svgdata);

  // Draw new nodes.
  anchors.enter().append("circle").attr("class", "anchor").attr("r", 1);
  var newLabels = labels.enter().append("g").attr("class", "labels");
  labelBox = newLabels.append("g").attr("class", "labelbox");
  labelBox.append("text").attr("class", "labeltext").attr("y", 10);
  newLabels.append("line").attr("class", "link");
  links = svg.selectAll(".link");

  // Set up attributes.
  anchors
    .attr("cx", function (d) {
      return d.x;
    })
    .attr("cy", 0);
  labelBox.selectAll("text").text(function (d) {
    return d.text;
  });

  // Enable events.
  $(".labelbox").unbind("click");
  $(".labelbox").click(function (e) {
    e.stopPropagation();
    $(".tooltip").hide();
    var tooltip = "tmut";
    var offTop = $(this).offset().top + 25;
    var offLeft = $(this).offset().left - 85;
    $(".muttooltip#" + tooltip)
      .css("top", offTop + "px")
      .css("left", offLeft + "px");
    // Remove old popup data and prepare for new.
    $(".muttooltip .tlabels div").unbind("click");
    $(".muttooltip .tlabels").html("");
    var mutData = d3.select(this).datum().data;
    var manyMuts = mutData.length >= 10 ? true : false;
    if (mutData.length == 1) {
      $(".muttooltip .tlabels").append('<div class="l1"><span class="bg"></span></div>');
    } else if (mutData.length < 10) {
      $(".muttooltip .tlabels").append('<div class="l1"><span class="bg"></span></div>');
    } else {
      $(".muttooltip .tlabels").append(
        '<div class="l1"><span class="bg"></span></div><div class="l2"><span class="bg"></span></div>'
      );
    }
    // Print data to popup.
    $(".muttooltip .tlabels").attr(
      "data-mut",
      mutData[0][0].m.substr(0, mutData[0][0].m.length - 1)
    );
    for (i = 0; i < mutData.length; i++) {
      var extraclass = !i ? "active" : "inactive";
      var curmut = !i ? mutData[i][0].m : mutData[i][0].m.slice(-1);
      var ele = i < 10 ? $(".muttooltip .tlabels .l1") : $(".muttooltip .tlabels .l2");
      ele.append('<div class="' + extraclass + '">' + curmut + "</div>");
    }
    fixMutPopupData(mutData, 0);
    // Enable click on popup.
    $(".muttooltip .tlabels div div").click(function () {
      if (mutData.length > 1) {
        $(".muttooltip .tlabels div .active").text(
          $(".muttooltip .tlabels div .active").text().slice(-1)
        );
        $(".muttooltip .tlabels div div").removeClass();
        $(this)
          .addClass("active")
          .text($(".muttooltip .tlabels").attr("data-mut") + $(this).text());
        var dataNum = $(this).parent().hasClass("l1")
          ? $(this).index() - 1
          : $(this).index() + 10 - 1;
        fixMutPopupData(mutData, dataNum);
        fixMutPopupBorders(manyMuts);
      } else {
        $(".muttooltip").hide();
      }
    });

    // Ensure show if same tooltip.
    if (lastMutTooltip == this) {
      $(".muttooltip#" + tooltip).toggle(0);
    } else {
      $(".muttooltip#" + tooltip).show(0);
    }
    lastMutTooltip = this;

    // Fix borders in popup.
    fixMutPopupBorders(manyMuts);
  });

  anchors.call(labelForce.update);

  labelForce.start();
  for (i = 10000; i > 0; --i) labelForce.tick();
  labelForce.stop();

  $(".protsvg").css("height", svgHeight + "px");
  $("#nothumanwarning").css("top", Math.max(svgHeight - 20, 0) + 260 + "px");
  draw();

  return Math.max(svgHeight - 20, 0);
}

function fixMutPopupData(data, num) {
  for (var i = 0; i < data[num].length; i++) {
    // Set variables.
    var head = data[num][i].i
      ? 'Interaction with: <a class="click2" target="_blank" href="http://www.uniprot.org/uniprot/' +
        data[num][i].id +
        '">' +
        data[num][i].i +
        "</a>"
      : "Stability results";
    var sbddg = data[num][0].d,
      el2_score = data[num][0].el2_score,
      sbmutdb = data[num][0].db,
      sbdgwt = data[num][0].dw,
      sbdgmut = data[num][0].dm,
      sbseq = data[num][0].si,
      sbdop = data[num][0].sm,
      // elaspic_version = data[num][0].elaspic_version,
      muttsid = 'Seq iden<span id="sbseq" class="mono">' + data[num][0].si + "</span>";
    if (sbseq.split(", ").length > 1) {
      sbseq = data[num][0].si.split(", ");
      sbseq = sbseq[0] + '<span class="nonmono">, </span>' + sbseq[1];
      muttsid = 'Seq idens<span id="sbseq" class="mono">' + sbseq + "</span>";
    }
    // Write scaffold.
    $(".muttooltip .ttext #mutthead").html(head);
    $(".muttooltip .ttext #muttsid").html(muttsid);
    $(".muttooltip .ttext #sbdop").html(sbdop);
    $(".muttooltip .ttext #sbdgwt").html(sbdgwt);
    $(".muttooltip .ttext #sbdgmut").html(sbdgmut);
    $(".muttooltip .ttext #sbddg").html(sbddg);
    $(".muttooltip .ttext #sbel2").html(el2_score);
    $(".muttooltip .ttext #dbs").html(sbmutdb + ".");
    // $('.muttooltip .ttext a#elaspic').attr("href", "https://gitlab.com/kimlab/elaspic/tags/v" + elaspic_version).html("v" + elaspic_version);
  }
  // Fix paddings for interactions.
  var mwidth = 200;
  var toppadding = 0;
  if (data[num][0].i) {
    toppadding += 15;
    if (data[num].length > 1) {
      mwidth += 15;
    }
  }
  if (data.length == 1) {
    toppadding += 5;
  } else if (data.length < 10) {
    toppadding += 25;
  } else {
    toppadding += 45;
  }
  $(".muttooltip .ttext .head").css("padding-top", toppadding + "px");
  $(".muttooltip").css("width", mwidth + "px");
  //var twidth = mwidth - 10;
  $(".muttooltip .ttext").css("width", mwidth - 10 + "px");
}

function fixMutPopupBorders(two) {
  var bgwidth1 =
    $(".muttooltip .tlabels .l1 div").last().position().left +
    $(".muttooltip .tlabels .l1 div").last().outerWidth() -
    5;
  $(".muttooltip .tlabels .l1 .bg").css("width", bgwidth1 + "px");
  if (two) {
    var bgwidth2 =
      $(".muttooltip .tlabels .l2 div").last().position().left +
      $(".muttooltip .tlabels .l2 div").last().outerWidth() -
      5;
    $(".muttooltip .tlabels .l2 .bg").css("width", bgwidth2 + "px");
  }
}

function showHover(element) {
  var left = parseInt($(element).css("left"));
  var right = parseInt($(element).css("width")) + left;
  var text = $(element).attr("data-text");
  var width = text.length * 7;
  var mid = parseInt((left + right) / 2 - width / 2) - 5;

  // Check if arrow should be placed.
  var arrow;
  if (width) {
    arrow = '<div class="arrow" style="margin-left: ' + parseInt(width / 2 - 4 + 5) + 'px;"></div>';
  } else {
    arrow = "";
  }

  right += 2;

  // Replace domain definitions if domain is too small.
  var domWidth = parseInt($(element).css("width"));
  var defWidth = $(element).attr("data-end").toString().length * 7;
  if (domWidth < defWidth) {
    left -= 30;
  } else {
    left -= 15;
    right -= 15;
  }
  var barid;
  if ($(element).attr("data-bar")) {
    barid = "#bar" + $(element).attr("data-bar") + " ";
  } else {
    barid = "";
  }
  $(barid + ".tooltip2d").html(
    '<div class="ttmid" style="left: ' +
      mid +
      "px; width: " +
      width +
      'px;"><div class="txt">' +
      text +
      "</div>" +
      arrow +
      "</div>" +
      '<div class="ttstart" style="left: ' +
      left +
      'px;">' +
      $(element).attr("data-start") +
      "</div>" +
      '<div class="ttend" style="left: ' +
      right +
      'px;">' +
      $(element).attr("data-end") +
      "</div>"
  );
  if (width) {
    $(barid + ".ttmid .txt").css("padding", "3px 5px");
  } else {
    $(barid + ".ttmid .txt").css("padding", "0px");
  }
  if (domWidth < defWidth) {
    $(barid + ".ttstart").css("text-align", "right");
    $(barid + ".ttend").css("text-align", "left");
  } else {
    $(barid + ".ttstart").css("text-align", "center");
    $(barid + ".ttend").css("text-align", "center");
  }
}

function linkPfam(domain) {
  var families = domain.attr("data-text");
  if (families.length < 1) {
    families = domain.html().trim();
  }
  families = families.split("+");
  var uniqueFams = [];
  for (var i = 0; i < families.length; ++i) {
    var u = true;
    for (var j = 0; j < uniqueFams.length; ++j) {
      if (families[i] == uniqueFams[j]) {
        u = false;
        break;
      }
    }
    if (u) {
      uniqueFams.push(families[i]);
      window.open("http://pfam.xfam.org/family/" + families[i]);
    }
  }
}
