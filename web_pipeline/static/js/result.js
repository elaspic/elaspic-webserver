function rerunMut(pnm) {
  $.ajax({
    url: "/json/rerun/",
    data: {
      m: pnm,
      j: jobID,
    },
    type: "GET",
    dataType: "json",
    cache: false,
    success: function (data) {
      if (data.error) {
        alert("Could not rerun " + pnm + ". Try again later.");
      } else {
        // Successfully rerun.
        location.reload();
      }
    },
    error: function () {
      alert("Could not rerun " + pnm + ". Try again later.");
    },
  });
}

function setRowColors() {
  $("#resulttable tbody tr").removeClass("odd").removeClass("even");
  $("#resulttable tbody tr:visible:odd").addClass("odd");
  $("#resulttable tbody tr:visible:even").addClass("even");
}

function filterResultTable() {
  function addOrAssign(column, index, sep, value) {
    if (column[index]) {
      column[index] += `${sep}${value}`;
    } else {
      column[index] = `${value}`;
    }
  }

  var columns = ["", "", "", "", "", "", "", "", "", "", ""];

  columns[1] = $("#inprot").val();

  if (!($("#instacom").prop("checked") && $("#instarun").prop("checked") && $("#instaerr").prop("checked"))) {
    if ($("#instacom").prop("checked")) {
      addOrAssign(columns, 0, "|", "1|2");
    }
    if ($("#instarun").prop("checked")) {
      addOrAssign(columns, 0, "|", "3|4");
    }
    if ($("#instaerr").prop("checked")) {
      addOrAssign(columns, 0, "|", "5");
    }
    if (!columns[0]) {
      columns[0] = "9";
    }
  }

  if (!($("#intypcor").prop("checked") && $("#intypint").prop("checked") && $("#intypunk").prop("checked"))) {
    if ($("#intypcor").prop("checked")) {
      addOrAssign(columns, 3, "|", "Core.*");
    }
    if ($("#intypint").prop("checked")) {
      addOrAssign(columns, 3, "|", "Interface.*");
    }
    if ($("#intypunk").prop("checked")) {
      addOrAssign(columns, 3, "|", "None.*");
    }
    if (!columns[3]) {
      columns[3] = "Some text that should never match anything.";
    } else {
      columns[3] = `/${columns[3]}/`;
    }
  }

  const options = ["inseq", "inali", "indop", "inpro", "inddg", "inel2"];
  for (const [index, element] of options.entries()) {
    console.log($.isNumeric($(`#${element}bot`).val()));
    if ($.isNumeric($(`#${element}bot`).val())) {
      let value = parseFloat($(`#${element}bot`).val());
      columns[5 + index] = `>= ${value}`;
    }
    if ($.isNumeric($(`#${element}top`).val())) {
      let value = parseFloat($(`#${element}top`).val());
      addOrAssign(columns, 5 + index, " && ", `<= ${value}`);
    }
  }

  var result = $("#resulttable").trigger("search", [columns]);

  setRowColors();
  updateDlLinks();
}

function updateDlLinks() {
  // Get all filtered mutations.
  var filteredMuts = [];
  $("#resulttable tbody tr:visible").each(function (index) {
    filteredMuts.push($(this).attr("data-pnt"));
  });
  filteredMuts = filteredMuts.join(" ");

  // Put them in the href of all download links.
  $("#download a").each(function (index) {
    var thisFile = $(this).attr("data-file");
    var baseHref = "/getfile/?j=" + jobID + "&f=" + thisFile + "&m=";
    $(this).attr("href", baseHref + filteredMuts);
  });
}

function bytesToKilo(bytes) {
  if (bytes < 1024) {
    return bytes + " B";
  }
  var kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return kilobytes.toFixed(1) + " kB";
  }
  var megabytes = kilobytes / 1024;
  if (megabytes < 1024) {
    return megabytes.toFixed(1) + " MB";
  }
  var gigabytes = megabytes / 1024;
  return megabytes.toFixed(1) + " GB";
}

