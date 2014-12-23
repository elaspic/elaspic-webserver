from django.http import HttpResponse, Http404
from django.shortcuts import render

from django.utils import simplejson

from web_pipeline import models

from Bio import SeqIO
import re
from itertools import islice

"""
        Views to import data from file to website.

"""


def importBase(request):


    path = {'proteins': 'uniprot.fasta',
            'identifiers': 'identifiers.txt',
            'hgncidentifiers': 'hgnc_downloads.txt',
            'domains': 'sebastian_10-sep-13.txt',
            'interactions': '',
            'proteinpdbs': ''}
	
    # Get database version.z
    models.VersionControl.objects.get_or_create(dbVersion = '0.0.0')
    db = models.VersionControl.objects.latest()

    context = {'path': path,
               'dbversion': db.dbVersion,
               'version_date': db.dateUpdated}
	
    return render(request, 'import.html', context)

def importer(request):
    # Check if the site was reached with GET method and assign variables.
    if not request.GET:
        raise Http404
    if not 'f' in request.GET or not 'n' in request.GET or not 'm' in request.GET or not request.GET['f']:
        raise Http404
    jsonDict = {'error': 0}
    path = 'databases/' + request.GET['f']
    imType = request.GET['t']

    # If first run..
    maxLines = int(request.GET['m'])
    if not maxLines:        
        # Count lines in file.
        i = 0
        try:
            if imType == "proteins":
                for seqs in SeqIO.parse(path, "fasta"):
                    i += 1
            else:
                with open(path) as f:
                    for i, l in enumerate(f):
                        pass
            maxLines = i
        except IOError:
            jsonDict['error'] = 1
        if imType == 'domains':
            totalDoms = set()
            with open(path, 'r') as f:
                for line in f:
                    totalDoms.add(line.split('\t')[1])
            mList = [models.Domain(name=dom) for dom in totalDoms]
            models.Domain.objects.bulk_create(mList)

    if not jsonDict['error']:

        jsonDict['lines'] = maxLines
        
        # Get line start and end in the requested interval.
        n = int(request.GET['n'])
        if n == 1:
            line_start = 0
        else:
            line_start = int(maxLines * ((n * 10 - 10.00) / 100))
        if n == 10:
            line_end = maxLines
        else:
            line_end = int(maxLines * ((n * 10 + 0.00) / 100))
        uList = []

        # If proteins, save proteins.
        if imType == 'proteins':
            allSeqs = SeqIO.parse(path, "fasta")
            currentSeqs = islice(allSeqs, line_start, line_end)
            for seqs in currentSeqs:
                reg = re.search(r'^([a-z]{2})[|](.+?)[|](.+?)\s(.+?)\sOS=Homo\ssapiens(.*)', \
                                seqs.description)
                
                # Ignore all isoforms as for now.
                #if '-' in reg.group(2):
                #    continue

                if 'SV=' in reg.group(5):
                    reg2 = re.search(r'SV=([0-9]+)', reg.group(5))
                    seqVer = int(reg2.group(1))        
                else:
                    seqVer = 0
                    
                uList.append(models.Protein(uniqueID=reg.group(2), 
                                            description=reg.group(4),
                                            sequence=seqs.seq, 
                                            sequenceVersion=seqVer))

            models.Protein.objects.bulk_create(uList, batch_size=500)
            
        else:
            # Otherwise, first look up dependencies.
            allProteins = models.Protein.objects.all()
            pdict = {}
            for protein in allProteins:
                pdict[protein.uniqueID] = protein
            if imType == 'identifiers':
                ok = ['GeneID', 'UniProtKB-ID', 'UniParc', 'UniRef', 'Ensembl', 
                      'Ensembl_PRO', 'Ensembl_TRS', 'RefSeq', 'RefSeq_NT', 
                      'UCSC', 'EMBL', 'EMBL-CDS', 'neXtProt', 'OMA', 'STRING', 
                      'ChEMBL', 'MINT', 'DIP', 'DMDM', 'H-InvDB', 'PharmGKB']
            elif imType == 'domains':
                allDomains = models.Domain.objects.all()
                ddict = {}
                for domain in allDomains:
                    ddict[domain.name] = domain
            elif imType == 'oldidentifiers':
                iList = []
                with open(path) as f:
                    for lines in f: 
                        iList.append(lines.split('\t')[0])
                        for syn in lines.split('\t')[2].split(', '):
                            iList.append(syn)
                
            # Then open file.
            with open(path) as f:
                currentLines = islice(f, line_start, line_end)
                for lines in currentLines: 
                    line = lines.split('\t')
                    # If identifiers, create instances.
                    # All 3 728 903
                    # In our: 1 337 781
                    # w/o ignore n '-': 721 403
                    if imType == 'identifiers':
                        if line[0] not in pdict:
                            continue
                        if line[1] not in ok:
                            continue
                        if line[2].strip() == '-':
                            continue
                        
                        uList.append(models.Identifier(identifierID = line[2].strip(), 
                                                       identifierType = line[1], 
                                                       uniprotID = pdict[line[0]]))
                    elif imType == 'hgncidentifiers':
                        if line[3] == '\n':
                            continue
                        if line[3].strip() not in pdict:
                            continue
                        uList.append(models.Identifier(identifierID = line[0], 
                                                       identifierType = "geneName", 
                                                       uniprotID = pdict[line[3].strip()]))
                        for syn in line[2].split(', '):
                            uList.append(models.Identifier(identifierID = syn,
                                                           identifierType = "geneNameSyn",
                                                           uniprotID = pdict[line[3].strip()]))
                    elif imType == 'oldidentifiers':
                        if line[3] == '\n':
                            continue
                        if line[3].strip() not in pdict:
                            continue
                        if line[1] in iList:
                            continue
                        for old in line[1].split(', '):
                            uList.append(models.Identifier(identifierID = old,
                                                           identifierType = "geneNameOld",
                                                           uniprotID = pdict[line[3].strip()]))
                        

                    # If domains, create protein-domains.
                    elif imType == 'domains':
                        if line[0] not in pdict:
                            continue
                        uList.append(models.ProteinDomain(protein = pdict[line[0]],
                                                          domain = ddict[line[1]],
                                                          defStart = line[2].split('-')[0],
                                                          defEnd = line[2].split('-')[1]))
                
                        
            # Save instances.
            if imType == 'identifiers' or imType == 'hgncidentifiers' or imType == 'oldidentifiers':
                models.Identifier.objects.bulk_create(uList, batch_size=10000)
            elif imType == 'domains':
                models.ProteinDomain.objects.bulk_create(uList, batch_size=10000)
                
        
        # Output variables.
        jsonDict['count'] = len(uList)
            
    
    # Return.
    return HttpResponse(simplejson.dumps(jsonDict), mimetype='application/json')


