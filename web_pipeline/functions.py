import os
import os.path as op
import re
import random
import time
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import now
from django.db.models import Q

from mum.settings import DB_PATH
from web_pipeline.models import (
    Job,
    HGNCIdentifier, UniprotIdentifier,
    Protein, ProteinLocal,
    CoreMutation, CoreMutationLocal,
    InterfaceMutation, InterfaceMutationLocal,
)

logger = logging.getLogger(__name__)


def get_random_id():
    """
    Return unique id for `column`.

    Returns
    -------
        random_id : str
            A unique id for the `jobID` / `localID` columns.
    """
    while True:
        random_id = "%06x" % random.randint(1, 16777215)
        user_path = op.join(DB_PATH, 'user_input', random_id)
        is_valid = (
            Job.objects.filter(Q(jobID=random_id) | Q(localID=random_id)).count() == 0 and
            not op.exists(user_path)
        )
        if is_valid:
            try:
                os.makedirs(user_path)
                return random_id
            except (OSError, FileExistsError):
                pass
        time.sleep(0.1)


def get_user_path(random_id):
    return op.join(DB_PATH, 'user_input', random_id)


def checkForCompletion(jobs):
    for j in jobs:
        jms = list(
            j.muts.filter(Q(status='queued') | Q(status='running') | Q(rerun=1) | Q(rerun=2))
        )
        if not(jms) and not(j.isDone):
            j.isDone = True
            j.dateFinished = now()
            j.save()
            sendEmail(j, 'complete')


# def getLocalData(jtom):
#    j = jtom.job
#    j.dateVisited = now()
#    j.save()
#
#    # Try to get data if not in web-server database yet.
#    aType = jtom.mut.affectedType
#    if not aType:
#        try:
#            jtom.realMut = [CoreMutation.objects.get(unique_id=j.id)]
#            if jtom.realMut.idx2 == -1:
#                aType = jtom.mut.affectedType = 'CO'
#            else:
#                aType = jtom.mut.affectedType = 'IN'
#            jtom.mut.save()
#        except:
#            jtom.realMut = []
#    return jtom


def getResultData(jtom):
    """
    """
    logger.debug("getResultData({})".format(jtom))

    # Update job last visited to now.
    j = jtom.job
    j.dateVisited = now()
    # j.save()

    local = True if j.localID else False
    CM = CoreMutationLocal if local else CoreMutation
    IM = InterfaceMutationLocal if local else InterfaceMutation
    aType = jtom.mut.affectedType
    logger.debug("aType: {}".format(aType))

    jtom.realMutErr = None

    jtom.realMut = list(
        CM.objects.filter(protein_id=jtom.mut.protein, mut=jtom.mut.mut)
    )
    if aType == 'IN':
        jtom.realMut += list(
            IM.objects.filter(protein_id=jtom.mut.protein, mut=jtom.mut.mut)
        )

    # Return one by one
    if aType == 'CO':
        if len(jtom.realMut) > 1:
            # With overlapping domains, pick first highest sequence identity,
            # then lowest model score.
            muts = sorted(jtom.realMut, key=lambda m: m.model.seq_id, reverse=True)
            highestSeqID = []
            for m in muts:
                if m.model.seq_id < muts[0].model.seq_id:
                    break
                else:
                    highestSeqID.append(m)
            jtom.realMut = [min(highestSeqID, key=lambda m: m.model.dope_score)]
        return jtom

    if aType == 'IN':
        jtom.realMut = [m for m in jtom.realMut if not m.mut_errors]
        return jtom

    if jtom.realMut:
        jtom.realMutErr = 'NOT'  # not in core or in interface.
        return jtom

    if not jtom.realMut:
        jtom.realMutErr = 'DNE'  # does not exists.
        jtom.realMut = [CM()]
        return jtom

    jtom.realMutErr = 'OTH'  # other.
    return jtom


def sendEmail(j, sendType):
    """Send email to user.

    Used by the jobsubmitter. Do not remove!

    Parameters
    ----------
    j : job | tuple
    sendType

    Returns
    -------

    """
    if isinstance(j, (list, tuple)):
        job_id, job_email = j
    else:
        job_id, job_email = j.jobID, j.email

    # Validate email address
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:[a-zA-Z]{2,4}|museum)$', job_email):
        return 0

    # Set Subject and content.
    if sendType == 'started':
        subject, status = 'started', 'has been correctly STARTED'
    elif sendType == 'complete':
        subject, status = 'results', 'is COMPLETE'

    # Prepare template and email object.
    sendSubject = '%s %s - Job ID: %s' % (settings.SITE_NAME, subject, job_id)
    html_content = render_to_string('email.html', {'JID': job_id,
                                                   'SITE_NAME': settings.SITE_NAME,
                                                   'SITE_URL': settings.SITE_URL,
                                                   'SUPPORT_EMAIL': settings.ADMINS[0][1],
                                                   'status': status})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(sendSubject, text_content, settings.EMAIL_HOST_USER, [job_email])
    msg.attach_alternative(html_content, "text/html")

    # Send email.
    logger.debug('Sending email...')
    try:
        msg.send()
        logger.debug('Email sent successfully! :)')
        return 1
    except Exception as e:
        logger.error('The following exception occured while trying to send mail: {}'.format(e))
        return 0


def getPnM(p):
    """Return protein and mutation from the format PROT.MUT."""
    protnMut = re.match(r'(.+)\.([A-Za-z]{1}[0-9]+[A-Za-z]{1}_?[0-9]*)$', p)
    if not protnMut:
        return None, None
    return protnMut.group(1).upper(), protnMut.group(2).upper()


