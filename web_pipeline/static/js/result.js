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
				alert('Could not rerun ' + pnm + '. Try again later.');
			} else {
				// Successfully rerun.
				location.reload();
			}
		},
		error: function () {
			alert('Could not rerun ' + pnm + '. Try again later.');
		}
	});
}

function setRowColors() {
	$('#resulttable tbody tr').removeClass('odd').removeClass('even');
	$('#resulttable tbody tr:visible:odd').addClass('odd');
    $('#resulttable tbody tr:visible:even').addClass('even');
}

function filterResultTable() {

	var inProt = $('#inprot').val();
	// (condition) ? true-value : false-value;
	var inSeqBot = $.isNumeric( $('#inseqbot').val() ) ? parseFloat( $('#inseqbot').val() ) : -Infinity;
	var inSeqTop = $.isNumeric( $('#inseqtop').val() ) ? parseFloat( $('#inseqtop').val() ) : Infinity;
	var inAliBot = $.isNumeric( $('#inalibot').val() ) ? parseFloat( $('#inalibot').val() ) : -Infinity;
	var inAliTop = $.isNumeric( $('#inalitop').val() ) ? parseFloat( $('#inalitop').val() ) : Infinity;
	var inDOPBot = $.isNumeric( $('#indopbot').val() ) ? parseFloat( $('#indopbot').val() ) : -Infinity;
	var inDOPTop = $.isNumeric( $('#indoptop').val() ) ? parseFloat( $('#indoptop').val() ) : Infinity;
	var indGwBot = $.isNumeric( $('#indgwbot').val() ) ? parseFloat( $('#indgwbot').val() ) : -Infinity;
	var indGwTop = $.isNumeric( $('#indgwtop').val() ) ? parseFloat( $('#indgwtop').val() ) : Infinity;
	var indGmBot = $.isNumeric( $('#indgmbot').val() ) ? parseFloat( $('#indgmbot').val() ) : -Infinity;
	var indGmTop = $.isNumeric( $('#indgmtop').val() ) ? parseFloat( $('#indgmtop').val() ) : Infinity;
	var inddGBot = $.isNumeric( $('#inddgbot').val() ) ? parseFloat( $('#inddgbot').val() ) : -Infinity;
	var inddGTop = $.isNumeric( $('#inddgtop').val() ) ? parseFloat( $('#inddgtop').val() ) : Infinity;

    // Recusively filter the jquery object to get results.
    var jo = $("#resulttable tbody").find("tr");
    joFiltered = jo.filter(function () {
    	var toKeep = true;
        var $row = $(this);

        // Filter by each column.
        var test = $row.find('td').each(function() {
	        $cell = $(this);

	        // Protein.
	        if ($cell.hasClass('tdp')) {
		    	if ($cell.text().toLowerCase().indexOf(inProt.toLowerCase()) == -1) return toKeep = false;
			// Status.
			} else if ($cell.hasClass('tds')) {
				if (!$('#instacom').prop('checked')) {
					if ($cell.hasClass('done') || $cell.hasClass('doneNO')) return toKeep = false;
				}
				if (!$('#instarun').prop('checked')) {
					if ($cell.hasClass('running') || $cell.hasClass('queued')) return toKeep = false;
				}
				if (!$('#instaerr').prop('checked')) {
					if ($cell.hasClass('error')) return toKeep = false;
				}
			// Type.
			} else if ($cell.hasClass('tdt')) {
				if (!$('#intypcor').prop('checked') && $cell.text().trim() == 'Core') return toKeep = false;
				if (!$('#intypint').prop('checked') && $cell.text().trim().split(' ')[0] == 'Interface') return toKeep = false;
				if (!$('#intypunk').prop('checked') && $cell.text().trim() == 'None') return toKeep = false;
			// Sequence identity score.
		    } else if ($cell.hasClass('tdi')) {
		    	if (inSeqBot > parseFloat($cell.text()) || inSeqTop < parseFloat($cell.text())) {
					if ((parseFloat($cell.text()) != 1000000)) return toKeep = false;
				}
			// Alignment score.
		    } else if ($cell.hasClass('tda')) {
		    	if (inAliBot > parseFloat($cell.text()) || inAliTop < parseFloat($cell.text())) {
					if ((parseFloat($cell.text()) != 1000000)) return toKeep = false;
				}
			// DOPE score.
		    } else if ($cell.hasClass('tdd')) {
		    	if (inDOPBot > parseFloat($cell.text()) || inDOPTop < parseFloat($cell.text())) {
					if ((parseFloat($cell.text()) != 1000000)) return toKeep = false;
				}
		    // dG_wt.
		    } else if ($cell.hasClass('tdwd')) {
		    	if (indGwBot > parseFloat($cell.text()) || indGwTop < parseFloat($cell.text())) {
					if ((parseFloat($cell.text()) != 1000000)) return toKeep = false;
				}
		    // dG_mut.
		    } else if ($cell.hasClass('tdmd')) {
		    	if (indGmBot > parseFloat($cell.text()) || indGmTop < parseFloat($cell.text())) {
					if ((parseFloat($cell.text()) != 1000000)) return toKeep = false;
				}
		    // ddG.
		    } else if ($cell.hasClass('tdg')) {
		    	if (inddGBot > parseFloat($cell.text()) || inddGTop < parseFloat($cell.text())) {
					if ((parseFloat($cell.text()) != 1000000)) return toKeep = false;
				}
		    }
        });
        if (toKeep) {
        	return true;
        }
    });

    // Hide all the rows, then show the rows that match.
    jo.hide();
    joFiltered.show();

	setRowColors();
	updateDlLinks()

}
function updateDlLinks() {
	// Get all filtered mutations.
	var filteredMuts = [];
    $('#resulttable tbody tr:visible').each(function(index){
    	filteredMuts.push( $(this).attr('data-pnt') );
    });
    filteredMuts = filteredMuts.join(' ');

    // Put them in the href of all download links.
    $('#download a').each(function(index){
    	var thisFile = $(this).attr('data-file');
    	var baseHref = '/getfile/?j=' + jobID + '&f=' + thisFile + '&m='
    	$(this).attr('href', baseHref + filteredMuts);
    });
}

