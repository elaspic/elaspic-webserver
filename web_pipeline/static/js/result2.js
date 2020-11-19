function makeInitiationScript(domainID) {
  return (
    'load FILES "' +
    mutPath +
    domainID +
    'wt.pdb" "' +
    mutPath +
    domainID +
    'mut.pdb";' +
    "select all; spacefill off; color label [0,25,72]; set labeloffset -7 0;" +
    'data "property_resno"|end "property_resno"; {*}.property_resno = for(x;{*};x.resno+' +
    resNumDiff +
    "); " +
    "select *" +
    chainself +
    " or *" +
    chaininac +
    "; define ~prot selected; select all and not ~prot; wireframe 0.2; define ~on " +
    defaultShow +
    ";"
  );
}

function jmolisready() {
  $("#appletloading").remove();
  var quality;
  if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    quality = jmolmode == "JAVA" ? "normal" : "worst";
  } else {
    quality = "normal";
  }

  var script = makeInitiationScript(initialdomain);
  script += color(defaultColor);
  script += closeby($("#stickFormRange").val(), true, true);
  script += label("sticks", "model 0");
  script += setMode(quality);
  script += centerAt("mut");

  Jmol.script(jmol1, script);
}

function jmolscript(toRun, arg1, arg2) {
  var script;
  switch (toRun) {
    case "cart":
      script = cartoon(arg1);
      break;
    case "sticks":
      script = sticks(arg1);
      break;
    case "label":
      script = label(arg1, arg2);
      break;
    case "color":
      script = color(arg1);
      break;
    case "model":
      script = showModel(arg1);
      break;
    case "show":
      script = showProtein(arg1);
      break;
    case "center":
      script = centerAt(arg1);
      break;
    case "mode":
      script = setMode(arg1);
      break;
  }
  Jmol.script(jmol1, script);
}

