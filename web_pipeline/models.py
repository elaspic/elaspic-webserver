import functools
import logging
from collections import defaultdict

from django.db import models
from django.utils.timezone import localtime

logger = logging.getLogger(__name__)


class Mut(models.Model):
    TYPE_CHOICES = (
        ("NO", "None"),
        ("CO", "Core"),
        ("IN", "Interaction"),
    )

    protein = models.CharField(max_length=50, db_index=True)
    mut = models.CharField(max_length=8)
    chain = models.SmallIntegerField(
        null=True, blank=True
    )  # chain_idx; 0 -> first chain in PDB

    affectedType = models.CharField(max_length=2, choices=TYPE_CHOICES, blank=True)
    dateAdded = models.DateTimeField(auto_now_add=True)
    dateFinished = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, default="queued")

    rerun = models.SmallIntegerField(default=0)
    taskId = models.CharField(max_length=50, blank=True)

    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return "%s.%s" % (self.protein, self.mut)

    class Meta:
        # app_label = 'Mut'
        db_table = "muts"
        index_together = [
            ("protein", "mut"),
        ]
        # ordering = ['protein', 'mut']


class Job(models.Model):
    jobID = models.CharField(max_length=10, primary_key=True)
    dateRun = models.DateTimeField(auto_now_add=True)
    dateFinished = models.DateTimeField(null=True, blank=True)
    dateVisited = models.DateTimeField(auto_now_add=True)
    isDone = models.BooleanField(default=False)
    email = models.EmailField(blank=True)

    localID = models.CharField(max_length=50, null=True, blank=True)

    muts = models.ManyToManyField(Mut, through="JobToMut", related_name="jobs")

    browser = models.TextField(blank=True)

    def getDateRun(self):
        return localtime(self.dateRun)

    def getDateFinished(self):
        return localtime(self.dateFinished) if self.dateFinished else "-"

    def __str__(self):
        return self.jobID

    class Meta:
        db_table = "jobs"
        get_latest_by = "dateRun"
        ordering = ["jobID"]


class JobToMut(models.Model):
    mut = models.ForeignKey(Mut, on_delete=models.CASCADE)  # intermediary model
    job = models.ForeignKey(Job, on_delete=models.CASCADE)  # intermediary model
    inputIdentifier = models.CharField(max_length=70)

    realMut = None
    realMutErr = None

    def __str__(self):
        return "#%s to mut%d" % (self.job_id, self.mut_id)

    class Meta:
        db_table = "job_to_mut"


# %% Database: 'uniprot_kb'

# from django.db.models import fields
# from south.modelsinspector import add_introspection_rules
#
# class BigAutoField(fields.AutoField):
#     def db_type(self, connection):
#         if 'mysql' in connection.__class__.__module__:
#             return 'bigint AUTO_INCREMENT'
#         return super(BigAutoField, self).db_type(connection)
#
# add_introspection_rules([], ["^MYAPP\.fields\.BigAutoField"])


class UniprotIdentifier(models.Model):
    id = models.AutoField(primary_key=True, db_index=True)

    identifierID = models.CharField(
        max_length=255, db_index=True, db_column="identifier_id"
    )
    identifierType = models.CharField(
        max_length=20, db_index=True, db_column="identifier_type"
    )
    uniprotID = models.CharField(max_length=10, db_index=True, db_column="uniprot_id")

    def __str__(self):
        return "%s: %s (%s)" % (self.identifierType, self.identifierID, self.uniprotID)

    class Meta:
        db_table = "uniprot_identifier"
        managed = False


class HGNCIdentifier(models.Model):

    identifierID = models.CharField(
        max_length=255, primary_key=True, db_index=True, db_column="identifier_id"
    )
    identifierType = models.CharField(
        max_length=20, db_index=True, db_column="identifier_type"
    )
    uniprotID = models.CharField(max_length=10, db_index=True, db_column="uniprot_id")

    def __str__(self):
        return self.identifierID

    class Meta:
        db_table = "hgnc_identifiers"
        managed = False