function updateDlCell(celldata, cellid) {
  if (celldata[0]) {
    var files, size;
    if (celldata[0] == 1) {
      files = "1 file";
    } else {
      files = celldata[0] + " files";
    }
    size = bytesToKilo(celldata[1]);

    $("#" + cellid + " .desc").text("(" + files + ", " + size + ")");

    $("#" + cellid + " span, #" + cellid + " a").show();
  } else {
    $("#" + cellid + " span, #" + cellid + " a").hide();
  }
}

function updateDlTable(data, length) {
  if (data) {
    updateDlCell(data.simpleresults, "simpleresults");
    updateDlCell(data.allresults, "allresults");
    updateDlCell(data.wtmodelsori, "pdbwt");
    updateDlCell(data.wtmodelsopt, "pdbori");
    updateDlCell(data.mutmodels, "pdbmut");
    updateDlCell(data.alignments, "aligns");
    updateDlCell(data.sequences, "seqs");
    var totalFiles = data.simpleresults[0] + data.allresults[0] + data.wtmodelsori[0] + data.wtmodelsopt[0] + data.mutmodels[0] + data.alignments[0] + data.sequences[0];
    $("#filecount").text(totalFiles);
    if (totalFiles) {
      $("#dlall").show();
    } else {
      $("#dlall").hide();
    }
  }
}

function updateDownloadableFiles(ajaxReqs) {
  // Get filtered mutations.
  var filteredMuts = [];
  $("#resulttable tbody tr:visible").each(function (index) {
    filteredMuts.push($(this).attr("data-pnt"));
  });

  // Abort old ajax request.
  if (ajaxReqs[ajaxReqs.length - 1]) {
    ajaxReqs[ajaxReqs.length - 1].abort();
  }

  // Ajax!
  $("#dltable td a").hide();
  $("#dltable td span").html("");
  ajaxReqs[ajaxReqs.length] = $.ajax({
    url: "/json/getdownloads/",
    data: {
      m: filteredMuts.join(" "),
      j: jobID,
    },
    type: "GET",
    dataType: "json",
    cache: false,
    success: function (data) {
      updateDlTable(data, filteredMuts.length);
    },
    error: function () {
      updateDlTable(null, filteredMuts.length);
    },
  });
}

