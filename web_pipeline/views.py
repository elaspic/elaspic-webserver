import logging
import os
import pickle
from shutil import copyfile
from tempfile import mkdtemp

import requests
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.utils.timezone import now

from . import functions as fn
from . import conf
from .functions import fetchProtein, getPnM, getResultData, isInvalidMut, sendEmail
from .models import (
    CoreModel,
    CoreMutation,
    InterfaceMutation,
    Job,
    JobToMut,
    Mut,
    Protein,
    ProteinLocal,
    _CoreMutation,
    _InterfaceMutation,
    findInDatabase,
)

logger = logging.getLogger(__name__)


try:
    os.environ["MPLCONFIGDIR"] = mkdtemp()
    from pipeline.code.elaspic import blacklisted_uniprots
except ImportError:
    blacklisted_uniprots = []


def inp(request, p):
    context = {
        "current": p,
        "type": "input",
        "test": request.META.get("HTTP_HOST", ""),
        "conf": conf,
    }
    return render(request, p + ".html", context)


def runPipeline(request):
    logger.debug("request: {}".format(request.GET))

    # Check for valid request.
    if not request.GET:
        raise Http404
    if not ("proteins" in request.GET) or not ("email" in request.GET):
        raise Http404
    if not request.GET["proteins"].strip():
        return HttpResponseRedirect("/")  # No protein input.

    # Check if running local pdb.
    if "jid" in request.GET and "chain" in request.GET and request.GET["chain"]:
        local = True
        mut = request.GET["proteins"].split(".")[-1]
        filename = request.GET["fileToUpload"]

        # Create job in database.
        random_id = request.GET["jid"]
        user_path = fn.get_user_path(random_id)
        chain = request.GET["chain"]

        with open(os.path.join(user_path, "pdb_parsed.pickle"), "rb") as f:
            seq = pickle.load(f)[int(chain)][1]  # list of (chain_id, chain_seq)
        with open(os.path.join(user_path, "input.fasta"), "w") as f:
            f.write(">input.pdb\n")
            f.write(seq)
        if isInvalidMut(mut, seq):
            logger.error(
                "Mutation '{}' if not valid for sequence '{}'".format(mut, seq)
            )
            return HttpResponseRedirect("/")

        j = Job.objects.create(
            jobID=random_id,
            email=request.GET["email"],
            browser=request.META["HTTP_USER_AGENT"],
            localID=random_id,
        )

        m = Mut.objects.create(
            protein=random_id, mut=mut, chain=chain, status="running"
        )

        JobToMut.objects.create(job=j, mut=m, inputIdentifier=filename)

    else:
        local = False
        # Generate list of valid proteins and mutations.
        pnms = request.GET["proteins"].split(" ")[:10000]
        logger.debug("pnms: {}".format(pnms))
        validPnms = []
        for pnm in pnms:
            iden, mut = getPnM(pnm)
            p = fetchProtein(iden)
            if not p:
                logger.error(
                    "Could not fetch protein for pnm: '{}', iden: '{}', mut: '{}'".format(
                        pnm, iden, mut
                    )
                )
                continue
            if isInvalidMut(mut, p.seq):
                logger.error(
                    "Invalid mutation for pnm: '{}', iden: '{}', mut: '{}'".format(
                        pnm, iden, mut
                    )
                )
                continue
            validPnms.append([p.id, mut, iden])
        if not validPnms:
            return HttpResponseRedirect("/")  # No valid proteins.
        logger.debug("validPnms: {}".format(validPnms))

        random_id = fn.get_random_id()
        j = Job.objects.create(
            jobID=random_id,
            email=request.GET["email"],
            browser=request.META["HTTP_USER_AGENT"],
        )

        # Create mutations in database if not already there.
        newMuts, doneMuts = [], []

        for pnm in validPnms:
            toRerun = False
            m = list(Mut.objects.filter(protein=pnm[0], mut=pnm[1]))
            #        # Check for blacklisted uniprots and skip.
            #        if pnm[0] in blacklisted_uniprots:
            #            if m:
            #                mut = m[0]
            #                mut.status = 'error'
            #                mut.affectedType = ''
            #                mut.error = '5: Blacklisted'
            #                mut.save()
            #                doneMuts.append([mut, pnm[2]])
            #            else:
            #                doneMuts.append([Mut.objects.create(protein=pnm[0], mut=pnm[1],
            #                                                    status='error',
            #                                                    error='5: Blaclisted'), pnm[2]])
            #            checkForCompletion(doneMuts[-1][0].jobs.all())
            #            continue

            # Get potential results.
            muts = list(CoreMutation.objects.filter(protein_id=pnm[0], mut=pnm[1]))
            imuts = list(
                InterfaceMutation.objects.filter(protein_id=pnm[0], mut=pnm[1])
            )

            if m:
                mut = m[0]
                typ = mut.affectedType

                # Add rerun mutations to run list. Reasons:
                # 1) Mutation data disappeared from ELASPIC database.
                # 2) Mutation data changed from core to interface.
                # 3) Mutation data changed from not in domain.
                # 4) Pipeline crashed or ran out of time on last run.
                if (
                    (typ == "CO" and not muts)
                    or (typ == "IN" and not imuts)
                    or (typ == "CO" and imuts)
                    or (typ == "NO" and (muts or imuts))
                    or (mut.error and (mut.error[0] != "1"))
                ):
                    toRerun = True

                # Add mutations to lists.
                # if toRerun and not(mut.rerun):  # AS
                if toRerun:
                    mut.rerun = True
                    mut.save()
                    newMuts.append([mut, pnm[2]])
                else:
                    doneMuts.append([mut, pnm[2]])
            else:
                # Create new mutations if the result isn't already complete.
                if (muts and not imuts and all(mut.ddG for mut in muts)) or (
                    imuts and all(mut.ddG for mut in imuts)
                ):
                    doneMuts.append(
                        [
                            Mut.objects.create(
                                protein=pnm[0],
                                mut=pnm[1],
                                status="done",
                                affectedType="IN" if imuts else "CO",
                                dateFinished=now(),
                            ),
                            pnm[2],
                        ]
                    )
                else:
                    newMuts.append(
                        [Mut.objects.create(protein=pnm[0], mut=pnm[1]), pnm[2]]
                    )

        # Link all mutations to job.
        JobToMut.objects.bulk_create(
            [
                JobToMut(job=j, mut=allMuts[0], inputIdentifier=allMuts[1])
                for allMuts in doneMuts + newMuts
            ]
        )

    # ##### Run pipeline #####

    if local:
        data_in = {
            "job_id": j.jobID,
            "job_email": j.email,
            "job_type": "local",
            "secret_key": conf.JOBSUBMITTER_SECRET_KEY,
            "mutations": [
                {
                    "protein_id": random_id,
                    "mutations": "{}_{}".format(int(chain) + 1, mut),
                    "structure_file": "input.pdb",
                    # 'sequence_file': 'input.fasta',
                }
            ],
        }
    else:
        # Run pipeline for new mutations.
        data_in = {
            "job_id": j.jobID,
            "job_email": j.email,
            "job_type": "database",
            "secret_key": conf.JOBSUBMITTER_SECRET_KEY,
            "mutations": [],
        }
        for m in newMuts:
            mut = m[0]
            mut.status = "running"
            # mut.taskId = p.task_ids
            mut.save()
            data_in["mutations"].append(
                {
                    "protein_id": mut.protein,
                    "mutations": mut.mut,
                    "uniprot_domain_pair_ids": "",
                }
            )

    if data_in:
        status = None
        n_tries = 0
        while (not status or status == "error") and n_tries < 10:
            n_tries += 1
            r = requests.post("http://localhost:8001/elaspic/api/1.0/", json=data_in)
            if not r.ok:
                logger.error("Bad response from jobsubmitter server: {}".format(r))
                continue
            status = r.json().get("status", None)
            logger.debug("status: {}".format(status))
    else:
        logger.debug(
            "No data! All mutations are done? newMuts: {}, doneMuts: {}".format(
                newMuts, doneMuts
            )
        )

    if local:
        sendEmail(j, "started")
    else:
        # Set job to done if all mutations are already done.
        if all(
            [
                (
                    True
                    if (m[0].status == "done" or m[0].status == "error")
                    and not (m[0].rerun)
                    else False
                )
                for m in newMuts + doneMuts
            ]
        ):
            j.isDone = True
            j.dateFinished = now()
            j.save()
            # Send completion email.
            sendEmail(j, "complete")
        if not j.isDone:
            # Send start email.
            sendEmail(j, "started")

    # Redirect to result page.
    return HttpResponseRedirect(
        "http://%s/result/%s/" % (request.get_host(), random_id)
    )