# %% Sequences
class _Protein(models.Model):
    id = models.CharField(max_length=50, primary_key=True, db_column="protein_id")
    name = models.CharField(max_length=50, db_column="protein_name")

    description = models.CharField(max_length=255, blank=True)
    organism_name = models.CharField(max_length=255, blank=True)
    # gene_name = models.CharField(max_length=255, blank=True)

    # isoforms = models.IntegerField(null=True, blank=True)
    # sequence_version = models.IntegerField(null=True, blank=True)
    # db = models.CharField(max_length=12)

    seq = models.TextField(db_column="sequence")
    provean_supset_file = models.TextField()
    provean_supset_length = models.IntegerField()

    def __str__(self):
        return "%s (%s)" % (self.id, self.name)

    def desc(self):
        return self.description

    class Meta:
        abstract = True
        ordering = ["id"]


class Protein(_Protein):
    def getname(self):
        return get_protein_name(self.id, local=False)

    class Meta(_Protein.Meta):
        db_table = "elaspic_sequence"
        managed = False


class ProteinLocal(_Protein):
    """"""

    # id = models.IntegerField(primary_key=True, db_column='s_id')
    #
    # unique_id = models.CharField(max_length=255)
    # idx = models.IntegerField()
    #
    # sequence = models.TextField(null=True, blank=True)

    def getname(self):
        return get_protein_name(self.id, local=True)

    class Meta(_Protein.Meta):
        db_table = "elaspic_sequence_local"


@functools.lru_cache(maxsize=256, typed=False)
def get_protein_name(protein_id, local):
    """Find protein name in the database. Store result in lru cache.

    Parameters
    ----------
    protein_id : str
    local : True | False

    Returns
    -------
    str | None
    """
    if local:
        return _get_protein_name_local(protein_id)
    else:
        return _get_protein_name(protein_id)


def _get_protein_name_local(protein_id):
    try:
        name = ProteinLocal.objects.get(id=protein_id).name
    except ProteinLocal.DoesNotExist:
        name = None
    return name


def _get_protein_name(protein_id):
    try:
        name = HGNCIdentifier.objects.get(
            identifierType="HGNC_genename", uniprotID=protein_id
        ).identifierID
    except HGNCIdentifier.DoesNotExist:
        try:
            name = UniprotIdentifier.objects.get(
                identifierType="GeneWiki", uniprotID=protein_id
            ).identifierID
        except (
            UniprotIdentifier.DoesNotExist,
            UniprotIdentifier.MultipleObjectsReturned,
        ):
            try:
                protein_name = Protein.objects.get(id=protein_id).name
            except Protein.DoesNotExist:
                logger.error("Could not find protein: '{}'".format(protein_id))
                name = None
            else:
                name = protein_name.split("_")[0]
    except HGNCIdentifier.MultipleObjectsReturned:
        name = list(
            HGNCIdentifier.objects.filter(
                identifierType="HGNC_genename", uniprotID=protein_id
            )
        )[0].identifierID
    if "-" not in protein_id:
        return name
    else:
        return name + " isoform " + protein_id.split("-")[-1]


