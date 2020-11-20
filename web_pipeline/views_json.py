import json
import logging
import os.path as op
import pickle
from collections import Counter, defaultdict
from re import sub
from subprocess import PIPE, Popen

import requests
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import Http404, HttpResponse
from django.utils import html
from kmbio import PDB
from kmtools import structure_tools

from . import functions as fn
from . import conf
from .filemanager import FileManager
from .functions import fetchProtein, getPnM, isInvalidMut
from .models import InterfaceModel  # InterfaceModelLocal,
from .models import (
    CoreModel,
    CoreMutation,
    CoreMutationLocal,
    InterfaceMutation,
    InterfaceMutationLocal,
    Job,
    JobToMut,
    findInDatabase,
)

# Create logger to redirect output.
logger = logging.getLogger(__name__)

MAX_NUM_MUTATIONS = 100


def rerunMut(request):
    logger.debug("rerunMut({})".format(request))
    if not request.GET:
        raise Http404
    if not ("m" in request.GET) or not ("j" in request.GET):
        raise Http404

    protein, mut = getPnM(request.GET["m"].upper())
    error = 0

    try:
        jtom = JobToMut.objects.get(
            job_id=request.GET["j"], inputIdentifier=protein, mut__mut=mut
        )
    except JobToMut.DoesNotExist:
        error = 1
    else:
        j = jtom.job
        j.isDone = False
        j.save()
        m = jtom.mut
        if not m.rerun:
            m.rerun = True
            m.save()
            # ##### Rerun pipeline #####
            # runPipelineWrapper.delay(m, j.jobID)
            # sleepabit.delay(5,10)
            data_in = {
                "job_id": j.jobID,
                "job_email": j.email,
                "job_type": "database",
                "secret_key": conf.JOBSUBMITTER_SECRET_KEY,
                "mutations": [
                    {
                        "protein_id": mut.protein,
                        "mutations": mut.mut,
                        "uniprot_domain_pair_ids": "",
                    }
                ],
            }
            status = None
            n_tries = 0
            while (not status or status == "error") and n_tries < 10:
                n_tries += 1
                r = requests.post(
                    "http://localhost:8001/elaspic/api/1.0/", json=data_in
                )
                status = r.json().get("status", None)

    return HttpResponse(json.dumps({"error": error}), content_type="application/json")


def getfile(request):
    logger.info("getfile({})".format(request))

    if not request.GET:
        raise Http404
    if not ("j" in request.GET) or not ("f" in request.GET) or not ("m" in request.GET):
        raise Http404

    fm = FileManager(jobID=request.GET["j"], muts=request.GET["m"].split(" "))

    filename = request.GET["f"]
    data = fm.makeFile(fileToMake=filename)
    content_type = _get_content_type(filename)
    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = "attachment; filename=" + filename
    return response


def _get_content_type(filename):
    if filename.endswith(".txt"):
        return "text/plain"
    elif filename.endswith(".zip"):
        return "application/zip"
    else:
        raise Exception("Unrecognized extension for file: {}".format(filename))


def getdownloads(request):
    logger.info("getdownloads({})".format(request))
    """ Used on result page to check for available files, prepared files in
        archives, and to return their file sizes. """

    if not request.GET:
        raise Http404
    if not "m" or not ("j" in request.GET):
        raise Http404

    files = [
        "simpleresults.txt",
        "allresults.txt",
        "wtmodels-ori.zip",
        "wtmodels-opt.zip",
        "mutmodels.zip",
        "alignments.zip",
        "sequences.zip",
    ]

    jsonDict = {}
    fm = FileManager(jobID=request.GET["j"], muts=request.GET["m"].split(" "))

    for f in files:
        data = fm.makeFile(fileToMake=f)
        file_size = len(data)
        logger.debug("fm.file_count: {}".format(fm.file_count))
        jsonDict[f.split(".")[0].replace("-", "")] = [fm.file_count, file_size]
    logger.debug("jsonDict: {}".format(jsonDict))
    logger.debug("fm.files: {}".format(fm.files._FixedDict__data))
    return HttpResponse(json.dumps(jsonDict), content_type="application/json")


