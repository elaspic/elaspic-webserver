import io
import logging
import os.path as op
import shutil
import tempfile
from zipfile import ZipFile

from Bio import SeqIO
from Bio.Alphabet import generic_protein
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from django.conf import settings

from elaspic.call_foldx import names_rows_stability as energyHeader
from web_pipeline import functions, models

logger = logging.getLogger(__name__)


class FileManager:
    """

    Attributes
    ----------
    filename : str
        Name of file which is procuded (no path or extension).
    filetype : str
        Extension of file which is produced.
    """
    _valid_filenames = [
        'simpleresults.txt', 'allresults.txt',
        'wtmodels-ori.zip', 'wtmodels-opt.zip', 'mutmodels.zip',
        'alignments.zip', 'sequences.zip',
        'allresults.zip',
    ]

    def __init__(self, jobID, muts):
        logger.debug("jobID: {}".format(jobID))
        logger.debug("muts: {}".format(muts))
        self.muts = []
        self.files = None
        self.file_name = None

        self.job = models.Job.objects.get(jobID=jobID)
        self.local = True if self.job.localID else False
        if self.job.localID:
            self.P = models.ProteinLocal
            self.CM = models.CoreModelLocal
            self.CMut = models.CoreMutationLocal
            self.IM = models.InterfaceModelLocal
            self.IMut = models.InterfaceMutationLocal
        else:
            self.P = models.Protein
            self.CM = models.CoreModel
            self.CMut = models.CoreMutation
            self.IM = models.InterfaceModel
            self.IMut = models.InterfaceMutation

        # Save mutation list.
        for pnm in muts:
            iden, mut = functions.getPnM(pnm)
            if iden is None or mut is None:
                logger.error("Something wrong happened when parsing pnm: '{}'".format(pnm))
                logger.error("iden: '{}'".format(iden))
                logger.error("mut: '{}'".format(mut))
                continue

            # Get interaction if it is an interface mutaition.
            isInterface = '_' in mut
            if isInterface:
                mut, interfaceID = mut.split('_')
                try:
                    model = self.IM.objects.get(id=interfaceID)
                except (self.IM.DoesNotExist, ValueError):
                    logger.error("Interface model with id '{}' was not found!".format(interfaceID))
                    continue

            # Get local mutation data.
            jtom = list(
                models.JobToMut.objects.filter(
                    mut__mut=mut, inputIdentifier=iden, job_id=jobID))
            if len(jtom) != 1:
                continue

            # Get pipeline mutation data.
            if isInterface:
                data = jtom[0]
                realMut = list(self.IMut.objects.filter(mut=mut, model=model))
                data.realMut = [realMut[0]]
                data.realMutErr = None
            else:
                data = functions.getResultData(jtom[0])
                data.realMut = [data.realMut[0]]
            self.muts.append(data)

    @property
    def file_count(self):
        if self.files is None:
            return 0
        return len([k for gp in self.files for k in self.files[gp]])

    def makeFile(self, fileToMake):
        self.file_name, self.file_ext = op.splitext(fileToMake)
        self.tempdir = tempfile.mkdtemp()
        self.files = functions.FixedDict({op.splitext(k)[0]: {} for k in self._valid_filenames})

        # Validate input
        if fileToMake not in self._valid_filenames:
            raise ValueError(
                "filename {} must be one of {}".format(fileToMake, self._valid_filenames))

        # Return empty buffer if mutation list is empty
        if not self.muts:
            return b''

        # Data (allresults)
        if self.file_name in ['simpleresults', 'allresults']:
            self.add_data_files()

        # Sequences.
        if self.file_name in ['sequences'] or fileToMake in ['allresults.zip']:
            self.add_sequence_files()

        # Structures.
        if self.file_name in ['wtmodels-ori', 'wtmodels-opt', 'mutmodels'] or \
                fileToMake in ['allresults.zip']:
            self.add_structure_files()

        # Alignments
        if self.file_name in ['alignments'] or fileToMake in ['allresults.zip']:
            self.add_alignment_files()

        # Text or zip
        if self.file_ext == '.txt':
            buffer = self._get_txt_buffer()
        elif self.file_ext == '.zip':
            buffer = self._get_zip_buffer()
        else:
            raise Exception("Unsupported extension: {}".format(self.file_ext))

        shutil.rmtree(self.tempdir, ignore_errors=True)

        return buffer.getvalue()

    def add_data_files(self):
        header, body = self.make_csv()
        tf = tempfile.NamedTemporaryFile(mode='wb+', dir=self.tempdir, delete=False)
        tf.write(('\t'.join(header) + '\r\n').encode('utf-8'))
        tf.write(('\r\n'.join(body)).encode('utf-8'))
        tf.flush()
        tf.close()
        assert self.file_name in ['allresults', 'simpleresults']
        filename = self.file_name + '.txt'  # 'allresults.txt' or 'simpleresults.txt'
        self.files[self.file_name][filename] = tf.name

    def make_csv(self):
        """
        TODO: Refactor this to use pandas?
        """
        body = []
        for m in self.muts:
            header, bodyline = self._make_row(m)
            bodyline = [str(l) for l in bodyline]
            body.append('\t'.join(bodyline))
        return header, body

    def _make_row(self, m):
        """Create a row for the CSV file.
        """
        mutCompleted = (
            m.mut.status == 'done' and m.mut.affectedType != 'NO' and
            (self.job.isDone or not m.mut.rerun)
        )
        c = 1
        if mutCompleted:
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

        assert m.realMut[0].mutation_type in ['core', 'interface']
        inInterface = m.realMut[0].mutation_type == 'interface'

        ic = (2 if c == 1 else 1) if inInterface else 0

        # Protein name, mutation, status, and type.
        db_cosmic = '-'
        db_clinvar = '-'
        db_uniprot = '-'
        mut_dbs = models.findInDatabase([m.mut.mut], m.mut.protein)
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
                    m.realMut[0].mutation_type,
                    db_cosmic, db_clinvar, db_uniprot]

        # Domain definitions IF allresults.
        if self.file_name == 'allresults':
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
        if self.file_name == 'allresults':
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

        if self.file_name == 'allresults':
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
                        'Provean_score',
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
                    bodyline += (
                        rm.stability_energy_wt.split(',') +
                        rm.stability_energy_mut.split(',') +
                        r(9)
                    )
                # Remaining interface features.
                else:
                    energyComplexWt = rm.analyse_complex_energy_wt.split(',')
                    energyComplexMut = rm.analyse_complex_energy_mut.split(',')
                    bodyline += (
                        energyComplexWt[2:] +
                        energyComplexMut[2:] + [
                            energyComplexWt[0],
                            energyComplexMut[0],
                            energyComplexWt[1],
                            energyComplexMut[1],
                            mo.interface_area_hydrophobic,
                            mo.interface_area_hydrophilic,
                            mo.interface_area_total,
                            rm.contact_distance_wt,
                            rm.contact_distance_mut
                        ]
                    )
            else:
                bodyline += r(55)
        return header, bodyline

    def add_sequence_files(self):
        for m in self.muts:
            try:
                p = self.P.objects.get(id=m.mut.protein)
            except (self.P.DoesNotExist, self.P.MultipleObjectsReturned) as e:
                logger.error(
                    "Failed to get protein with error: '{}: {}'"
                    .format(type(e), e))
                continue
            fname = m.inputIdentifier + '.fasta'
            if not (fname in self.files['sequences']):
                seq = SeqRecord(Seq(p.seq, generic_protein),
                                id="%s|%s|%s" % (m.inputIdentifier, p.id, p.name),
                                description=p.description)
                seqfile = tempfile.NamedTemporaryFile(dir=self.tempdir, delete=False)
                SeqIO.write([seq], seqfile.name, 'fasta')
                seqfile.flush()
                self.files['sequences'][fname] = seqfile.name
                seqfile.close()

    def add_structure_files(self):
        for m in self.muts:
            if m.realMutErr:
                continue
            rm = m.realMut[0]
            chain = rm.findChain()
            mpath = rm.model.data_path
            defs = rm.model.getdefs(chain).replace(":", "-")
            if isinstance(rm.model, models._CoreModel):
                extratext = ''
            else:
                inacChain = 2 if chain == 1 else 1
                inacprot = rm.model.getprot(inacChain).id
                inacdefs = rm.model.getdefs(inacChain).replace(":", "-")
                extratext = ' with %s_%s' % (inacprot, inacdefs)
            if self.file_name in ['wtmodels-ori', 'allresults']:
                if rm.model.model_filename:
                    fname = '%s_%s%s original.pdb' % (m.inputIdentifier, defs, extratext)
                    self.files['wtmodels-ori'][fname] = op.join(
                        settings.DB_PATH, mpath, rm.model.model_filename)
            if self.file_name in ['wtmodels-opt', 'allresults']:
                if rm.model_filename_wt:
                    fname = '%s_%s%s optimized.pdb' % (m.inputIdentifier, defs, extratext)
                    self.files['wtmodels-opt'][fname] = op.join(
                        settings.DB_PATH, mpath, rm.model_filename_wt)
            if self.file_name in ['mutmodels', 'allresults']:
                if rm.model_filename_mut:
                    fname = '%s_%s%s %s.pdb' % (m.inputIdentifier, defs, extratext, m.mut.mut)
                    self.files['mutmodels'][fname] = op.join(
                        settings.DB_PATH, mpath, rm.model_filename_mut)

    def add_alignment_files(self):
        for m in self.muts:
            if m.realMutErr:
                continue
            rm = m.realMut[0]
            chain = rm.findChain()
            defs = rm.model.getdefs(chain).replace(":", "-")
            if isinstance(rm.model, models._CoreModel):
                fname = '%s_%s.aln' % (m.inputIdentifier, defs)
                if not (fname in self.files['alignments']):
                    self.files['alignments'][fname] = op.join(
                        settings.DB_PATH, rm.model.data_path, rm.model.alignment_filename)
                logger.debug("fname: {}".format(fname))
            else:
                # Interface.
                chain_other = 2 if chain == 1 else 1
                inacprot = rm.model.getprot(chain_other).id
                inacdefs = rm.model.getdefs(chain_other).replace(":", "-")
                fname = (
                    '{}_{} (with {}_{}).aln'.format(
                        m.inputIdentifier,
                        defs,
                        inacprot,
                        inacdefs,
                    ))
                fname2 = (
                    '{}_{} (with {}_{}).aln'.format(
                        inacprot,
                        inacdefs,
                        m.inputIdentifier,
                        defs,
                    ))
                logger.debug("fname: {}".format(fname))
                logger.debug("fname2: {}".format(fname2))

                if chain == 1:
                    alignment_filename_1, alignment_filename_2 = (
                        rm.model.alignment_filename_1, rm.model.alignment_filename_2
                    )
                else:
                    alignment_filename_2, alignment_filename_1 = (
                        rm.model.alignment_filename_1, rm.model.alignment_filename_2
                    )
                logger.debug("alignment_filename_1: {}".format(alignment_filename_1))
                logger.debug("alignment_filename_2: {}".format(alignment_filename_2))

                if not (fname in self.files['alignments']):
                    self.files['alignments'][fname] = op.join(
                        settings.DB_PATH, rm.model.data_path, alignment_filename_1)
                if not (fname2 in self.files['alignments']):
                    self.files['alignments'][fname2] = op.join(
                        settings.DB_PATH, rm.model.data_path, alignment_filename_2)

    def _get_txt_buffer(self):
        ofh = io.BytesIO()  # output file handle
        for filename, file in self.files[self.file_name].items():
            logger.debug('self.file_name: {}'.format(self.file_name))
            logger.debug('filename: {}'.format(filename))
            logger.debug('file: {}'.format(file))
            with open(file, 'rb') as ifh:
                ofh.write(ifh.read())
        return ofh

    def _get_zip_buffer(self):
        """Save self.files as zip.
        """
        ofh = io.BytesIO()  # output file handle
        z = ZipFile(ofh, "w")
        for fold in self.files:
            logger.debug("fold: {}".format(fold))
            # Set subfolder if everything is requested.
            if fold == 'simpleresults':
                continue
            # Write file to zip.
            for filename, file in self.files[fold].items():
                if ((fold in ['allresults', 'simpleresults']) or
                        (self.file_name not in ['allresults', 'simpleresults'])):
                    z.write(file, filename)
                elif fold in ['wtmodels-ori', 'wtmodels-opt', 'mutmodels']:
                    z.write(file, 'models' + '/' + filename)
                else:
                    z.write(file, fold + '/' + filename)
        z.close()
        return ofh