# %% Core
class _CoreModel(models.Model):
    @property
    def local(self):
        raise NotImplementedError

    @property
    def protein(self):
        return self.getprot()

    # Key
    id = models.AutoField(primary_key=True, db_index=True, db_column="domain_id")
    protein_id = models.CharField(max_length=15)
    domain_idx = models.IntegerField(db_index=True)

    # Domain
    clan = models.CharField(max_length=255, db_column="pfam_clan")
    name = models.CharField(max_length=255, db_index=True, db_column="pdbfam_name")
    alignment_def = models.CharField(max_length=255, db_column="alignment_def")

    data_path = models.TextField(blank=True, db_column="path_to_data")

    def get_protein_name(self, chain=1):
        return get_protein_name(self.protein_id, local=self.local)

    def getclan(self, chain=1):
        return self.clan if self.clan else "-"

    def getname(self, chain=1):
        return self.name

    def getdefs(self, chain=1):
        if self.model_domain_def:
            return self.model_domain_def
        elif self.domain_def:
            return self.domain_def
        return self.alignment_def

    # def __str__(self):
    #     return self.name

    # Template
    # align_file = models.CharField(max_length=255, blank=True, db_column='alignment_filename')
    align_score = models.IntegerField(
        null=True, blank=True, db_column="alignment_score"
    )
    align_coverage = models.FloatField(
        null=True, blank=True, db_column="alignment_coverage"
    )
    template_errors = models.TextField(
        blank=True, null=True, db_column="template_errors"
    )
    domain_def = models.CharField(max_length=255, blank=True)
    cath = models.CharField(max_length=255, blank=True, db_column="cath_id")
    seq_id = models.FloatField(null=True, blank=True, db_column="alignment_identity")

    def getcath(self, chain=1):
        return self.cath[:-2]

    def getSeqId(self, chain=1):
        return self.seq_id

    def getAlnSc(self, chain=1):
        if chain == 1:
            return self.align_score
        elif chain == 2:
            return "-"

    def getsequenceidentity(self, chain=1):
        return "%0.3f" % self.seq_id

    def getalignscore(self, chain=1):
        return "%0.3f" % self.align_score

    @property
    def error(self):
        if self.model_errors:
            return self.model_errors
        if self.template_errors:
            return self.template_errors
        return None

    # def __str__(self):
    #     return '%d' % self.domain_id

    # Model
    model_errors = models.TextField(blank=True, null=True, db_column="model_errors")
    dope_score = models.FloatField(null=True, blank=True, db_column="norm_dope")
    model_filename = models.CharField(max_length=255, blank=True)
    alignment_filename = models.CharField(max_length=255, blank=True)
    chain = models.CharField(max_length=1, null=True)
    model_domain_def = models.CharField(max_length=255)

    def getchain(self, chain):
        return self.chain

    def __str__(self):
        return "{}.{}.{}".format(self.id, self.protein_id, self.domain_idx)

    class Meta:
        abstract = True
        unique_together = [
            ("protein_id", "domain_idx"),
        ]
        ordering = ["id"]


class CoreModel(_CoreModel):

    local = False
    interactions = models.ManyToManyField(
        "self", symmetrical=False, through="InterfaceModel", blank=True
    )

    # protein = models.ForeignKey(Protein, db_index=True, db_column='protein_id')

    def getprot(self, chain=1):
        return Protein.objects.get(id=self.protein_id)

    def getpdbtemplate(self, chain=1, link=True):
        pdb = self.cath[:-3] + "_" + self.cath[-3]
        if link:
            return (
                '<a class="click2" target="_blank" href="http://www.cathdb.info/pdb/%s">%s</a>'
                % (self.cath[:-3], pdb)
            )
        return pdb

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        # self.protein = Protein.objects.get(id=self.protein_id)

    class Meta(_CoreModel.Meta):
        db_table = "elaspic_core_model"
        managed = False


class CoreModelLocal(_CoreModel):

    local = True
    interactions = models.ManyToManyField(
        "self", symmetrical=False, through="InterfaceModelLocal", blank=True
    )

    # protein = models.ForeignKey(ProteinLocal, db_index=True, db_column='protein_id')

    def getprot(self, chain=1):
        return ProteinLocal.objects.get(id=self.protein_id)

    def getpdbtemplate(self, chain=1, link=True):
        return self.cath

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        # self.protein = ProteinLocal.objects.get(id=self.protein_id)

    class Meta(_CoreModel.Meta):
        db_table = "elaspic_core_model_local"