def checkIfJobIsReady(request):

    if not request.POST:
        raise Http404
    if not ("j" in request.POST):
        raise Http404
    try:
        j = Job.objects.get(jobID=request.POST["j"])
    except Job.DoesNotExist:
        raise Http404

    staList, seqList, idenList = [], [], []
    for jm in j.jobtomut_set.all():
        staList.append(jm.mut.status)
        seqList.append(jm.mut.mut)
        idenList.append(jm.inputIdentifier)

    # TODO: job is ready when all mutations are ready
    jsonDict = {"done": j.isDone, "status": staList, "seq": seqList, "iden": idenList}

    return HttpResponse(json.dumps(jsonDict), content_type="application/json")


def _move_hetatm_to_hetatm_chain(chain, hetatm_chain, res):
    chain.detach_child(res.id)
    hetatm_res = res
    hetatm_res.id = (
        hetatm_res.id[0],
        len(hetatm_chain) + 1,
        hetatm_res.id[2],
    )
    hetatm_chain.add(hetatm_res)


def _correct_methylated_lysines(res):
    lysine_atoms = ["N", "CA", "CB", "CG", "CD", "CE", "NZ", "C", "O"]
    new_resname = "LYS"
    new_resid = (" ", res.id[1], res.id[2])
    res.resname = new_resname
    res.id = new_resid
    atom_idx = 0
    while atom_idx < len(res):
        atom_id = res.child_list[atom_idx].id
        if atom_id not in lysine_atoms:
            res.detach_child(atom_id)
        else:
            atom_idx += 1


def uploadFile(request):

    if not request.FILES:
        raise Http404
    if not ("fileToUpload" in request.FILES):
        raise Http404

    myfile = request.FILES["fileToUpload"]
    filetype = request.POST["filetype"]
    random_id = ""

    if myfile.size > 10000000:
        jsonDict = {"msg": "File is too large (>10 MB)", "error": 1}
        return HttpResponse(json.dumps(jsonDict), content_type="application/json")

    try:
        process = Popen(
            ["/usr/bin/file", "-i", myfile.temporary_file_path()], stdout=PIPE
        )
        stdout, stderr = process.communicate()

        if stdout.decode().split(" ")[1].split("/")[0] not in ("text", "chemical"):
            msg = "Uploaded file has to be raw text (not '{0}')".format(
                stdout.decode().split(" ")[1][:-1]
            )
            jsonDict = {"msg": msg, "error": 1}
            return HttpResponse(json.dumps(jsonDict), content_type="application/json")

        # Protein list upload.
        if filetype == "prot":

            # Remove white-spaces and empty lines.
            lines = myfile.read().decode().split("\n")
            trimmedLines = []
            for idx, line in enumerate(lines):
                if idx >= 500:
                    break
                newline = sub(r"\s+", "", line)
                if newline:
                    trimmedLines.append(newline)
            msg = "\n".join(trimmedLines)

    except Exception as e:
        logger.error("Caught exception '%s': %s", type(e), e)
        jsonDict = {"msg": "File could not be uploaded - try again", "error": 1}
        return HttpResponse(json.dumps(jsonDict), content_type="application/json")

    if filetype == "pdb":
        try:
            random_id = fn.get_random_id()
            user_path = fn.get_user_path(random_id)
            suffix = myfile.name.split(".")[-1]
            if suffix in ["cif", "mmcif"]:
                input_pdb = op.join(user_path, "input.cif")
            else:
                input_pdb = op.join(user_path, "input.pdb")

            with open(input_pdb, "w") as ifh:
                ifh.write(myfile.read().decode())

            structure = PDB.load(input_pdb)
            structure_tools.process_structure(structure)
            seq = [
                (
                    chain.id,
                    structure_tools.get_chain_sequence(
                        chain, if_unknown="replace", unknown_residue_marker="X"
                    ),
                )
                for chain in structure.chains
            ]
            logger.debug("seq: '{}'".format(seq))

            if len(seq) < 1:
                jsonDict = {"msg": "PDB does not have any valid chains. ", "error": 1}
                return HttpResponse(
                    json.dumps(jsonDict), content_type="application/json"
                )

            with open(op.join(user_path, "pdb_parsed.pickle"), "bw") as f:
                f.write(pickle.dumps(seq))

            msg = seq

        except Exception as e:
            logger.error("Caught exception '%s': %s", type(e), e)
            jsonDict = {"msg": f"PDB could not be parsed: {e}.", "error": 1}
            return HttpResponse(json.dumps(jsonDict), content_type="application/json")

    jsonDict = {
        "inputfile": myfile.name or "uploadedFile",
        "userpath": random_id,
        "msg": msg,
        "error": 0,
    }

    return HttpResponse(json.dumps(jsonDict), content_type="application/json")