function updateSecondary2dbar(protein, isdimer) {
  // Get domains
  var domainID = protein.substring(1);
  curDomains = domains[domainID];
  curDomainData = domains[domainID + "data"];

  // Switch URL.
  var newUrl = isdimer ? "?p=h" + domainID : "?p=n" + domainID;
  history.pushState("ELASPIC", "ELASPIC", newUrl);

  // Remove old DOM domains.
  $("#bar2 .domain").remove();

  // Set protein name and size.
  if (isdimer) {
    $("#bar2 .pname, #pshowinac, #sbprot").html(curDomainData["pid"]);
  } else {
    $("#bar2 .pname, #pshowinac, #sbprot").html(curDomainData["pname"]);
  }
  $("#bar2 .pdesc").html(curDomainData["pdesc"]);
  $("#bar2 .enddesc").html(curDomainData["psize"]);
  $("#sbdom").html(curDomainData["dname"]);
  $("#sbseq").html(curDomainData["seqid"]);
  $("#sbpdb").html(curDomainData["pdb"]);
  $("#sbdop").html(curDomainData["dopescore"]);
  $("#sbdgwt").html(curDomainData["dgwt"]);
  $("#sbdgmut").html(curDomainData["dgmut"]);
  $("#sbddg").html(curDomainData["ddg"]);
  chainself = curDomainData["chainself"];
  chaininac = curDomainData["chaininac"];
  currentMut = curDomainData["mutnum"];

  // Add new domains.
  var d2;
  for (var i = 0; i < curDomains.length; i++) {
    var domhtml = '<div title="Click to open Pfam description." class="domain popup';
    if (curDomains[i]["status"]) {
      domhtml += " current2";
      d2 = {
        pxsize: parseInt(curDomains[i]["pxsize"]),
        pxstart: parseInt(curDomains[i]["pxstart"]),
      };
    }
    domhtml += '" style="width: ' + curDomains[i]["pxsize"];
    domhtml += "px; left: " + curDomains[i]["pxstart"];
    domhtml += 'px;" data-start="' + curDomains[i]["start"];
    domhtml += '" data-end="' + curDomains[i]["end"];
    domhtml += '" data-text="' + curDomains[i]["popup"];
    domhtml += '" data-bar="2">';
    domhtml += curDomains[i]["name"];
    domhtml += "</div>";
    $("#bar2").append(domhtml);
  }

  // Renew domain interaction shadow. Copied from views.py.
  // d1s: domain 1 start, d1w: domain 1 width.
  var d2s = d2["pxstart"],
    d2w = d2["pxsize"];
  var d1e = d1s + d1w,
    d2e = d2s + d2w;
  var d1 = {
    pxstart: d1s,
    pxsize: d1w,
  };
  //Find width of overlap/space.
  var mid_left = Math.min(Math.max(d1s, d2s), Math.min(d1e, d2e));
  var mid_right = Math.max(Math.max(d1s, d2s), Math.min(d1e, d2e));
  var mid_width = mid_right - mid_left;
  //Find width outside overlap/space.
  var first_d = d1s <= d2s ? d1 : d2;
  var notfirst_d = first_d == d2 ? d1 : d2;
  var last_d = d1e >= d2e ? d1 : d2;
  //If complete overlap.
  var overlap, left_width, right_width;
  if (first_d == last_d) {
    overlap = true;
    left_width = notfirst_d["pxstart"] - first_d["pxstart"];
    right_width =
      last_d["pxstart"] + last_d["pxsize"] - (notfirst_d["pxstart"] + notfirst_d["pxsize"]);
  } else if (first_d["pxstart"] + first_d["pxsize"] > last_d["pxstart"]) {
    overlap = true;
    left_width = last_d["pxstart"] - first_d["pxstart"];
    right_width = last_d["pxstart"] + last_d["pxsize"] - (first_d["pxstart"] + first_d["pxsize"]);
  } else {
    overlap = false;
    left_width = first_d["pxsize"];
    right_width = last_d["pxsize"];
  }
  //Find which direction the overlap is going.
  var left_side = first_d == d1 ? "down" : "up";
  var right_side = last_d == d1 ? "up" : "down";
  var mid_side = overlap ? "solid" : left_side;
  //Calculate heights.
  var left_height, right_height, mid_top_height, mid_bot_height;
  if (overlap) {
    left_height = right_height = Math.round(d_full_height / 2);
    mid_top_height = mid_bot_height = Math.round(d_full_height / 4);
  } else {
    left_height = Math.round(
      (d_full_height * first_d["pxsize"]) / (mid_width + first_d["pxsize"]) / 2
    );
    right_height = Math.round(
      (d_full_height * last_d["pxsize"]) / (mid_width + last_d["pxsize"]) / 2
    );
    mid_top_height =
      left_side == "down"
        ? Math.round(d_full_height / 2) - right_height
        : Math.round(d_full_height / 2) - left_height;
    mid_bot_height =
      left_side == "down"
        ? Math.round(d_full_height / 2) - left_height
        : Math.round(d_full_height / 2) - right_height;
  }
  //Reset shadow.
  var bord_color = "#E8EAE8";
  var back_color = "#F4F4F4";

  $("#protein2dinac .before, #protein2dinac .after").css("border-color", bord_color);
  $("#protein2dinac .toptria, #protein2dinac .bottria").css("border-color", "transparent");
  $("#protein2dinac .before").css("border-left-color", "transparent");
  $("#protein2dinac .after").css("border-right-color", "transparent");
  $("#protein2dinac .before, #protein2dinac .after").css("top", "auto").css("bottom", "auto");
  //Set shadow.
  $("#protein2dinac")
    .css("left", mid_left + "px")
    .css("width", mid_width + "px");
  $("#protein2dinac .toptria, #protein2dinac .bottria")
    .css("border-left-width", Math.round(mid_width / 2) + "px")
    .css("border-right-width", Math.round(mid_width / 2) + "px");
  $("#protein2dinac .toptria")
    .css("border-top-width", mid_top_height + "px")
    .css("border-bottom-width", mid_top_height + "px");
  $("#protein2dinac .bottria")
    .css("border-top-width", mid_bot_height + "px")
    .css("border-bottom-width", mid_bot_height + "px");
  $("#protein2dinac .before")
    .css("border-top-width", left_height + "px")
    .css("border-bottom-width", left_height + "px")
    .css("border-left-width", Math.round(left_width / 2) + "px")
    .css("border-right-width", Math.round(left_width / 2) + "px")
    .css("left", "-" + left_width + "px");
  $("#protein2dinac .after")
    .css("border-top-width", right_height + "px")
    .css("border-bottom-width", right_height + "px")
    .css("border-left-width", Math.round(right_width / 2) + "px")
    .css("border-right-width", Math.round(right_width / 2) + "px")
    .css("right", "-" + right_width + "px");

  if (mid_side == "down") {
    $("#protein2dinac .toptria")
      .css("border-top-color", back_color)
      .css("border-right-color", back_color);
    $("#protein2dinac .bottria")
      .css("border-bottom-color", back_color)
      .css("border-left-color", back_color);
  } else if (mid_side == "up") {
    $("#protein2dinac .toptria")
      .css("border-top-color", back_color)
      .css("border-left-color", back_color);
    $("#protein2dinac .bottria")
      .css("border-bottom-color", back_color)
      .css("border-right-color", back_color);
  }
  if (left_side == "down") {
    $("#protein2dinac .before").css("border-bottom-color", "transparent").css("top", "0px");
  } else if (left_side == "up") {
    $("#protein2dinac .before").css("border-top-color", "transparent").css("bottom", "0px");
  }
  if (right_side == "down") {
    $("#protein2dinac .after").css("border-top-color", "transparent").css("bottom", "0px");
  } else if (right_side == "up") {
    $("#protein2dinac .after").css("border-bottom-color", "transparent").css("top", "0px");
  }

  // Enable popup.
  $(".popup").hover(
    function () {
      showHover(this);
      var currentbar = "#bar" + $(this).attr("data-bar");
      $(currentbar + " .tooltip2d").show();
    },
    function () {
      var currentbar = "#bar" + $(this).attr("data-bar");
      $(currentbar + " .tooltip2d").hide();
    }
  );

  $(".domain").unbind("click");
  $(".domain").click(function () {
    linkPfam($(this));
  });

  // Write loading message.
  var loadingmessage =
    'hide all; set echo top left; color echo [40,100,150]; font echo 18 SANSSERIF; echo "Loading structure, please wait..';
  if (jmolmode == "HTML5") {
    loadingmessage += "|(Switch mode to JAVA for snappier performance)";
  }
  loadingmessage += '";';

  Jmol.script(jmol1, loadingmessage);

  // Preserve jmol options.
  var mode = $(".bmode.underline").attr("id").substring(5);
  var stcks = $(".bstick.underline").attr("id").substring(6);
  if (stcks == "num") {
    stcks = $("#stickFormRange").val();
  }
  var cntrat = $(".bcenter.underline").attr("id").substring(1);
  var pZoom =
    "zoom " + Jmol.getPropertyAsString(jmol1, "orientationInfo.zoom").split("\t")[1] + ";";

  // Load PDBs.
  var script = makeInitiationScript(domainID);
  $("#pdbdl #dlwt").attr("href", mutPath + domainID + "wt.pdb");
  $("#pdbdl #dlmut").attr("href", mutPath + domainID + "mut.pdb");

  // Set saved jmol options.
  script += setMode(mode) + cartoon(defaultCartoon) + label(defaultLabel, "model " + defaultModel);
  script += color(defaultColor) + showModel(defaultModel) + sticks(stcks);
  script += centerAt(cntrat) + showProtein(defaultShow) + pZoom;
  Jmol.script(jmol1, script);
}