# %% Core Mutation
class _CoreMutation(models.Model):

    mutation_type = "core"

    @property
    def protein(self):
        raise NotImplementedError

    # Key
    protein_id = models.CharField(max_length=15, primary_key=True)
    # domain_id = models.AutoField(primary_key=True, db_column='domain_id', db_index=True)
    domain_idx = models.IntegerField(db_index=True)
    mut = models.CharField(max_length=8, db_column="mutation")

    # Data
    mut_date_modified = models.DateField()

    model_filename_wt = models.CharField(max_length=255)
    model_filename_mut = models.CharField(max_length=255)

    mut_errors = models.TextField(null=True, blank=True, db_column="mutation_errors")

    pdb_chain = models.CharField(max_length=1, null=True, db_column="chain_modeller")
    pdb_mut = models.CharField(max_length=8, null=True, db_column="mutation_modeller")

    stability_energy_wt = models.TextField(null=True)
    stability_energy_mut = models.TextField(null=True)

    physchem_wt = models.CharField(max_length=255, null=True)
    physchem_wt_ownchain = models.CharField(max_length=255, null=True)
    physchem_mut = models.CharField(max_length=255, null=True)
    physchem_mut_ownchain = models.CharField(max_length=255, null=True)

    secondary_structure_wt = models.CharField(max_length=1, null=True)
    secondary_structure_mut = models.CharField(max_length=1, null=True)
    solvent_accessibility_wt = models.FloatField(null=True, blank=True)
    solvent_accessibility_mut = models.FloatField(null=True, blank=True)

    matrix_score = models.FloatField(null=True, blank=True)
    provean_score = models.FloatField(null=True, blank=True)

    ddG = models.FloatField(null=True, blank=True, db_column="ddg")

    elaspic_version = models.CharField(max_length=255)

    protbert_score = models.FloatField(null=True, blank=True)
    proteinsolver_score = models.FloatField(null=True, blank=True)
    el2_score = models.FloatField(null=True, blank=True)
    el2_version = models.CharField(max_length=255, null=True, blank=True)

    def getdomain(self, chain=1):
        return self.model

    def dGwt(self):
        return (
            self.stability_energy_wt.split(",")[0] if self.stability_energy_wt else None
        )

    def dGmut(self):
        return (
            self.stability_energy_mut.split(",")[0]
            if self.stability_energy_mut
            else None
        )

    def getddG(self):
        return self.ddG if self.ddG else "-"

    def findChain(self):
        return 1

    def __str__(self):
        return "{}.{}".format(self.protein_id, self.mut)

    class Meta:
        abstract = True
        # ordering = ['id']
        unique_together = [
            ("protein_id", "model", "mut"),
        ]
        index_together = [
            ("protein_id", "mut"),
        ]


class CoreMutation(_CoreMutation):

    model = models.ForeignKey(
        CoreModel, db_column="domain_id", related_name="muts", on_delete=models.CASCADE
    )

    @property
    def protein(self):
        return Protein.objects.get(id=self.protein_id)

    # protein = models.ForeignKey(Protein, db_index=True, db_column='protein_id')

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        # self.protein = Protein.objects.get(id=self.protein_id)

    class Meta(_CoreMutation.Meta):
        db_table = "elaspic_core_mutation"
        managed = False


class CoreMutationLocal(_CoreMutation):

    model = models.ForeignKey(
        CoreModelLocal,
        db_column="domain_id",
        related_name="muts",
        on_delete=models.CASCADE,
    )

    @property
    def protein(self):
        return ProteinLocal.objects.get(id=self.protein_id)

    # protein = models.ForeignKey(ProteinLocal, db_index=True, db_column='protein_id')

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        # self.protein = ProteinLocal.objects.get(id=self.protein_id)

    class Meta(_CoreMutation.Meta):
        db_table = "elaspic_core_mutation_local"