$(document).ready(function () {
  // **********************************
  //  Description of ALL pager options
  // **********************************
  var pagerOptions = {
    // target the pager markup - see the HTML block below
    container: $(".pager"),

    // use this url format "http:/mydatabase.com?page={page}&size={size}&{sortList:col}"
    ajaxUrl: null,

    // modify the url after all processing has been applied
    customAjaxUrl: function (table, url) {
      return url;
    },

    // ajax error callback from $.tablesorter.showError function
    // ajaxError: function( config, xhr, settings, exception ) { return exception; };
    // returning false will abort the error message
    ajaxError: null,

    // add more ajax settings here
    // see http://api.jquery.com/jQuery.ajax/#jQuery-ajax-settings
    ajaxObject: { dataType: "json" },

    // process ajax so that the data object is returned along with the total number of rows
    ajaxProcessing: null,

    // Set this option to false if your table data is preloaded into the table, but you are still using ajax
    processAjaxOnInit: true,

    // output string - default is '{page}/{totalPages}'
    // possible variables: {size}, {page}, {totalPages}, {filteredPages}, {startRow}, {endRow}, {filteredRows} and {totalRows}
    // also {page:input} & {startRow:input} will add a modifiable input in place of the value
    // In v2.27.7, this can be set as a function
    // output: function(table, pager) { return 'page ' + pager.startRow + ' - ' + pager.endRow; }
    output: "{startRow:input} – {endRow} / {totalRows} rows",

    // apply disabled classname (cssDisabled option) to the pager arrows when the rows
    // are at either extreme is visible; default is true
    updateArrows: true,

    // starting page of the pager (zero based index)
    page: 0,

    // Number of visible rows - default is 10
    size: 10,

    // Save pager page & size if the storage script is loaded (requires $.tablesorter.storage in jquery.tablesorter.widgets.js)
    savePages: true,

    // Saves tablesorter paging to custom key if defined.
    // Key parameter name used by the $.tablesorter.storage function.
    // Useful if you have multiple tables defined
    storageKey: "tablesorter-pager",

    // Reset pager to this page after filtering; set to desired page number (zero-based index),
    // or false to not change page at filter start
    pageReset: 0,

    // if true, the table will remain the same height no matter how many records are displayed. The space is made up by an empty
    // table row set to a height to compensate; default is false
    fixedHeight: false,

    // remove rows from the table to speed up the sort of large tables.
    // setting this to false, only hides the non-visible rows; needed if you plan to add/remove rows with the pager enabled.
    removeRows: false,

    // If true, child rows will be counted towards the pager set size
    countChildRows: false,

    // css class names of pager arrows
    cssNext: ".next", // next page arrow
    cssPrev: ".prev", // previous page arrow
    cssFirst: ".first", // go to first page arrow
    cssLast: ".last", // go to last page arrow
    cssGoto: ".gotoPage", // select dropdown to allow choosing a page

    cssPageDisplay: ".pagedisplay", // location of where the "output" is displayed
    cssPageSize: ".pagesize", // page size selector - select dropdown that sets the "size" option

    // class added to arrows when at the extremes (i.e. prev/first arrows are "disabled" when on the first page)
    cssDisabled: "disabled", // Note there is no period "." in front of this class name
    cssErrorRow: "tablesorter-errorRow", // ajax error information row
  };

  // Download files ajax.
  var first = true;
  var ajaxRequests = [];

  $("#resulttable").bind("tablesorter-initialized", function (e, table) {
    // do something after tablesorter has initialized
    filterResultTable();
    $("#result-table-progress").hide();
    $("#resulttable").show();
    $("#resulttable").trigger("applyWidgets");
    if (first) updateDownloadableFiles(ajaxRequests);
    first = false;
  });

  // Enable the sortable table.
  $("#resulttable")
    .tablesorter({
      sortList: [
        [0, 0],
        [1, 0],
        [2, 0],
      ],

      // Pre-sort: status, protein, mutation.

      // initialized: function (table) {
      //   // do something after tablesorter has initialized
      //   filterResultTable();
      //   $("#result-table-progress").hide();
      //   $("#resulttable").show();
      //   if (first) updateDownloadableFiles(ajaxRequests);
      //   first = false;
      // },

      // headers : { 0 : { sorter: false } },

      headerTemplate: "{content}",

      theme: "blue",
      widthFixed: false,
      widgets: ["zebra", "filter"],

      widgetOptions: {
        zebra: ["odd", "even"],
        filter_columnFilters: false,
      },
    })

    // bind to pager events
    // *********************
    .bind("pagerChange pagerComplete pagerInitialized pageMoved", function (e, c) {
      var msg = '"</span> event triggered, ' + (e.type === "pagerChange" ? "going to" : "now on") + ' page <span class="typ">' + (c.page + 1) + "/" + c.totalPages + "</span>";
      $("#display")
        .append('<li><span class="str">"' + e.type + msg + "</li>")
        .find("li:first")
        .remove();
    })

    // initialize the pager plugin
    // ****************************
    .tablesorterPager(pagerOptions);

  // Add two new rows using the "addRows" method
  // the "update" method doesn't work here because not all rows are
  // present in the table when the pager is applied ("removeRows" is false)
  // ***********************************************************************
  var r,
    $row,
    num = 50,
    row = '<tr><td>Student{i}</td><td>{m}</td><td>{g}</td><td>{r}</td><td>{r}</td><td>{r}</td><td>{r}</td><td><button type="button" class="remove" title="Remove this row">X</button></td></tr>' + '<tr><td>Student{j}</td><td>{m}</td><td>{g}</td><td>{r}</td><td>{r}</td><td>{r}</td><td>{r}</td><td><button type="button" class="remove" title="Remove this row">X</button></td></tr>';
  $("button:contains(Add)").click(function () {
    // add two rows of random data!
    r = row.replace(/\{[gijmr]\}/g, function (m) {
      return {
        "{i}": num + 1,
        "{j}": num + 2,
        "{r}": Math.round(Math.random() * 100),
        "{g}": Math.random() > 0.5 ? "male" : "female",
        "{m}": Math.random() > 0.5 ? "Mathematics" : "Languages",
      }[m];
    });
    num = num + 2;
    $row = $(r);
    $("table").find("tbody").append($row).trigger("addRows", [$row]);
    return false;
  });

  // Delete a row
  // *************
  $("table").delegate("button.remove", "click", function () {
    var t = $("table");
    // disabling the pager will restore all table rows
    // t.trigger('disablePager');
    // remove chosen row
    $(this).closest("tr").remove();
    // restore pager
    // t.trigger('enablePager');
    t.trigger("update");
    return false;
  });

  // Destroy pager / Restore pager
  // **************
  $("button:contains(Destroy)").click(function () {
    // Exterminate, annhilate, destroy! http://www.youtube.com/watch?v=LOqn8FxuyFs
    var $t = $(this);
    if (/Destroy/.test($t.text())) {
      $("table").trigger("destroyPager");
      $t.text("Restore Pager");
    } else {
      $("table").tablesorterPager(pagerOptions);
      $t.text("Destroy Pager");
    }
    return false;
  });

  // Disable / Enable
  // **************
  $(".toggle").click(function () {
    var mode = /Disable/.test($(this).text());
    $("table").trigger((mode ? "disable" : "enable") + "Pager");
    $(this).text((mode ? "Enable" : "Disable") + "Pager");
    return false;
  });
  $("table").bind("pagerChange", function () {
    // pager automatically enables when table is sorted.
    $(".toggle").text("Disable Pager");
  });

  // clear storage (page & size)
  $(".clear-pager-data").click(function () {
    // clears user set page & size from local storage, so on page
    // reload the page & size resets to the original settings
    $.tablesorter.storage($("table"), "tablesorter-pager", "");
  });

  // go to page 1 showing 10 rows
  $(".goto").click(function () {
    // triggering "pageAndSize" without parameters will reset the
    // pager to page 1 and the original set size (10 by default)
    // $('table').trigger('pageAndSize')
    $("table").trigger("pageAndSize", [1, 10]);
  });

  // Enable filtering of table (but do not redownload files)
  $("#filtcontrols input").click(function () {
    filterResultTable();
    // updateDownloadableFiles(ajaxRequests);
  });
  $("#filtcontrols input").keyup(function () {
    filterResultTable();
    // updateDownloadableFiles(ajaxRequests);
  });
  $("#reset").click(function () {
    $("#filtcontrols .inputtext").val("");
    $("#filtcontrols .checkbox").prop("checked", true);
    $(".tooltip#tfil").hide();
    filterResultTable();
    // updateDownloadableFiles(ajaxRequests);
  });

  // Tooltips
  $(document).click(function () {
    $(".tooltip").hide();
  });

  $(".tclose").click(function () {
    var tooltip = "t" + $(this).attr("id").substr(2);
    $(".tooltip#" + tooltip).hide();
  });

  $(".tooltip").click(function (e) {
    e.stopPropagation();
  });

  $(".help").mousedown(function (e) {
    e.stopPropagation();
  });

  var lastHelp;
  $(".help").click(function (e) {
    e.stopPropagation();
    var tooltip = "t" + $(this).attr("class").split(" ")[1];
    var offTop = $(this).offset().top - 10;
    var offLeft = $(this).offset().left + 30;
    $(".tooltip#" + tooltip)
      .css("top", offTop + "px")
      .css("left", offLeft + "px");

    // Insert protein and mutation for error tooltip.
    if (tooltip == "term") {
      $("#toolpnm").html($(this).attr("data-pnm"));
    }

    // Ensure show if same tooltip.
    if (lastHelp == this) {
      $(".tooltip#" + tooltip).toggle(0);
    } else {
      $(".tooltip#" + tooltip).show(0);
    }
    lastHelp = this;
  });

  // Rerun
  $("#rerun").click(function () {
    rerunMut($("#toolpnm").html());
    $("#rerun").unbind("click");
  });
});