def getProtein(request):
    """"""
    logger.debug("getProtein({})".format(request))

    # return HttpResponse(
    #    json.dumps({'r': [{'seq': 'AAAAAAAAAAAAAAAAAAAAAAAA'}], 'e': False}),
    #    content_type='application/json')

    # Check if the site was reached with GET method.
    if not request.GET:
        raise Http404
    if not ("p" in request.GET):
        raise Http404

    # Parse requested input.
    inps = request.GET["p"].split()
    reqs = dict(
        mut=True if "m" in request.GET else False,
        name=True if "n" in request.GET else False,
        seq=True if "s" in request.GET else False,
        dom=True if "d" in request.GET else False,
        knownmuts=True if "k" in request.GET else False,
        err=True if "e" in request.GET else False,
    )

    # Get all requested info from database.
    output, done = [], set()
    for idx, inp in enumerate(inps):
        mutation_info = _get_mutation_info(inp, reqs, done)
        output.append(mutation_info)

    # Create error lists.
    err = _get_errors(output) if reqs["err"] else None

    # Return
    logger.debug("output: {}".format(output))
    logger.debug("err: {}".format(err))
    return HttpResponse(
        json.dumps({"r": output, "e": err}), content_type="application/json"
    )


def _get_mutation_info(inp, reqs, done):
    mutation_info = {"iden": inp}

    if reqs["mut"]:
        protein, mut = getPnM(inp.upper())
    else:
        protein, mut = inp, None

    if not protein:
        mutation_info["error"] = True
        mutation_info["emsg"] = "SNX"
        return mutation_info
    if inp == "":
        mutation_info["error"] = True
        mutation_info["emsg"] = "EMP"
        return mutation_info

    p = fetchProtein(protein)  # get protein from database
    if not p:
        mutation_info["error"] = True
        mutation_info["emsg"] = "DNE"
        return mutation_info

    mutation_info.update(_get_mutation_info_info(p, mut, reqs))
    if reqs["mut"]:
        mutation_info.update(_check_for_duplicates(p.id + mut, done))
    return mutation_info


def _check_for_duplicates(unique_id, done):
    if unique_id in done:
        return {"error": True, "emsg": "DUP"}
    else:
        done.add(unique_id)
        return {}