def dbupdater(request):
    # Check if the site was reached with GET method.
    if not request.GET:
        raise Http404
    if not 'v' in request.GET or not request.GET['v']:
        raise Http404
    jsonDict = {'error': 0}
    
    try:
        ver = request.GET['v']
        pC = models.Protein.objects.count()
        #sC = models.Protein.objects.exclude(pdb__isnull=True).count()
        dC = models.ProteinDomain.objects.count()
        duC = models.Domain.objects.count()
        iC = models.Interaction.objects.count()
        mC = models.Mutation.objects.count()
        #eC = models.ProteinElm.object.count()
        #euC = models.Elm.object.count()
        idC = models.Identifier.objects.count()
        v = models.VersionControl(dbVersion=ver, proteinCount=pC, 
                                  domainCount=dC, domainUniqueCount=duC,
                                  interactionCount=iC, mutationCount=mC, 
                                  identifierCount=idC)
        v.save()
        jsonDict = {'error': 0, 'pC': pC, 'dC': dC, 'duC': duC, 'eC': 0, 
                    'euC': 0, 'iC': iC, 'mC': mC, 'idC': idC}
    except: 
        jsonDict = {'error': 1}
        
    # Return.
    return HttpResponse(simplejson.dumps(jsonDict), mimetype='application/json')
    
def dbreset(request):
    # Check if the site was reached with GET method.
    if not request.GET:
        raise Http404
    jsonDict = {'error': 0}
    
    # Remove all links from Mutation to Protein.
    for mut in models.Mutation.objects.all():
        mut.protein = None
        mut.save()
    
    # Remove all old entries.
    try:
        models.ProteinDomain.objects.all().delete()
        models.Domain.objects.all().delete()
        models.InteractionInfo.objects.all().delete()
        models.MutatedInteraction.objects.all().delete() # This has to be fixed later.
        models.Interaction.objects.all().delete()
        models.Identifier.objects.all().delete()
        models.Protein.objects.all().delete()
    except:
        jsonDict['error'] = 1

    # Return.
    return HttpResponse(simplejson.dumps(jsonDict), mimetype='application/json')