function setMode(mode) {
  $(".bmode").removeClass("underline");
  $("#bmode" + mode).addClass("underline");
  var script;
  switch (mode) {
    case "best":
      script = "set platformSpeed 8; set antialiasDisplay true; set cartoonFancy true;";
      break;
    case "normal":
      script = "set platformSpeed 7; set antialiasDisplay true; set cartoonFancy false;";
      break;
    case "worst":
      script = "set platformSpeed 1; set antialiasDisplay false; set cartoonFancy false;";
      break;
  }
  return script;
}

function showModel(num) {
  $(".bshow").removeClass("underline");
  $("#b" + num.replace(".", "\\.")).addClass("underline");
  defaultModel = num;
  return label(defaultLabel, "model " + num);
}

function showProtein(mode) {
  $(".pshow").removeClass("underline");
  $("#pshow" + mode).addClass("underline");
  var cartoonmode = "";
  if (defaultCartoon == "on") {
    cartoonmode = "cartoon on;";
  } else if (defaultCartoon == "trans") {
    cartoonmode =
      "cartoon on; color cartoon translucent 0.9; select selected and (helix or sheet); color cartoon translucent 0.5;";
  }
  var script = "select all; cartoon off; wireframe off;";
  switch (mode) {
    case "self":
      defaultShow = "*" + chainself;
      script += "select *" + chainself + " and ~sticks; wireframe 0.2; select *" + chainself + "; ";
      break;
    case "inac":
      defaultShow = "*" + chaininac;
      script += "select *" + chaininac + " and ~sticks; wireframe 0.2; select *" + chaininac + "; ";
      break;
    case "hetatm":
      defaultShow = "all and not ~prot";
      script += "select all and not ~prot or hetero; wireframe 0.2;";
      break;
    case "all":
      defaultShow = "all";
      script +=
        "select ~sticks; wireframe 0.2; select not ~prot or hetero; wireframe 0.2; select all;";
      break;
  }
  script += "define ~on selected;" + cartoonmode;
  script += label(defaultLabel, "model " + defaultModel);
  return script;
}