def _get_mutation_info_info(p, mut, reqs):
    """"""
    mutation_info = {"error": False, "emsg": None}

    if reqs["mut"]:
        mutation_info["mut"] = mut
        mutation_info["muterr"] = isInvalidMut(mut, p.seq)

    # Set basic info.
    mutation_info["prot"] = p.id
    mutation_info["nothuman"] = False if p.organism_name == "Homo sapiens" else True

    # Set sequence
    if reqs["seq"]:
        mutation_info["seq"] = p.seq

    # Set gene name
    if reqs["name"]:
        mutation_info["desc"] = p.desc()
        # p.identifier_set.get(identifierType='geneName').identifierID
        mutation_info["gene"] = p.id

    # Set domains
    if reqs["dom"] or reqs["knownmuts"] or reqs["mut"]:
        ds = list(CoreModel.objects.filter(protein_id=p.id))

        pid_to_name = {}
        inacs = defaultdict(set)
        all_domain_range = set()
        all_interface_models = set()
        logger.debug("Going over all domains and interactions...")
        for d in ds:
            doms, defs, domain_range, interface_models = _get_domain_info(
                d, pid_to_name, inacs
            )
            mutation_info.setdefault("doms", []).append(doms)
            mutation_info.setdefault("defs", []).append(defs)
            all_domain_range.update(domain_range)
            all_interface_models.update(interface_models)

        inacsum = defaultdict(int)
        for aas in inacs.values():
            for aa in aas:
                inacsum[aa] += 1
        mutation_info["inacsum"] = inacsum

        mutation_info["inacs"] = sorted(
            [
                {"pid": k, "prot": pid_to_name[k], "aa": list(map(int, v))}
                for k, v in inacs.items()
            ],
            key=lambda x: x["prot"],
        )
    logger.debug("Done going over all domains and interactions!")
    logger.debug("mutation_info: {}".format(mutation_info))

    if reqs["mut"]:
        logger.debug("all_domain_range: {}".format(all_domain_range))
        # logger.debug("all_interface_models: {}".format(all_interface_models))
        logger.debug("mut: {}".format(mut))
        if int(mut[1:-1]) not in all_domain_range:
            mutation_info["error"] = True
            mutation_info["emsg"] = "OOD"

    # Set already known mutations for protein.
    logger.debug("knownmutsReq")
    if reqs["knownmuts"]:
        knMuts = _get_known_muts(p, ds, all_domain_range, all_interface_models)

        # output[idx]['prot'] = str(knMuts['537'])
        mutation_info["known"] = knMuts

    return mutation_info


def _get_domain_info(d, pid_to_name, interactions):
    doms = d.getname("")
    defs = d.getdefs(1)
    domain_range = set(range(int(defs.split(":")[0]), int(defs.split(":")[1]) + 1))
    interface_modes = set()

    # Set interactions.
    model1 = (
        InterfaceModel.objects.filter(domain1=d)
        .exclude(aa1__isnull=True)
        .exclude(aa1__exact="")
        .exclude(aa1__exact=",")
    )
    for m in model1:
        partner_protein_id = m.protein_id_2
        partner_protein_name = m.get_protein_name(2)
        pid_to_name[partner_protein_id] = partner_protein_name
        interactions[partner_protein_id] |= set(m.aa1.split(","))
        interface_modes.add((m, partner_protein_id, partner_protein_name))

    model2 = (
        InterfaceModel.objects.filter(domain2=d)
        .exclude(aa2__isnull=True)
        .exclude(aa2__exact="")
        .exclude(aa2__exact=",")
    )
    for m in model2:
        partner_protein_id = m.protein_id_1
        partner_protein_name = m.get_protein_name(1)
        pid_to_name[partner_protein_id] = partner_protein_name
        interactions[partner_protein_id] |= set(m.aa2.split(","))
        interface_modes.add((m, partner_protein_id, partner_protein_name))

    return doms, defs, domain_range, interface_modes