function bytesToKilo(bytes) {
	if (bytes < 1024) {
		return bytes + ' B';
	}
	var kilobytes = bytes / 1024;
	if (kilobytes < 1024) {
		return kilobytes.toFixed(1) + ' kB';
	}
	var megabytes = kilobytes / 1024;
	if (megabytes < 1024) {
		return megabytes.toFixed(1) + ' MB';
	}
	var gigabytes = megabytes / 1024;
	return megabytes.toFixed(1) + ' GB';
}

function updateDlCell(celldata, cellid) {
	if (celldata[0]) {
		var files, size;
		if (celldata[0] == 1) {
			files = '1 file';
		} else {
			files = celldata[0] + ' files'
		}
		size = bytesToKilo(celldata[1]);

		$('#' + cellid + ' .desc').text('(' + files + ', ' + size + ')');

		$('#' + cellid + ' span, #' + cellid + ' a').show();
	} else {
		$('#' + cellid + ' span, #' + cellid + ' a').hide();
	}
}

function updateDlTable(data, length) {
	if (data) {
		updateDlCell(data.simpleresults, 'simpleresults');
		updateDlCell(data.allresults, 'allresults');
		updateDlCell(data.wtmodelsori, 'pdbwt');
		updateDlCell(data.wtmodelsopt, 'pdbori');
		updateDlCell(data.mutmodels, 'pdbmut');
		updateDlCell(data.alignments, 'aligns');
		updateDlCell(data.sequences, 'seqs');
		var totalFiles = data.simpleresults[0] + data.allresults[0] +
						 data.wtmodelsori[0] + data.wtmodelsopt[0] + data.mutmodels[0] +
						 data.alignments[0] + data.sequences[0];
		$('#filecount').text(totalFiles);
		if (totalFiles) {
			$('#dlall').show();
		} else {
			$('#dlall').hide();
		}
	}
}

function updateDownloadableFiles(ajaxReqs) {

	// Get filtered mutations.
    var filteredMuts = [];
    $('#resulttable tbody tr:visible').each(function(index){
    	filteredMuts.push( $(this).attr('data-pnt') );
    });

    // Abort old ajax request.
	if (ajaxReqs[ajaxReqs.length - 1]) {
		ajaxReqs[ajaxReqs.length - 1].abort();
	}

	// Ajax!
	$('#dltable td a').hide();
	$('#dltable td span').html('');
	ajaxReqs[ajaxReqs.length] = $.ajax({
		url: "/json/getdownloads/",
		data: {
			m: filteredMuts.join(' '),
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
		}
	});
}

$(document).ready(function(){

	// Download files ajax.
	var first = true;
	var ajaxRequests = new Array();

	// Enable the sortable table.
	$('#resulttable').tablesorter({
        sortList: [[0,0],[1,0],[2,0]], // Pre-sort: status, protein, mutation.
    }).bind("sortEnd", function() {
    	filterResultTable();
    	if (first) updateDownloadableFiles(ajaxRequests);
    	first = false;
    });

    // Enable filtering of table.
    $("#filtcontrols input").click(function() {
    	filterResultTable();
    	updateDownloadableFiles(ajaxRequests);
    });
    $("#filtcontrols input").keyup(function() {
    	filterResultTable();
    	updateDownloadableFiles(ajaxRequests);
    });
    $("#reset").click(function() {
    	$("#filtcontrols .inputtext").val('');
    	$('#filtcontrols .checkbox').prop('checked', true);
    	$('.tooltip#tfil').hide();
    	filterResultTable();
    	updateDownloadableFiles(ajaxRequests);
    });

    // Tooltips.
	$(document).click(function() {
		$('.tooltip').hide();
	});
	$('.tclose').click(function() {
		var tooltip = 't' + $(this).attr('id').substr(2);
		$('.tooltip#' + tooltip).hide();
	});
	$('.tooltip').click(function(e) {
		e.stopPropagation();
	});
	var lastHelp;
    $('.help').click(function(e) {
    	e.stopPropagation();
    	var tooltip = 't' + $(this).attr('class').split(' ')[1];
    	var offTop = $(this).offset().top - 10;
    	var offLeft = $(this).offset().left + 30;
    	$('.tooltip#' + tooltip).css('top', offTop + 'px').css('left', offLeft + 'px');

    	// Insert protein and mutation for error tooltip.
    	if (tooltip == 'term') {
	    	$('#toolpnm').html( $(this).attr('data-pnm') );
    	}
    	// Ensure show if same tooltip.
    	if (lastHelp == this) {
			$('.tooltip#' + tooltip).toggle(0);
		} else {
			$('.tooltip#' + tooltip).show(0);
		}
		lastHelp = this;
    });

    // Rerun.
    $('#rerun').click(function() {
    	rerunMut( $('#toolpnm').html() );
    	$('#rerun').unbind('click');
    });
});