function centerAt(mode) {
  $(".bcenter").removeClass("underline");
  $("#b" + mode).addClass("underline");
  var script;
  if (mode == "prot") {
    script = "select all; zoom (selected) 0;";
  } else if (mode == "mut") {
    script = "select " + currentMut + "; zoom (selected) 0;";
  }
  return script;
}

function cartoon(mode, selected) {
  $(".bcart").removeClass("underline");
  $("#bcart" + mode).addClass("underline");
  var script;
  switch (mode) {
    case "on":
      script = "select all; cartoon on; color cartoon translucent 0;";
      break;
    case "off":
      script = "select all; cartoon off;";
      break;
    case "trans":
      script = cartoonTranslucent();
      break;
  }
  defaultCartoon = mode;
  return script;
}

function cartoonTranslucent() {
  return "select all; cartoon on; color cartoon translucent 0.9; select helix or sheet; color cartoon translucent 0.5;";
}

function closeby(distance, doStick, doZoom) {
  var script =
    "select group within(" +
    distance +
    ", " +
    currentMut +
    ") and protein; " +
    'script "' +
    staticFolder +
    'jsmol/ras.scr"; ';

  script += "define ~closeby selected;";

  if (doStick) {
    script +=
      "select ~prot; wireframe off; select ~closeby or hetero; wireframe 0.2; define ~sticks ~closeby or hetero;";
  }
  if (doZoom) {
    script += " zoom (selected) 0;";
  }
  return script;
}

function sticks(mode) {
  $(".bstick").removeClass("underline");
  var script;
  if (mode == "off") {
    $("#bstickoff").addClass("underline");
    script = "select ~prot; wireframe off; define ~sticks hetero;";
  } else if (mode == "on") {
    $("#bstickon").addClass("underline");
    script = "select ~prot; wireframe 0.2; define ~sticks all;";
  } else {
    $("#bsticknum").addClass("underline");
    script = closeby(mode, true, false);
  }
  if (defaultLabel == "sticks") {
    script += label("sticks", false);
  }
  return script;
}

function label(mode, model) {
  $(".blabel").removeClass("underline");
  $("#blabel" + mode).addClass("underline");
  var showModel = "";
  if (model) {
    showModel = " " + model + ";";
  }
  var script;
  if (mode == "off") {
    script = "select protein; label off;";
  } else {
    model = defaultModel;
    if (mode == "sticks") {
      primary = "~sticks";
    } else if (mode == "on") {
      primary = "~prot";
    }
    if (defaultModel == "2.1") {
      script =
        "select protein; label off; select " +
        primary +
        ' and model=2.1 and *.ca and ~on; label "%[group1]%1.0[property_resno]";';
    } else {
      script =
        "select protein; label off; select " +
        primary +
        ' and model=1.1 and *.ca and ~on; label "%[group1]%1.0[property_resno]";';
      if (defaultModel == "0") {
        script += " select " + primary + " and " + currentMut + " and *.ca and ~on; label off;";
        var ca, cb;
        if (reverseLabel) {
          ca = "2.1";
          cb = "1.1";
        } else {
          ca = "1.1";
          cb = "2.1";
        }
        script +=
          " select " +
          primary +
          " and " +
          currentMut +
          " and model=" +
          ca +
          ' and *.ca and ~on; label "%[group1]%1.0[property_resno]";';
        script +=
          " select " +
          primary +
          " and " +
          currentMut +
          " and model=" +
          cb +
          ' and *.cb and ~on; label "%[group1]%1.0[property_resno]";';
      }
    }
  }
  defaultLabel = mode;
  return script + showModel;
}