def _get_known_muts(p, ds, all_domain_range, all_interface_models):
    logger.debug(
        "_get_known_muts(%s, %s, %s, %s)", p, ds, all_domain_range, all_interface_models
    )
    mdict = {}
    muts = [
        (mut, None, None)
        for model in ds
        for mut in model.muts.exclude(ddG=None)
        if int(mut.mut[1:-1]) in all_domain_range
    ] + [
        (mut, partner_protein_id, partner_protein_name)
        for (model, partner_protein_id, partner_protein_name) in all_interface_models
        for mut in model.muts.filter(protein_id=p.id).exclude(ddG=None)
        if int(mut.mut[1:-1]) in all_domain_range
    ]
    logger.debug("muts: '{}'".format(muts))
    logger.debug("done querying mutations...")

    mut_dbs = findInDatabase([m[0].mut for m in muts], p.id)

    logger.debug("Done 'findInDatabase'")

    # Skip core mutations not in any database.
    muts = [
        m
        for m in muts
        if (
            (isinstance(m[0], (CoreMutationLocal, InterfaceMutationLocal)))
            or (
                isinstance(m[0], (CoreMutation, InterfaceMutation))
                and len(mut_dbs[m[0].mut])
            )
        )
    ]
    # If still > 100 mutations, keep residues with the largest number of mutants

    if len(muts) > MAX_NUM_MUTATIONS:
        mutated_residue_counts = Counter([m[0].mut[:-1] for m in muts])
        most_common_mutated_residues = {
            x[0] for x in mutated_residue_counts.most_common(MAX_NUM_MUTATIONS)
        }
        muts = [m for m in muts if m[0].mut[:-1] in most_common_mutated_residues]

    for m_tuple in muts:
        m, partner_protein_id, partner_protein_name = m_tuple
        chain = m.findChain()
        isInt = partner_protein_name
        iId = partner_protein_id

        mut_dbs_html = ""
        if mut_dbs[m.mut]:
            mut_dbs_html = (
                "Mutation in database" + ("s" if len(mut_dbs[m.mut]) > 1 else "") + ": "
            )
            for i, db in enumerate(mut_dbs[m.mut]):
                if i:
                    mut_dbs_html += ", "
                mut_dbs_html += (
                    '<a target="_blank" href="' + db["url"] + '">' + db["name"] + "</a>"
                )
        else:
            mut_dbs_html = "Mutation run by user"

        toAppend = {
            "i": isInt,
            "id": iId,
            "m": m.mut,
            "d": "%0.3f" % m.ddG,
            "dw": m.dGwt(),
            "dm": m.dGmut(),
            "si": m.model.getsequenceidentity(chain),
            "sm": "%0.3f" % m.model.dope_score,
            "db": mut_dbs_html,
            "elaspic_version": m.elaspic_version,
        }
        if m.mut in mdict and mdict[m.mut][0]["i"]:
            mdict[m.mut].append(toAppend)
        else:
            mdict[m.mut] = [toAppend]

    knMuts = {}

    for k in mdict:
        mnum = mdict[k][0]["m"][1:-1]
        knMuts.setdefault(mnum, list()).append(mdict[k])

    # Sort mutations
    for k in knMuts:
        knMuts[k] = sorted(knMuts[k], key=lambda x: int(x[0]["m"][1:-1]))
    return knMuts


def _get_errors(output):
    """Save and count all errors."""
    errDict = {
        "SNX": {},  # syntax error
        "DNE": {},  # protein not found
        "SLF": {},  # mutation: self error
        "DUP": {},  # duplicate
        "SYN": {},  # synonym
        "OOB": {},  # mutation: out of bounds or wrong residue error
        "OOD": {},  # mutation falls outside of a domain
    }
    errIdx = {
        "SNX": 0,
        "DNE": 1,
        "OOB": 2,
        "SLF": 3,
        "DUP": 4,
        "SYN": 5,
        "OOD": 6,
    }
    good = []
    err = {
        "errors": [[] for _ in range(len(errDict))],
        "header": [],
        "eclass": [],
        "good": good,
        "title": False,
    }

    for prot in output:
        if prot["emsg"] == "EMP":
            continue
        if prot["error"]:
            idx = "emsg"
        elif prot["muterr"]:
            idx = "muterr"
        else:
            good.append(prot["iden"])
            continue
        if not prot["iden"] in errDict[prot[idx]]:
            errDict[prot[idx]][prot["iden"]] = 1
        else:
            errDict[prot[idx]][prot["iden"]] += 1

    # Translate to list of format "PROT.MUT (1x)"
    for eidx in errDict:
        err["errors"].append([])
        for prot in errDict[eidx]:
            if errDict[eidx][prot] == 1:
                err["errors"][errIdx[eidx]].append("<b>%s</b>" % prot)
            else:
                err["errors"][errIdx[eidx]].append(
                    "<b>%s</b> (x%d)" % (prot, errDict[eidx][prot])
                )

    # Assign headeres to error lists.
    errLists = 0
    for idx, errls in enumerate(err["errors"]):
        err["header"].append(None)
        err["eclass"].append(None)
        if len(errls) > 0:
            errLists += 1
            title, header, myclass = _get_error_info(idx, len(errls) == 1)
            err["header"][idx] = "%s (%d):" % (header, len(errls))
            err["eclass"][idx] = myclass
    if errLists == 1:
        err["title"] = title
    if errLists > 1:
        err["title"] = "There are multiple errors."
    return err