# %% Interface
class _InterfaceModel(models.Model):
    @property
    def local(self):
        raise NotImplementedError

    # Key
    id = models.AutoField(primary_key=True, db_index=True, db_column="interface_id")
    protein_id_1 = models.CharField(max_length=15)
    # domain_id_1 = models.IntegerField(db_index=True)
    # domain_idx_1 = models.IntegerField(db_index=True)
    protein_id_2 = models.CharField(max_length=15)
    # domain_id_2 = models.IntegerField(db_index=True)
    # domain_idx_2 = models.IntegerField(db_index=True)

    # domain pair
    data_path = models.TextField(blank=True, db_column="path_to_data")

    def get_protein_name(self, chain=1):
        if chain == 1:
            return get_protein_name(self.protein_id_1, local=self.local)
        elif chain == 2:
            return get_protein_name(self.protein_id_2, local=self.local)
        else:
            raise ValueError

    def getclan(self, chain):
        if chain == 1:
            return self.domain1.getclan()
        elif chain == 2:
            return self.domain2.getclan()

    def getname(self, chain):
        if chain == 1:
            return self.domain1.name
        elif chain == 2:
            return self.domain2.name

    def getdefs(self, chain):
        try:
            if chain == 1:
                defs = self.model_domain_def_1
            elif chain == 2:
                defs = self.model_domain_def_2
            if defs:
                return defs
        except Exception:
            pass
        if chain == 1:
            return self.domain1.getdefs()
        elif chain == 2:
            return self.domain2.getdefs()

    def getdomain(self, chain):
        if chain == 1:
            return self.domain1
        elif chain == 2:
            return self.domain2

    # def __str__(self):
    #     return '%s-%s' % (self.domain1_id, self.domain2_id)

    # domain pair template
    align_score1 = models.IntegerField(
        null=True, blank=True, db_column="alignment_score_1"
    )
    align_score2 = models.IntegerField(
        null=True, blank=True, db_column="alignment_score_2"
    )

    align_coverage_1 = models.IntegerField(
        null=True, blank=True, db_column="alignment_coverage_1"
    )
    align_coverage_2 = models.IntegerField(
        null=True, blank=True, db_column="alignment_coverage_2"
    )

    cath1 = models.CharField(max_length=255, blank=True, db_column="cath_id_1")
    cath2 = models.CharField(max_length=255, blank=True, db_column="cath_id_2")

    seq_id1 = models.FloatField(null=True, blank=True, db_column="alignment_identity_1")
    seq_id2 = models.FloatField(null=True, blank=True, db_column="alignment_identity_2")

    errors = models.TextField(null=True, blank=True, db_column="template_errors")

    def getcath(self, chain):
        if chain == 1:
            return self.cath1[:-2]
        elif chain == 2:
            return self.cath2[:-2]

    def getSeqId(self, chain):
        if chain == 1:
            return self.seq_id1
        elif chain == 2:
            return self.seq_id2

    def getAlnSc(self, chain):
        if chain == 1:
            return self.align_score1
        elif chain == 2:
            return self.align_score2

    def getsequenceidentity(self, chain):
        if chain == 1:
            return "%0.3f, %0.3f" % (self.seq_id1, self.seq_id2)
        elif chain == 2:
            return "%0.3f, %0.3f" % (self.seq_id2, self.seq_id1)

    def getalignscore(self, chain):
        if chain == 1:
            return "%0.3f, %0.3f" % (self.align_score1, self.align_score2)
        elif chain == 2:
            return "%0.3f, %0.3f" % (self.align_score2, self.align_score1)

    # def __str__(self):
    #     return '%d' % self.domain_id

    # domain pair model
    model_domain_def_1 = models.CharField(max_length=255)
    model_domain_def_2 = models.CharField(max_length=255)
    model_errors = models.TextField(null=True, blank=True)
    dope_score = models.FloatField(null=True, blank=True, db_column="norm_dope")
    model_filename = models.CharField(max_length=255, blank=True)

    alignment_filename_1 = models.CharField(max_length=255, blank=True)
    alignment_filename_2 = models.CharField(max_length=255, blank=True)

    aa1 = models.TextField(blank=True, db_column="interacting_aa_1")
    aa2 = models.TextField(blank=True, db_column="interacting_aa_2")

    chain_1 = models.CharField(max_length=1, null=True)
    chain_2 = models.CharField(max_length=1, null=True)

    interface_area_hydrophobic = models.FloatField(null=True, blank=True)
    interface_area_hydrophilic = models.FloatField(null=True, blank=True)
    interface_area_total = models.FloatField(null=True, blank=True)

    def getchain(self, chain):
        if chain == 1:
            return self.chain_1
        elif chain == 2:
            return self.chain_2

    def __str__(self):
        return "{}-{}-{}".format(self.id, self.protein_id_1, self.protein_id_2)

    class Meta:
        abstract = True
        ordering = ["id"]


class InterfaceModel(_InterfaceModel):

    local = False
    domain1 = models.ForeignKey(
        CoreModel,
        db_index=True,
        related_name="p1",
        db_column="domain_id_1",
        on_delete=models.CASCADE,
    )
    domain2 = models.ForeignKey(
        CoreModel,
        db_index=True,
        related_name="p2",
        db_column="domain_id_2",
        on_delete=models.CASCADE,
    )

    def getprot(self, chain):
        if chain == 1:
            return Protein.objects.get(id=self.protein_id_1)
        elif chain == 2:
            return Protein.objects.get(id=self.protein_id_2)

    def getpdbtemplate(self, chain, link=True):
        if link:
            a1 = (
                '<a class="click2" target="_blank" href="http://www.cathdb.info/pdb/%s">%s_%s</a>'
                % (self.cath1[:-3], self.cath1[:-3], self.cath1[-3])
            )
            a2 = (
                '<a class="click2" target="_blank" href="http://www.cathdb.info/pdb/%s">%s_%s</a>'
                % (self.cath2[:-3], self.cath2[:-3], self.cath2[-3])
            )
        else:
            a1 = self.cath1[:-3] + "_" + self.cath1[-3]
            a2 = self.cath2[:-3] + "_" + self.cath2[-3]
        if chain == 1:
            return "%s, %s" % (a1, a2)
        elif chain == 2:
            return "%s, %s" % (a2, a1)

    class Meta(_InterfaceModel.Meta):
        db_table = "elaspic_interface_model"
        managed = False