function surface(mode) {
  $(".bsur").removeClass("underline");
  $("#bsur" + mode).addClass("underline");
  var script;
  switch (mode) {
    case "on":
      script = "select all; isosurface off;";
      break;
    case "off":
      script = "select all; isosurface molecular;";
      break;
    case "trans":
      script = "model 1.1; isosurface molecular;";
      break;
  }
  return script;
}

function color(mode, chains) {
  $(".bcolor").removeClass("underline");
  $("#bcolor" + mode).addClass("underline");
  //alert(chainself + ' ' + chaininac);
  var extra = "";
  var script;
  switch (mode) {
    case "chain":
      script =
        "select all; color [153,153,153]; color cartoon [153,153,153]; select not _C; color [250,100,0];" +
        '{nitrogen}.color = "[20,120,210]"; {oxygen}.color = "[200,20,20]"; {sulfur}.color = "[250,250,0]"; {phosphorus}.color = "[40,130,70]";' +
        "select *" +
        chainself +
        " and _C;  color [160,210,250]; color cartoon [160,210,250];" +
        "select *" +
        chaininac +
        " and _C;  color [241,175,183]; color cartoon [241,175,183];";
      break;
    case "structure":
      script = "select protein; color structure; color cartoon structure;";
      break;
    //case "residue":
    //  var script = "select protein; color amino; color cartoon amino;";
    //  break;
    case "atom":
      script =
        '{all}.color = "[250,100,0]"; {nitrogen}.color = "[20,120,210]"; {oxygen}.color = "[200,20,20]"; {sulfur}.color = "[250,250,0]"; {phosphorus}.color = "[40,130,70]";' +
        "select model=1.1 and _C; color [153,153,153]; color cartoon [153,153,153];" +
        "select model=2.1 and _C; color [115,194,255]; color cartoon [115,194,255];";
      extra = " and _C";
      break;
    case "hydro":
      script =
        "select [ile]; color [0.996,0.062,0.062]; color cartoon [0.996,0.062,0.062]; " +
        "select [phe]; color [0.996,0.109,0.109]; color cartoon [0.996,0.109,0.109]; " +
        "select [val]; color [0.992,0.156,0.156]; color cartoon [0.992,0.156,0.156]; " +
        "select [leu]; color [0.992,0.207,0.207]; color cartoon [0.992,0.207,0.207]; " +
        "select [trp]; color [0.992,0.254,0.254]; color cartoon [0.992,0.254,0.254]; " +
        "select [met]; color [0.988,0.301,0.301]; color cartoon [0.988,0.301,0.301]; " +
        "select [ala]; color [0.988,0.348,0.348]; color cartoon [0.988,0.348,0.348]; " +
        "select [gly]; color [0.984,0.394,0.394]; color cartoon [0.984,0.394,0.394]; " +
        "select [cys]; color [0.984,0.445,0.445]; color cartoon [0.984,0.445,0.445]; " +
        "select [tyr]; color [0.984,0.492,0.492]; color cartoon [0.984,0.492,0.492]; " +
        "select [pro]; color [0.980,0.539,0.539]; color cartoon [0.980,0.539,0.539]; " +
        "select [thr]; color [0.980,0.586,0.586]; color cartoon [0.980,0.586,0.586]; " +
        "select [ser]; color [0.980,0.637,0.637]; color cartoon [0.980,0.637,0.637]; " +
        "select [his]; color [0.977,0.684,0.684]; color cartoon [0.977,0.684,0.684]; " +
        "select [glu]; color [0.977,0.730,0.730]; color cartoon [0.977,0.730,0.730]; " +
        "select [asn]; color [0.973,0.777,0.777]; color cartoon [0.973,0.777,0.777]; " +
        "select [gln]; color [0.973,0.824,0.824]; color cartoon [0.973,0.824,0.824]; " +
        "select [asp]; color [0.973,0.875,0.875]; color cartoon [0.973,0.875,0.875]; " +
        "select [lys]; color [0.899,0.922,0.922]; color cartoon [0.899,0.922,0.922]; " +
        "select [arg]; color [0.899,0.969,0.969]; color cartoon [0.899,0.969,0.969]; ";
      break;
    //case "charge":
    //  var script = 'select protein;';
    //  break;
  }
  defaultColor = mode;

  script += "select " + currentMut + " and model=2.1" + extra + "; color label [200,20,20];";

  var trans;
  if (defaultCartoon == "trans") {
    trans = cartoonTranslucent();
  } else {
    trans = "";
  }
  return script + trans;
}