def _get_error_info(idx, is_single_error):
    if is_single_error:
        if idx == 0:
            title = "There is a line with invalid syntax."
        elif idx == 1:
            title = "There is an unrecognized gene symbol."
        elif idx == 2:
            title = "There is an unrecognized protein residue."
        elif idx == 3:
            title = "There is a synonymous mutation."
        elif idx == 4:
            title = "There is a duplicated gene symbol."
        elif idx == 5:
            title = "There is a duplicated gene symbol."
        elif idx == 6:
            title = "Mutation falls outside of a protein domain."
    else:
        if idx == 0:
            title = "There are lines with invalid syntax."
        elif idx == 1:
            title = "There are unrecognized gene symbols."
        elif idx == 2:
            title = "There are unrecognized protein residues."
        elif idx == 3:
            title = "There are synonymous mutations."
        elif idx == 4:
            title = "There are duplicate gene symbols."
        elif idx == 5:
            title = "There are duplicate gene symbols."
        elif idx == 6:
            title = "Mutations fall outside of protein domains."
    if idx == 0:
        header = "Invalid syntax"
        myclass = "error"
    elif idx == 1:
        header = "Unrecognized gene symbols"
        myclass = "unknown"
    elif idx == 2:
        header = "Unrecognized protein residues"
        myclass = "unknown"
    elif idx == 3:
        header = "Synonymous mutations"
        myclass = "warning"
    elif idx == 4:
        header = "Duplicates"
        myclass = "warning"
    elif idx == 5:
        header = "Synonyms"
        myclass = "warning"
    elif idx == 6:
        header = "Outside of structural domain"
        myclass = "warning"
    return title, header, myclass


def contactmail(request):
    # Check if the page was reached legitimately.
    if not request.POST:
        raise Http404
    if not any(x in request.POST for x in ["name", "from", "topic", "msg"]):
        raise Http404

    from_email = request.POST["from"]
    subject = "ELASPIC: " + request.POST["topic"]

    message = "<i>From: " + html.strip_tags(request.POST["name"]) + "<br />"
    message += "Email: " + html.strip_tags(from_email) + "</i><br /><br />"
    message += (
        "Topic: <b>" + html.strip_tags(request.POST["topic"]) + "</b><br /><br />"
    )
    message += "Message: <br /><b>"
    message += html.strip_tags(request.POST["msg"]).replace("\n", "<br/>")
    message += "</b>"

    email = EmailMessage(
        subject,
        message,
        "ELASPIC-webserver@kimlab.org",
        [a[1] for a in settings.ADMINS],
    )
    email.headers = {"Reply-To": from_email, "From": "ELASPIC-webserver@kimlab.org"}
    email.content_subtype = "html"

    try:
        email.send()
    except Exception:
        error = True
        response = "Sorry, there was an error with your request. Please try again."
    else:
        error = False
        response = (
            "Your message has been successfully sent. "
            "Allow us 2 business days to get back to you."
        )
    return HttpResponse(
        json.dumps({"response": response, "error": error}),
        content_type="application/json",
    )