class InterfaceModelLocal(_InterfaceModel):

    local = True
    domain1 = models.ForeignKey(
        CoreModelLocal,
        db_index=True,
        related_name="p1",
        db_column="domain_id_1",
        on_delete=models.CASCADE,
    )
    domain2 = models.ForeignKey(
        CoreModelLocal,
        db_index=True,
        related_name="p2",
        db_column="domain_id_2",
        on_delete=models.CASCADE,
    )

    def getprot(self, chain):
        if chain == 1:
            return ProteinLocal.objects.get(id=self.protein_id_1)
        elif chain == 2:
            return ProteinLocal.objects.get(id=self.protein_id_2)

    def getpdbtemplate(self, chain, link=True):
        if chain == 1:
            return "{}, {}".format(self.cath1, self.cath2)
        elif chain == 2:
            return "{}, {}".format(self.cath2, self.cath1)

    class Meta(_InterfaceModel.Meta):
        db_table = "elaspic_interface_model_local"


# %% Interface Mutation
class _InterfaceMutation(models.Model):

    mutation_type = "interface"  # interface

    @property
    def protein(self):
        raise NotImplementedError

    # Key
    # interface_id = models.IntegerField(primary_key=True, db_index=True)
    # protein_id_1 = models.CharField(max_length=15)
    # domain_id_1 = models.IntegerField(db_index=True)
    # protein_id_2 = models.CharField(max_length=15)
    # domain_id_2 = models.IntegerField(db_index=True)
    protein_id = models.CharField(max_length=15, primary_key=True)
    mut = models.CharField(max_length=8, db_column="mutation")
    chain_idx = models.IntegerField()

    # Data
    mut_date_modified = models.DateField()

    model_filename_wt = models.CharField(max_length=255)
    model_filename_mut = models.CharField(max_length=255)

    mut_errors = models.TextField(null=True, blank=True, db_column="mutation_errors")

    pdb_chain = models.CharField(max_length=1, null=True, db_column="chain_modeller")
    pdb_mut = models.CharField(max_length=8, null=True, db_column="mutation_modeller")

    stability_energy_wt = models.TextField(null=True)
    stability_energy_mut = models.TextField(null=True)
    analyse_complex_energy_wt = models.TextField(null=True)
    analyse_complex_energy_mut = models.TextField(null=True)

    physchem_wt = models.CharField(max_length=255, null=True)
    physchem_wt_ownchain = models.CharField(max_length=255, null=True)
    physchem_mut = models.CharField(max_length=255, null=True)
    physchem_mut_ownchain = models.CharField(max_length=255, null=True)

    secondary_structure_wt = models.CharField(max_length=1, null=True)
    secondary_structure_mut = models.CharField(max_length=1, null=True)
    solvent_accessibility_wt = models.FloatField(null=True, blank=True)
    solvent_accessibility_mut = models.FloatField(null=True, blank=True)

    contact_distance_wt = models.FloatField(null=True, blank=True)
    contact_distance_mut = models.FloatField(null=True, blank=True)

    matrix_score = models.FloatField(null=True, blank=True)
    provean_score = models.FloatField(null=True, blank=True)

    ddG = models.FloatField(null=True, blank=True, db_column="ddg")

    protbert_score = models.FloatField(null=True, blank=True)
    proteinsolver_score = models.FloatField(null=True, blank=True)
    el2_score = models.FloatField(null=True, blank=True)
    el2_version = models.CharField(max_length=255, null=True, blank=True)

    elaspic_version = models.CharField(max_length=255)

    def getdomain(self, chain):
        return self.model.getdomain(chain)

    def dGwt(self):
        try:
            dGwt = self.analyse_complex_energy_wt.split(",")[2]
        except AttributeError:
            dGwt = None
        return dGwt

    def dGmut(self):
        try:
            dGmut = self.analyse_complex_energy_mut.split(",")[2]
        except AttributeError:
            dGmut = None
        return dGmut

    def getddG(self):
        return self.ddG if self.ddG else "-"

    def findChain(self):
        if self.chain_idx == 0:
            return 1
        elif self.chain_idx == 1:
            return 2
        elif self.protein_id == self.model.protein_id_1:
            return 1
        elif self.protein_id == self.model.protein_id_2:
            return 2
        else:
            raise ValueError(
                "self.chain_idx: {}, self.protein_id: {}".format(
                    self.chain_idx, self.protein_id
                )
            )

    def getinacprot(self, chain=None):
        c = chain or self.findChain()
        if c == 1:
            return self.model.getprot(2)
        elif c == 2:
            return self.model.getprot(1)

    def __str__(self):
        return "%s.%s" % (self.protein_id, self.mut)

    class Meta:
        abstract = True