def displayResult(request):
    logger.debug("displayResult({})".format(request))

    # Check if request ID is legit.
    requestID = request.path.split("/")[2]
    try:
        job = Job.objects.get(jobID=requestID)
    except Job.DoesNotExist:
        raise Http404

    # # Fetch data
    # local = True if job.localID else False

    #    if job.localID:
    #        m = getLocalData(job.jobtomut_set.first())
    #        if m.realMut:
    #            # Alignscore and seqid are already there.
    #            m.realMut[0].pdbtemp = m.inputIdentifier
    #            # Get interacting protein.
    #            # TODO: Add interactions if there.
    #        data = [m]

    jtoms = job.jobtomut_set.all()
    j = jtoms[0].job
    if not j.isDone:
        job_is_done = True
        for jtom in jtoms:
            running_time = jtom.mut.dateAdded - now()
            if running_time.total_seconds() > 86400:  # 1 day
                jtom.mut.status = "error"
                jtom.mut.error = "3: OUTATIME"
                jtom.mut.save()
            if jtom.mut.status not in ["done", "error"]:
                job_is_done = False
        if job_is_done:
            j.isDone = True
            j.dateFinished = now()
            j.save()

    data = [getResultData(jtom) for jtom in jtoms]
    logger.debug("data: {}".format(data))

    for m in data:
        logger.debug("m: {}".format(m))
        logger.debug("m.realMut: {}".format(m.realMut))
        logger.debug("m.realMutErr: {}".format(m.realMutErr))

        doneInt, toRemove = [], []
        # Set mutation status temporarily as 'running' if its rerunning.
        #            if m.mut.rerun and not(job.isDone):
        #                if m.mut.rerun == 2:
        #                    m.mut.status = 'running'
        #                else:
        #                    m.mut.status = 'queued'

        # Get additional data for result table.
        if not m.realMutErr:
            print(len(m.realMut))
            for i, mut in enumerate(m.realMut):
                chain = mut.findChain()
                # Get alignment scores.
                mut.alignscore = mut.model.getalignscore(chain)
                mut.seqid = mut.model.getsequenceidentity(chain)
                mut.pdbtemp = mut.model.getpdbtemplate(chain, link=False)
                # Get interacting protein.
                if isinstance(mut, _InterfaceMutation):
                    d = mut.getdomain(1 if chain == 2 else 2)
                    if d.protein_id == m.mut.protein:
                        mut.inac = "self"
                    else:
                        mut.inac = d.get_protein_name()

                    # AS: don't know what's going on here but errors so skip...
                    mut.inacd = "h%d" % d.id if mut.inac == "self" else "n%d" % d.id
                    # Check for dublicates. Remove the last one.
                    # This is a quick and dirty fix and should be fixed to pick
                    # the highest sequence identity.
                    dubkey = "%s.%s.%d" % (m.mut.protein, m.mut.mut, d.id)
                    if dubkey in doneInt:
                        toRemove.append(i)
                    else:
                        doneInt.append(dubkey)
            m.realMut = [m for i, m in enumerate(m.realMut) if i not in toRemove]

    context = {
        "url": "http://%s/result/%s/" % (request.get_host(), requestID),
        "type": "result",
        "current": "result",
        "isRunning": not (job.isDone),
        "job": job,  # {'jobID': 'asd'},
        "data": data,
        "conf": conf,
    }
    logger.debug("job: {}".format(job))
    logger.debug("context: {}".format(context))
    logger.debug("context.data: {}".format([d.realMut for d in context["data"]]))
    return render(request, "result.html", context)


