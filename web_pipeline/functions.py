from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import now
from django.db.models import Q

from web_pipeline.models import (
    HGNCIdentifier, UniprotIdentifier,
    Protein, ProteinLocal,
    CoreMutation, CoreMutationLocal,
    InterfaceMutation, InterfaceMutationLocal,
)
import logging
from re import match

logger = logging.getLogger(__name__)


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

    # Update job last visited to now.
    j = jtom.job
    j.dateVisited = now()
    j.save()

    local = True if j.localID else False
    CM = CoreMutationLocal if local else CoreMutation
    IM = InterfaceMutationLocal if local else InterfaceMutation
    aType = jtom.mut.affectedType
    jtom.realMutErr = None
    if aType == 'CO':
        jtom.realMut = list(
            CM.objects.filter(protein_id=jtom.mut.protein, mut=jtom.mut.mut)
        )
    elif aType == 'IN':
        # TODO: Would be nice to give both a core and an interface result, but too many chages.
        # if local:
        #     jtom.realMut = (
        #         list(CM.objects.filter(protein_id=jtom.mut.protein, mut=jtom.mut.mut)) +
        #         list(IM.objects.filter(protein_id=jtom.mut.protein, mut=jtom.mut.mut))
        #     )
        # else:
        jtom.realMut = (
            # list(CM.objects.filter(protein_id=jtom.mut.protein, mut=jtom.mut.mut)) +
            list(IM.objects.filter(protein_id=jtom.mut.protein, mut=jtom.mut.mut))
        )
    else:
        jtom.realMutErr = 'NOT'  # Not in core or in interface.
        jtom.realMut = [{}]
        return jtom
    if not jtom.realMut:
        jtom.realMutErr = 'DNE'  # Does not exists.
        jtom.realMut = [{}]
        return jtom
    if aType == 'CO':
        if len(jtom.realMut) > 1:
            # With overlapping domains, pick first highest sequence identity,
            # then lowest model score.
            # jtom.realMutErr = 'MOR'
            muts = sorted(jtom.realMut, key=lambda m: m.model.seq_id, reverse=True)
            highestSeqID = []
            for m in muts:
                if m.model.seq_id < muts[0].model.seq_id:
                    break
                else:
                    highestSeqID.append(m)
            jtom.realMut = [min(highestSeqID, key=lambda m: m.model.dope_score)]
        return jtom
    elif aType == 'IN':
        jtom.realMut = [m for m in jtom.realMut if not m.mut_errors]
        return jtom

    jtom.realMutErr = 'OTH'  # Other.
    return jtom


def sendEmail(j, sendType):
    if isinstance(j, (list, tuple)):
        job_id, job_email = j
    else:
        job_id, job_email = j.jobID, j.email

    # Validate email address
    if not match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:[a-zA-Z]{2,4}|museum)$', job_email):
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
    try:
        msg.send()
        return 1
    except Exception as e:
        logger.error('The following exception occured while trying to send mail: {}'.format(e))
        return 0


def getPnM(p):
    ''' Returns protein and mutation from the format PROT.MUT '''

    protnMut = match(r'(.+)\.([A-Za-z]{1}[0-9]+[A-Za-z]{1}_?[0-9]*)$', p)
    if not protnMut:
        return None, None
    return protnMut.group(1).upper(), protnMut.group(2).upper()


def fetchProtein(pid, local=False):
    ''' Tries to find protein in ELASPIC database, in the order:

        1) Uniprot ID.
        2) HGNC identifiers.
        3) Uniprot identifiers.

    '''
    logger.debug("fetchProtein({}, {})".format(pid, local))
    pid = pid.upper()
    try:
        # 1) Database protein
        return Protein.objects.get(id=pid)
    except Protein.DoesNotExist as e:
        logger.debug(e)
        try:
            # Local protein
            return ProteinLocal.objects.get(id=pid)
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

                except (UniprotIdentifier.DoesNotExist, Protein.DoesNotExist):
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
    ''' Validates mutation of the format X001Y
        Returns <errorMessage> if invalid or None if valid '''

    # Test if input is valid syntax.
    goodSyntax = match(r'[A-Z]{1}[1-9]{1}[0-9]*[A-Z]{1}$', mut)
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
