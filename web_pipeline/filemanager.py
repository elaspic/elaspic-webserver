import six
from zipfile import ZipFile
from os import path
from tempfile import NamedTemporaryFile
import logging

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import generic_protein

from django.conf import settings

from web_pipeline.models import (
    Job, JobToMut, findInDatabase,
    Protein, ProteinLocal,
    CoreModel, CoreModelLocal,
    CoreMutation, CoreMutationLocal,
    InterfaceModel, InterfaceModelLocal,
    InterfaceMutation, InterfaceMutationLocal
)
from web_pipeline.functions import getPnM, getResultData

from elaspic.call_foldx import names_rows_stability as energyHeader


# Create logger to redirect output.
logger = logging.getLogger(__name__)


class FileManager(object):

    def __init__(self, jobID, muts):
        self.muts = []
        self.job = Job.objects.get(jobID=jobID)
        self.local = True if self.job.localID else False
        if self.job.localID:
            self.P = ProteinLocal
            self.CM = CoreModelLocal
            self.CMut = CoreMutationLocal
            self.IM = InterfaceModelLocal
            self.IMut = InterfaceMutationLocal
        else:
            self.P = Protein
            self.CM = CoreModel
            self.CMut = CoreMutation
            self.IM = InterfaceModel
            self.IMut = InterfaceMutation

        logger.info(jobID)
        logger.info(muts)

        # Save mutation list.
        for pnm in muts:
            iden, mut = getPnM(pnm)

            # Get interaction if it is an interface mutaition.
            isInterface = True if '_' in mut else False
            if isInterface:
                mut, interfaceID = mut.split('_')
                inac = self.IM.objects.get(id=interfaceID)
                model = inac.model

            # Get local mutation data.
            jtom = list(JobToMut.objects.filter(mut__mut=mut, inputIdentifier=iden, job_id=jobID))
            if len(jtom) != 1:
                continue

            # Get pipeline mutation data.
            if isInterface:
                data = jtom[0]
                realMut = list(self.IMut.objects.filter(mut=mut, model=model))
                logger.info('realMut: {}'.format(realMut))
                data.realMut = [realMut[0]]
                data.realMutErr = None
            else:
                data = getResultData(jtom[0])
            self.muts.append(data)

    def makeFile(self, fileToMake):

        # Return None if mutation list is empty
        self.fileCount = 0
        if not self.muts:
            self.fileSize = 0
            self.type = ""
            return ""

        # Create temporary buffer file.
        myfile = six.BytesIO()
        files = {'sequences': {},
                 'alignments': {},
                 'simpleresults': {},
                 'allresults': {},
                 'models': {}}
        filename, filetype = fileToMake.split('.')
        al = True if filename == 'allresults' else False
        dbpath = settings.DB_PATH

        # ##### Make files. #####
        # Result text files.
        mutTypes = {'CO': 'core', 'IN': 'interface', 'NO': 'not in domain'}

        if filename == 'allresults' or filename == 'simpleresults' or al:
            self.fileCount = 1
            body = []
            for m in self.muts:

                mutCompleted = True if (m.mut.status == 'done' and m.mut.affectedType != 'NO') \
                                    and (self.job.isDone or not(m.mut.rerun)) else False
                if mutCompleted:
                    logger.info(m.realMut)
                    rm = m.realMut[0]
                    mo = rm.model
                    c = rm.findChain()

                def r(x):
                    return ['-' for i in range(0, x)]

                def wtmut(x):
                    return [
                        (m + '_mut' if i % 2 else m + '_wt')
                        for i, m in enumerate([y for y in x for _ in [1, 2]])
                    ]

                inInterface = True if m.mut.affectedType == 'IN' else False
                ic = (2 if c == 1 else 1) if inInterface else 0

                # Protein name, mutation, status, and type.
                db_cosmic = '-'
                db_clinvar = '-'
                db_uniprot = '-'
                mut_dbs = findInDatabase([m.mut.mut], m.mut.protein)
                for db in mut_dbs[m.mut.mut]:
                    if 'ClinVar' == db['name']:
                        db_clinvar = db['variation']
                    elif 'COSMIC' == db['name']:
                        db_cosmic = db['variation']
                    elif 'UniProt' == db['name']:
                        db_uniprot = db['variation']
                header = [
                    'Input_identifier', 'UniProt_ID', 'Mutation', 'Status',
                    'Type', 'COSMIC_mut_ID', 'ClinVar_mut_ID', 'UniProt_mut_ID'
                ]
                bodyline = [m.inputIdentifier, m.mut.protein, m.mut.mut,
                            m.mut.status if self.job.isDone or not(m.mut.rerun) else 'running',
                            mutTypes[m.mut.affectedType] if m.mut.affectedType else '-',
                            db_cosmic, db_clinvar, db_uniprot]

                # Domain definitions IF allresults.
                if filename == 'allresults' or al:
                    header += ['Domain_name',
                               'Domain_clan',
                               'Domain_definitions',
                               'Template_cath_id',
                               'Template_sequence_identity',
                               'Alignment_score']
                    bodyline += [mo.getname(c),
                                 mo.getclan(c),
                                 mo.getdefs(c),
                                 mo.getcath(c),
                                 mo.getSeqId(c),
                                 mo.getAlnSc(c)] if mutCompleted else r(6)

                # Interactor protein name.
                header += ['Interactor_UniProt_ID']
                bodyline += [mo.getprot(ic).id] if inInterface and mutCompleted else r(1)

                # Interactor domain definitions IF allresults.
                if filename == 'allresults' or al:
                    header += ['Interactor_domain_name',
                               'Interactor_domain_clan',
                               'Interactor_domain_definitions',
                               'Interactor_template_cath_id',
                               'Interactor_template_sequence_identity',
                               'Interactor_alignment_score']
                    bodyline += [mo.getname(ic),
                                 mo.getclan(ic),
                                 mo.getdefs(ic),
                                 mo.getcath(ic),
                                 mo.getSeqId(ic),
                                 mo.getAlnSc(ic)] if inInterface and mutCompleted else r(6)

                # Final ddG.
                header += ['Final_ddG']
                bodyline += [str(rm.ddG)] if mutCompleted else r(1)

                if filename == 'allresults' or al:
                    # Remaining shared features IF allresults.
                    sDict = {'H': 'alpha helix',
                             'B': 'residue in isolated beta-bridge',
                             'E': 'extended strand, participates in beta ladder',
                             'G': '3-helix (3/10 helix)',
                             'I': '5 helix (pi helix)',
                             'T': 'hydrogen bonded turn',
                             'S': 'bend',
                             '-': '-'}
                    physchem = ['pcv_salt_equal', 'pcv_salt_opposite', 'pcv_hbond', 'pcv_vdW']

                    header += (['Model/DOPE_score',
                                'Sift_score',
                                'Matrix_score'] +
                               wtmut(['Secondary_structure',
                                     'Solvent_accessibility']) +
                               [n + '_wt' for n in physchem] +
                               [n + '_mut' for n in physchem] +
                               [n + '_self_wt' for n in physchem] +
                               [n + '_self_mut' for n in physchem])

                    bodyline += ([mo.dope_score,
                                  rm.provean_score,
                                  rm.matrix_score,
                                  (sDict[rm.secondary_structure_wt]
                                      if rm.secondary_structure_wt in sDict else '-'),
                                  (sDict[rm.secondary_structure_mut]
                                      if rm.secondary_structure_mut in sDict else '-'),
                                  rm.solvent_accessibility_wt,
                                  rm.solvent_accessibility_mut] +
                                 rm.physchem_wt.split(',') +
                                 rm.physchem_mut.split(',') +
                                 rm.physchem_wt_ownchain.split(',') +
                                 rm.physchem_mut_ownchain.split(',') if mutCompleted else r(23))

                    header += ([n[0] + '_wt' for n in energyHeader] +
                               [n[0] + '_mut' for n in energyHeader] +
                               wtmut(['IntraclashesEnergy1',
                                     'IntraclashesEnergy2']) +
                               ['Interface_hydrophobic_area',
                                'Interface_hydrophilic_area',
                                'Interface_total_area'] +
                               wtmut(['Interface_contact_distance']))

                    if mutCompleted:
                        # Remaining core features.
                        if not inInterface:
                            bodyline += rm.stability_energy_wt.split(',') + \
                                        rm.stability_energy_mut.split(',') + \
                                        r(9)
                        # Remaining interface features.
                        else:
                            energyComplexWt = rm.stability_energy_wt.split(',')
                            energyComplexMut = rm.stability_energy_mut.split(',')
                            bodyline += (energyComplexWt[2:] +
                                         energyComplexMut[2:] +
                                         [energyComplexWt[0],
                                          energyComplexMut[0],
                                          energyComplexWt[1],
                                          energyComplexMut[1],
                                          mo.interface_area_hydrophobic,
                                          mo.interface_area_hydrophilic,
                                          mo.interface_area_total,
                                          rm.contact_distance_wt,
                                          rm.contact_distance_mut])
                    else:
                        bodyline += r(55)

                bodyline = [str(l) for l in bodyline]
                body.append('\t'.join(bodyline))

        if filetype == 'txt':
            self.type = 'text/plain'
            myfile.write(six.b('\t'.join(header) + '\r\n'))
            myfile.write(six.b('\r\n'.join(body)))

        elif filetype == 'zip':

            self.type = 'application/zip'

            # Result text files.
            if al:
                temp2 = NamedTemporaryFile()
                temp2.write('\t'.join(header) + '\r\n')
                temp2.write('\r\n'.join(body))
                temp2.flush()
                files['allresults'] = temp2.name

            # Sequences.
            if filename == 'sequences' or al:
                tempfiles = []
                for m in self.muts:
                    try:
                        p = self.P.objects.get(id=m.mut.protein)
                    except (self.P.DoesNotExist, self.P.MultipleObjectsReturned):
                        continue
                    fname = m.inputIdentifier + '.fasta'
                    if not (fname in files['sequences']):
                        seq = SeqRecord(Seq(p.seq, generic_protein),
                                        id="%s|%s|%s" % (m.inputIdentifier, p.id, p.name),
                                        description=p.description)
                        tempfiles.append(NamedTemporaryFile())
                        SeqIO.write([seq], tempfiles[-1].name, 'fasta')
                        tempfiles[-1].flush()
                        files['sequences'][fname] = tempfiles[-1].name
                        self.fileCount += 1

            # Structures.
            if (filename == 'wtmodels-ori' or
                    filename == 'wtmodels-opt' or filename == 'mutmodels' or al):
                for m in self.muts:
                    if m.realMutErr:
                        continue
                    rm = m.realMut[0]
                    # chain = rm.findChain()
                    try:
                        chain = rm.findChain()
                        mpath = rm.model.data_path
                        defs = rm.model.getdefs(chain).replace(":", "-")
                    except Exception:
                        continue
                    if m.mut.affectedType == 'IN':
                        inacChain = 2 if chain == 1 else 1
                        inacprot = rm.model.getprot(inacChain).id
                        inacdefs = rm.model.getdefs(inacChain).replace(":", "-")
                        extratext = ' with %s_%s' % (inacprot, inacdefs)
                    else:
                        extratext = ''
                    if filename == 'wtmodels-ori' or al:
                        ppath = rm.model.model_filename
                        if ppath:
                            fname = '%s_%s%s original.pdb' % (m.inputIdentifier, defs, extratext)
                            if not (fname in files['models']):
                                files['models'][fname] = path.join(dbpath, mpath, ppath)
                                self.fileCount += 1
                    if filename == 'wtmodels-opt' or al:
                        ppath = rm.model_filename_wt
                        if ppath:
                            fname = '%s_%s%s optimized.pdb' % (m.inputIdentifier, defs, extratext)
                            if not (fname in files['models']):
                                files['models'][fname] = path.join(dbpath, mpath, ppath)
                                self.fileCount += 1
                    if filename == 'mutmodels' or al:
                        ppath = rm.model_filename_mut
                        if ppath:
                            fname = (
                                '%s_%s%s %s.pdb'
                                % (m.inputIdentifier, defs, extratext, m.mut.mut)
                            )
                            if not (fname in files['models']):
                                files['models'][fname] = path.join(dbpath, mpath, ppath)
                                self.fileCount += 1

            # Alignments
            if filename == 'alignments' or al:
                for m in self.muts:
                    if m.realMutErr:
                        continue
                    rm = m.realMut[0]
                    chain = rm.findChain()
                    try:
                        mpath = rm.model.data_path
                    except Exception:
                        continue
                    apath = rm.model.getAlnFi(chain)
                    if apath:
                        defs = rm.model.getdefs(chain).replace(":", "-")
                        if m.mut.affectedType == 'IN':
                            # Interface.
                            inacChain = 2 if chain == 1 else 1
                            inacprot = rm.model.getprot(inacChain).id
                            inacdefs = rm.model.getdefs(inacChain).replace(":", "-")
                            fname = '%s_%s (with %s_%s).aln' % (m.inputIdentifier,
                                                                defs,
                                                                inacprot,
                                                                inacdefs)
                            apath2 = rm.model.getAlnFi(inacChain)
                            fname2 = '%s_%s (with %s_%s).aln' % (inacprot,
                                                                 inacdefs,
                                                                 m.inputIdentifier,
                                                                 defs)
                            if not (fname in files['alignments']):
                                files['alignments'][fname] = path.join(dbpath, mpath, apath)
                                self.fileCount += 1
                            if not (fname2 in files['alignments']):
                                files['alignments'][fname2] = path.join(dbpath, mpath, apath2)
                                self.fileCount += 1
                        else:
                            # Core.
                            fname = '%s_%s.aln' % (m.inputIdentifier, defs)
                            if not (fname in files['alignments']):
                                files['alignments'][fname] = path.join(dbpath, mpath, apath)
                                self.fileCount += 1

            # ##### Save files as zip. #####
            z = ZipFile(myfile, "w")
            for fold in files:
                # Set subfolder if everything is requested.
                if fold == 'simpleresults':
                    continue
                if fold == 'allresults' and al:
                    z.write(files[fold], 'allresults.txt')
                    continue
                # Write file to zip.
                for f in files[fold]:
                    z.write(files[fold][f], (fold + '/' if al else '') + f)
            z.close()

        # Return buffer file.
        self.fileSize = len(myfile.getvalue())
        return myfile.getvalue()