class InterfaceMutation(_InterfaceMutation):

    model = models.ForeignKey(
        InterfaceModel,
        db_column="interface_id",
        related_name="muts",
        on_delete=models.CASCADE,
    )

    @property
    def protein(self):
        return Protein.objects.get(id=self.protein_id)

    # protein = models.ForeignKey(Protein, db_index=True, db_column='protein_id')

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        # self.protein = Protein.objects.get(id=self.protein_id)

    class Meta(_InterfaceMutation.Meta):
        db_table = "elaspic_interface_mutation"
        managed = False


class InterfaceMutationLocal(_InterfaceMutation):

    model = models.ForeignKey(
        InterfaceModelLocal,
        db_column="interface_id",
        related_name="muts",
        on_delete=models.CASCADE,
    )

    @property
    def protein(self):
        return ProteinLocal.objects.get(id=self.protein_id)

    # protein = models.ForeignKey(ProteinLocal, db_index=True, db_column='protein_id')

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        # self.protein = ProteinLocal.objects.get(id=self.protein_id)

    class Meta(_InterfaceMutation.Meta):
        db_table = "elaspic_interface_mutation_local"


# %% Database: 'elaspic_mutation'
class DatabaseClinVar(models.Model):

    id = models.PositiveIntegerField(primary_key=True, db_column="id")
    protein_id = models.CharField(max_length=50, db_column="uniprot_id")
    mut = models.CharField(max_length=8, db_column="mutation")

    variation = models.CharField(max_length=50, db_column="variation_name")

    def makeLink(self):
        return (
            "http://www.ensembl.org/Homo_sapiens/Variation/Explore?v=" + self.variation
        )

    class Meta:
        db_table = "clinvar_mutation"
        managed = False


class DatabaseUniProt(models.Model):

    id = models.PositiveIntegerField(primary_key=True, db_column="id")
    protein_id = models.CharField(max_length=50, db_column="uniprot_id")
    mut = models.CharField(max_length=8, db_column="mutation")

    variation = models.CharField(max_length=50, db_column="variation_name")

    def makeLink(self):
        return "http://web.expasy.org/variant_pages/" + self.variation + ".html"

    class Meta:
        db_table = "uniprot_mutation"
        managed = False


class DatabaseCOSMIC(models.Model):

    id = models.PositiveIntegerField(primary_key=True, db_column="id")
    protein_id = models.CharField(max_length=50, db_column="uniprot_id")
    mut = models.CharField(max_length=8, db_column="mutation")

    variation = models.CharField(max_length=50, db_column="variation_name")

    def makeLink(self):
        return (
            "http://www.ensembl.org/Homo_sapiens/Variation/Explore?v=" + self.variation
        )

    class Meta:
        db_table = "cosmic_mutation"
        managed = False


def findInDatabase(mutations, protein_id):
    logger.debug("findInDatabase({}, {})".format(mutations, protein_id))
    dbs = defaultdict(list)

    for db in (DatabaseClinVar, DatabaseUniProt, DatabaseCOSMIC):
        for mut_db in db.objects.filter(mut__in=mutations, protein_id=protein_id):
            dbs[mut_db.mut].append(
                {
                    "name": mut_db.__class__.__name__[8:],
                    "url": mut_db.makeLink(),
                    "variation": mut_db.variation,
                }
            )
    logger.debug("dbs: '{}'".format(dbs))
    return dbs