def displaySecondaryResult(request):
    logger.debug("displaySecondaryResult({})".format(request))

    # Check URL for session change.
    if request.GET:
        if "j" in request.GET:
            request.session["jmol"] = request.GET["j"]
            url = (
                request.path
                if not ("p" in request.GET)
                else request.path + "?p=" + request.GET["p"]
            )
            return HttpResponseRedirect(url)

    # Check jmol mode.
    mode = request.session["jmol"] if "jmol" in request.session else "HTML5"

    # Set initial protein if requested
    initialProtein, initialHomodimer = False, None
    if "p" in request.GET:
        initialProtein = int(request.GET["p"][1:])
        initialHomodimer = True if request.GET["p"][0] == "h" else False
    logger.debug("initialProtein: {}".format(initialProtein))
    logger.debug("initialHomodimer: {}".format(initialHomodimer))

    curmut, curdom = None, None

    # Get protein and mutation from url request.
    currentIDs = request.path.split("/")  # Job[2], Mut[3]
    job = currentIDs[2]
    iden, mut = getPnM(currentIDs[3])
    returnUrl = "http://%s/result/%s/" % (request.get_host(), job)
    mutNum = int(mut[1:-1])

    # Get the mutation information or send back to main job URL.
    jtom = list(JobToMut.objects.filter(mut__mut=mut, inputIdentifier=iden, job_id=job))
    if len(jtom) != 1:
        return HttpResponseRedirect(returnUrl)
    m = jtom[0].mut
    j = Job.objects.get(jobID=job)
    local = True if j.localID else False

    if m.status != "done":
        # Mutation is not done.
        return HttpResponseRedirect(returnUrl)

    loadEverything = m.affectedType != "NO"

    # Load structure data if mutation was successful.
    intmuts = []
    # inCore = True if m.affectedType == 'CO' or m.affectedType == 'NO' else False
    inCore = not initialProtein
    data = getResultData(jtom[0])
    logger.debug("data: '{}'".format(data))

    if loadEverything:
        if data.realMutErr == "DNE":
            return render(
                request,
                "result2.html",
                {
                    "url": returnUrl,
                    "current": "result2",
                    "job": j,
                    "data": data,
                    "dbError": True,
                },
            )

        # Create pdb folder if not accessed before.
        pdbpath = os.path.join(conf.SAVE_PATH, job, currentIDs[3])
        if not os.path.exists(pdbpath):
            original_umask = os.umask(0)
            try:
                os.makedirs(pdbpath, 0o777)
            finally:
                os.umask(original_umask)
        fileError = False

        doneInt, toRemove = [], []
        for i, mu in enumerate(data.realMut):
            assert isinstance(mu, (_CoreMutation, _InterfaceMutation))
            # inCore = isinstance(mu, _CoreMutation) and not initialProtein

            if isinstance(mu, _CoreMutation):
                # CORE
                if not inCore:
                    toRemove.append(i)
                    continue
                # Transfer PDBs if not done before.
                copyfrom = os.path.join(conf.DB_PATH, data.realMut[0].model.data_path)
                if not os.path.exists(os.path.join(pdbpath, "wt.pdb")):
                    try:
                        copyfile(
                            os.path.join(copyfrom, data.realMut[0].model_filename_wt),
                            os.path.join(pdbpath, "wt.pdb"),
                        )
                    except Exception as e:
                        logger.error("Filerror: {}".format(e))
                        fileError = e
                if not os.path.exists(os.path.join(pdbpath, "mut.pdb")):
                    try:
                        copyfile(
                            os.path.join(copyfrom, data.realMut[0].model_filename_mut),
                            os.path.join(pdbpath, "mut.pdb"),
                        )
                    except Exception as e:
                        logger.error("Filerror: {}".format(e))
                        fileError = e

            elif isinstance(mu, _InterfaceMutation):
                # INTERFACE
                if inCore:
                    toRemove.append(i)
                    continue
                # Get interacting domain.
                chain = 2 if mu.findChain() == 1 else 1
                d = mu.model.getdomain(chain)

                # Check for dublicates. Remove the last one.
                # This is a quick and dirty fix and should be fixed to pick
                # the highest sequence identity.
                dubkey = "%s.%s.%d" % (m.protein, m.mut, d.id)
                if dubkey in doneInt:
                    toRemove.append(i)
                    continue
                else:
                    doneInt.append(dubkey)

                intmuts.append({"mut": mu, "domain": d})

                # Transfer PDBs if not done before.
                copyfrom = os.path.join(conf.DB_PATH, mu.model.data_path)
                copyto = os.path.join(pdbpath, str(d.id))
                if not os.path.exists(copyto + "wt.pdb"):
                    try:
                        copyfile(
                            os.path.join(copyfrom, mu.model_filename_wt),
                            copyto + "wt.pdb",
                        )
                    except Exception as e:
                        logger.error("Filerror: {}".format(e))
                        fileError = e
                if not os.path.exists(copyto + "mut.pdb"):
                    try:
                        copyfile(
                            os.path.join(copyfrom, mu.model_filename_mut),
                            copyto + "mut.pdb",
                        )
                    except Exception as e:
                        logger.error("Filerror: {}".format(e))
                        fileError = e

        data.realMut = [
            data.realMut[i] for i in range(len(data.realMut)) if i not in toRemove
        ]

        # Show error page if database fetching failed.
        if fileError:
            # Could not read mutation from database. Return error.
            logger.error("{}: {}".format(type(fileError), fileError))
            return render(
                request,
                "result2.html",
                {
                    "url": returnUrl,
                    "current": "result2",
                    "job": j,
                    "data": data,
                    "dbError": True,
                },
            )

        p = data.realMut[0].protein
        logger.debug("p: {}".format(p))

    # Load domains if mutation failed.
    elif not loadEverything:
        p = (
            ProteinLocal.objects.get(id=m.protein)
            if local
            else Protein.objects.get(id=m.protein)
        )

    pSize = len(p.seq) + 0.0

    # Get domain information.
    barSize = 868 if inCore else 590
    border = 1
    mutLineSize = 2
    mutDescSize = 70
    ds, domainName, proteinToDomainID = [], "", {}
    prots = (
        [p]
        + ([mu["domain"].protein for mu in intmuts] if intmuts else [])
        # [p] + ([mu['domain'].protein for mu in intmuts] if intmuts else [])
    )

    logger.debug("intmuts: {}".format(intmuts))
    logger.debug("prots: '{}'".format(prots))
    for idx, prot in enumerate(prots):

        if local:
            chain_pos = 1 if not idx else 2
            pds = [m.getdomain(chain_pos) for m in data.realMut]
            # pds = list(CoreModelLocal.objects.filter(protein_id=prot.id))
        else:
            # chain_pos = 1 if not idx else 2
            # pds = [m.getdomain(chain_pos) for m in data.realMut]
            pds = list(CoreModel.objects.filter(protein_id=prot.id))

        logger.debug("pds: '{}'".format(pds))

        # Check if homodimer with self.
        homodimer = True if prot == p else False
        logger.debug("homodimer: '{}'".format(homodimer))

        try:
            logger.debug(
                "intmuts...: {}".format(
                    intmuts[idx - 1]["mut"].model.getdomain(1 if chain == 2 else 2).id
                )
            )
        except IndexError:
            logger.debug("intmuts...: None")

        for didx, pd in enumerate(pds):
            # Get domain definitions.
            defs = pd.getdefs(1)
            defstart = int(defs.split(":")[0])
            defend = int(defs.split(":")[1])
            dpSize = len(prot.seq) + 0.0
            pxSize = (defend - defstart) / dpSize * barSize - border * 2
            if pxSize < 0:
                pxSize = 0

            # If this is not an interaction.
            if idx == 0:
                # Color if mutaiton is in domain.
                index = 0
                isInDomain = True if defstart <= mutNum and defend >= mutNum else False
                if isInDomain:
                    domainName = pd.name

            # If this is an interaction.
            else:
                # Check if protein is already in list.
                if not didx:
                    notUnique = (
                        proteinToDomainID[prot.id]
                        if prot.id in proteinToDomainID
                        else False
                    )
                    if not notUnique:
                        proteinToDomainID[prot.id] = intmuts[idx - 1]["domain"].id
                    # Get chains for coloring.
                    chain = 1 if intmuts[idx - 1]["mut"].findChain() == 1 else 2
                    chainself = intmuts[idx - 1]["mut"].model.getchain(chain)
                    chaininac = intmuts[idx - 1]["mut"].model.getchain(
                        1 if chain == 2 else 2
                    )
                    # Get mutation info.
                    seqid = intmuts[idx - 1]["mut"].model.getsequenceidentity(chain)
                    pdbtemp = intmuts[idx - 1]["mut"].model.getpdbtemplate(chain)
                    dopescore = intmuts[idx - 1]["mut"].model.dope_score
                    dgwt = intmuts[idx - 1]["mut"].dGwt()
                    dgmut = intmuts[idx - 1]["mut"].dGmut()
                    ddg = intmuts[idx - 1]["mut"].getddG()
                    pdbmutnum = intmuts[idx - 1]["mut"].pdb_mut[1:-1]

                # Color if interacting with protein 1.
                index = intmuts[idx - 1]["domain"].id
                isInDomain = True if index == pd.id else False

            # Decrease domain name if it does not fit.
            if len(pd.name) * 7 < pxSize:
                dname = pd.name
                dpopup = ""
            elif 14 < pxSize:
                dname = pd.name[: max(int(pxSize / 7) - 2, 0)] + ".."
                dpopup = pd.name
            else:
                dname = ""
                dpopup = pd.name

            # Save domain info in list.
            # <i>, name, popup, pxstart, pxsize, start, end, status, psize.
            if not didx:
                ds.append([])
            protName = prot.getname()
            ds[idx].append(
                [
                    index,
                    dname,
                    dpopup,
                    int(defstart / dpSize * barSize),
                    int(pxSize),
                    defstart,
                    defend,
                    isInDomain,
                    int(dpSize),
                    prot.id,
                    prot.desc(),
                    homodimer if idx else None,
                    chainself if idx else None,
                    chaininac if idx else None,
                    notUnique if idx else None,
                    protName,
                    seqid if idx else None,
                    dopescore if idx else None,
                    dgwt if idx else None,
                    dgmut if idx else None,
                    ddg if idx else None,
                    pdbmutnum if idx else None,
                    pdbtemp if idx else None,
                ]
            )
            # if prot.name.split('_')[0] == 'UBC':
            # o += prot.name.split('_')[0] + ', '
            # AS
            logger.debug("pd.id: {}, idx: {}, didx: {}".format(pd.id, idx, didx))
            if idx:
                _domain_id = (
                    intmuts[idx - 1]["mut"].model.getdomain(1 if chain == 2 else 2).id
                )
                if pd.id == initialProtein and _domain_id == initialProtein:
                    curdom = ds[idx]
                    curmut = intmuts[idx - 1]["mut"]
                    curmut.seqid = seqid if idx else None
                    curmut.pdbtemp = pdbtemp if idx else None
    pxMutnum = mutNum / pSize * barSize - mutLineSize / 2
    if pxMutnum < 0:
        pxMutnum = 0

    logger.debug("curdom: {}".format(curdom))
    logger.debug("curmut: {}".format(curmut))
    logger.debug("data.realMut: {}".format(data.realMut))
    logger.debug("ds: {}".format(ds))

    if not curmut:
        curmut = data.realMut[0] if inCore else data.realMut[-1]  # AS: indexerror?
        curdom = None if inCore else ds[1]

    if loadEverything:
        if not ("[" in curmut.pdb_mut):
            pdbMutNum = int(curmut.pdb_mut[1:-1])
        else:
            pdbMutNum = int(curmut.pdb_mut[2:-2])
    else:
        data = {"inputIdentifier": iden, "mut": {"mut": mut, "desc": p.desc()}}

    # Get the domains interacting.
    d2 = None
    if curdom:
        for dom in curdom:
            if dom[7]:
                d2 = dom
        # AS hacking
        if d2 is None and not inCore:
            d2 = curdom[-1]

    d1 = None
    for dom in ds[0]:
        if dom[7]:
            d1 = dom
    if d1 is None:
        # This occurs if the mutation is outside every domain
        # for example when interface domain definitions don't line up
        # with core domain definitions, and an interface mutation
        # is outside all core domains.
        d1 = ds[0][0]

    logger.debug("curdom: {}".format(curdom))
    logger.debug("d2: {}".format(d2))

    # Get domain interaction values for 2dbar.
    if d2:
        logger.debug("d1: {}".format(d1))
        # Set start and end for each domain.
        d1s, d1e = d1[3], d1[3] + d1[4]
        d2s, d2e = d2[3], d2[3] + d2[4]
        # Find width of overlap/space.
        midleft = min(max(d1s, d2s), min(d1e, d2e))
        midright = max(max(d1s, d2s), min(d1e, d2e))
        midwidth = midright - midleft
        # Find width outside overlap/space.
        first_d = d1 if d1[3] <= d2[3] else d2
        last_d = d1 if d1[3] + d1[4] >= d2[3] + d2[4] else d2
        notfirst_d = d1 if first_d == d2 else d2
        # If complete overlap.
        if first_d == last_d:
            overlap = True
            leftwidth = notfirst_d[3] - first_d[3]
            rightwidth = (last_d[3] + last_d[4]) - (notfirst_d[3] + notfirst_d[4])
        # If overlap in one end.
        elif first_d[3] + first_d[4] > last_d[3]:
            overlap = True
            leftwidth = last_d[3] - first_d[3]
            rightwidth = (last_d[3] + last_d[4]) - (first_d[3] + first_d[4])
        # If no overlap.
        else:
            overlap = False
            leftwidth = first_d[4]
            rightwidth = last_d[4]
        # Find which direction the overlap is going.
        leftside = "down" if first_d == d1 else "up"
        rightside = "up" if last_d == d1 else "down"
        midside = "solid" if overlap else leftside
        # Calculate heights
        fullheight = 80
        if overlap:
            leftheight = rightheight = fullheight / 2
            midtopheight = midbotheight = fullheight / 4
        else:
            leftheight = (fullheight * first_d[4] / (midwidth + first_d[4])) / 2
            rightheight = (fullheight * last_d[4] / (midwidth + last_d[4])) / 2
            midtopheight = (
                fullheight / 2 - rightheight
                if leftside == "down"
                else fullheight / 2 - leftheight
            )
            midbotheight = (
                fullheight / 2 - leftheight
                if leftside == "down"
                else fullheight / 2 - rightheight
            )

    # Find if mutation is in database.
    mut_dbs = findInDatabase([data.mut.mut], data.mut.protein)
    mut_dbs_html = ""
    if mut_dbs[m.mut]:
        mut_dbs_html = (
            "Mutation in database" + ("s" if len(mut_dbs[m.mut]) > 1 else "") + ": "
        )
        for i, db in enumerate(mut_dbs[m.mut]):
            if i:
                mut_dbs_html += " ,"
            mut_dbs_html += (
                '<a target="_blank" href="' + db["url"] + '">' + db["name"] + "</a>"
            )
    else:
        mut_dbs_html = "Mutation run by user"

    context = {
        "url": returnUrl,
        "current": "result2",
        "job": j,
        "size": pSize,
        "domains": ds,
        "curdomain": (
            [[xx if xx is not None else "" for xx in x] for x in curdom]
            if curdom is not None
            else [[""]]
        ),
        "conf": conf,
        "curmut": curmut,
        # 'type': 'result',
        "barsize": barSize,
        "mutnum": pdbMutNum if loadEverything else 0,
        "mutnumdiff": mutNum - pdbMutNum if loadEverything else 0,
        "pxmutnum": pxMutnum,
        "pxmutdesc": pxMutnum - mutDescSize / 2 + mutLineSize / 2,
        "domainname": domainName,
        "wtpdb": "4BHB",
        "mutpdb": "4BHC_R37L",
        "selectrange": range(0, 11),
        "data": data,
        "reverselabel": "true" if m.mut[-1] == "G" else "false",
        "jmolmode": mode,
        "loadeverything": loadEverything,
        # 'intmuts': intmuts,
        "inInt": not (inCore),
        "initialp": initialProtein,
        "initialh": initialHomodimer,
        "mut_dbs_html": mut_dbs_html + ".",
        "protein2dinac": {
            "full_height": fullheight if not inCore else 0,
            "mid_left": midleft if not inCore else 0,
            "mid_width": midwidth if not inCore else 0,
            "left_width": leftwidth if not inCore else 0,
            "right_width": rightwidth if not inCore else 0,
            "mid_side": midside if not inCore else 0,
            "left_side": leftside if not inCore else 0,
            "right_side": rightside if not inCore else 0,
            "left_height": leftheight if not inCore else 0,
            "right_height": rightheight if not inCore else 0,
            "mid_top_height": midtopheight if not inCore else 0,
            "mid_bot_height": midbotheight if not inCore else 0,
            "self_start": d1[3] if not inCore else 0,
            "self_width": d1[4] if not inCore else 0,
        },
    }
    logger.debug("context:\n{}".format(context))

    # <i>, name, popup, pxstart, pxsize, start, end, status, psize

    return render(request, "result2.html", context)


def jsmolpopup(request):
    return render(request, "jmolpopup.html", {})


def genericSite(request, site):

    context = {"this": site, "current": "generic"}
    context[site] = True

    if site == "help":
        pass
    elif site == "reference":
        pass
    elif site == "contact":
        pass

    return render(request, "generic.html", context)


# return render(request, 'test.html', {'msg': 'test'})