def fetchProtein(pid, local=False):
    """Try to find protein in ELASPIC database.

    Order:

        1) Uniprot ID.
        2) HGNC identifiers.
        3) Uniprot identifiers.

    """
    logger.debug("fetchProtein({}, {})".format(pid, local))
    pid = pid.upper()
    try:
        # 1) Database protein
        return Protein.objects.get(id=re.sub(r'[^\x00-\x7f]', r'_', pid))
    except Protein.DoesNotExist as e:
        logger.debug(e)
        try:
            # Local protein
            return ProteinLocal.objects.get(id=re.sub(r'[^\x00-\x7f]', r'_', pid))
        except ProteinLocal.DoesNotExist as e:
            logger.debug(e)
            try:
                # 2)
                iden = HGNCIdentifier.objects.get(identifierID=pid)
                return Protein.objects.get(id=iden.uniprotID)
            except (HGNCIdentifier.DoesNotExist, Protein.DoesNotExist) as e:
                logger.debug(e)
                try:
                    # 3)
                    iden = list(UniprotIdentifier.objects.filter(identifierID=pid))
                    if iden:
                        # If more than one identifier is found, return the most
                        # important one determined by the following dict:
                        Ids = {'primaryIds': ['GeneWiki', 'UniProtKB-ID', 'EMBL',
                                              'Ensembl_PRO', 'EMBL-CDS', 'Ensembl',
                                              'GeneCards', 'GI'],
                               'modelIds': ['WormBase_PRO', 'WormBase', 'WormBase_TRS',
                                            'CYGD', 'SGD', 'PomBase', 'FlyBase', 'Xenbase',
                                            'MGI', 'TAIR', 'PATRIC', 'dictyBase',
                                            'EchoBASE', 'EcoGene', 'euHCVdb', 'GeneFarm',
                                            'H-InvDB', 'VectorBase', 'TubercuList',
                                            'LegioList', 'Leproma', 'mycoCLAP', 'PseudoCAP'],
                               'secondaryIds': ['GeneID', 'EnsemblGenome']}

                        iden = sorted(
                            iden, key=lambda i: ([i.identifierType not in Ids[key] for key in Ids])
                        )
                        return Protein.objects.get(id=iden[0].uniprotID)
                    else:
                        logger.debug("Error: '{}'".format(UniprotIdentifier.DoesNotExist))
                        raise UniprotIdentifier.DoesNotExist

                except (UniprotIdentifier.DoesNotExist, Protein.DoesNotExist) as e:
                    logger.debug(e)
                    return None

    return None
# The entire uniprot ID list would be:
# ['Allergome', 'ArachnoServer', 'BioCyc', 'BioGrid', 'CGD', 'ChEMBL', 'CleanEx',
# 'ConoServer', 'CYGD', 'dictyBase', 'DIP', 'DisProt', 'DMDM', 'DNASU',
# 'DrugBank', 'EchoBASE', 'EcoGene', 'eggNOG', 'EMBL', 'EMBL-CDS', 'Ensembl',
# 'Ensembl_PRO', 'Ensembl_TRS', 'EnsemblGenome', 'EnsemblGenome_PRO',
# 'EnsemblGenome_TRS', 'euHCVdb', 'EuPathDB', 'FlyBase', 'GeneCards',
# 'GeneFarm', 'GeneID', 'GeneTree', 'GeneWiki', 'GenoList', 'GenomeRNAi', 'GI',
# 'GuidetoPHARMACOLOGY', 'H-InvDB', 'HGNC', 'HOGENOM', 'HOVERGEN', 'HPA',
# 'KEGG', 'KO', 'LegioList', 'Leproma', 'MaizeGDB', 'MEROPS', 'MGI', 'MIM',
# 'MINT', 'mycoCLAP', 'NCBI_TaxID', 'NextBio', 'neXtProt', 'OMA', 'Orphanet',
# 'OrthoDB', 'PATRIC', 'PDB', 'PeroxiBase', 'PharmGKB', 'PhosSite', 'PomBase',
# 'PptaseDB', 'PseudoCAP', 'Reactome', 'REBASE', 'RefSeq', 'RefSeq_NT', 'RGD',
# 'SGD', 'STRING', 'TAIR', 'TCDB', 'TreeFam', 'TubercuList', 'UCSC', 'UniGene',
# 'UniParc', 'UniPathway', 'UniProtKB-ID', 'UniRef100', 'UniRef50', 'UniRef90',
# 'VectorBase', 'World-2DPAGE', 'WormBase', 'WormBase_PRO', 'WormBase_TRS',
# 'Xenbase', 'ZFIN']


def isInvalidMut(mut, seq):
    """Validate mutation of the format X001Y.

    Return <errorMessage> if invalid or None if valid.
    """
    # Test if input is valid syntax.
    goodSyntax = re.match(r'[A-Z]{1}[1-9]{1}[0-9]*[A-Z]{1}$', mut)
    if not goodSyntax:
        return 'SNX'

    # Test if mutation replaces with itself.
    if mut[0:1] == mut[-1:]:
        return 'SLF'

    # Test if mutation falls into the protein sequence.
    if int(mut[1:-1]) > len(seq):
        return 'OOB'

    # Test if mutation is the right amino acid.
    if mut[0] != seq[int(mut[1:-1]) - 1] or mut[-1].upper() not in 'GASTCVLIMPFYWDENQHKR':
        return 'OOB'

    # Return None if mutation is valid.
    return None
