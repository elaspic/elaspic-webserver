from django.db import models

from django.utils.timezone import localtime

#
# To install: python /home/witvliet/Dropbox/django/mum/manage.py syncdb 
#
# Run shell: from web_pipeline.models import *
#
############################################################################
# Database: 'default'
# Engine: MySQL

shema = ''


class Mut(models.Model):
    TYPE_CHOICES = (
        ('NO', 'None'),
        ('CO', 'Core'),
        ('IN', 'Interaction'),
    )
    
    protein = models.CharField(max_length=50, db_index=True)
    mut = models.CharField(max_length=8)

    affectedType = models.CharField(max_length=2, choices=TYPE_CHOICES, blank=True)
    dateAdded = models.DateTimeField(auto_now_add=True)
    dateFinished = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, default='queued')
    
    rerun = models.SmallIntegerField(default=0)
    taskId = models.CharField(max_length=50, blank=True)
    
    error = models.TextField(blank=True, null=True) # AS + default=''

    #AS >>>
    provean_job_id = models.IntegerField(null=True)
    model_job_id = models.IntegerField(null=True)
    mutation_job_id = models.IntegerField(null=True)
    # <<<
    
    def __unicode__(self):
        return '%s.%s' % (self.protein, self.mut)
    
    class Meta:
        db_table = 'muts'
        #ordering = ['protein', 'mut']


class Job(models.Model):
    jobID = models.CharField(max_length=10, primary_key=True)
    dateRun = models.DateTimeField(auto_now_add=True)
    dateFinished = models.DateTimeField(null=True, blank=True)
    dateVisited = models.DateTimeField(auto_now_add=True)
    isDone = models.BooleanField(default=False)
    email = models.EmailField(blank=True)
    
    muts = models.ManyToManyField(Mut, through='JobToMut', related_name="jobs") #many-to-many

    browser = models.CharField(max_length=100, blank=True)
    
    
    def getDateRun(self):
        return localtime(self.dateRun)
        
    def getDateFinished(self):
        return localtime(self.dateFinished) if self.dateFinished else '-'
    
    
    def __unicode__(self):
        return self.jobID
        
    class Meta:
        db_table = 'jobs'
        get_latest_by = 'dateRun'
        ordering = ['jobID']


class JobToMut(models.Model):
    mut = models.ForeignKey(Mut) #intermediary model
    job = models.ForeignKey(Job) #intermediary model
    inputIdentifier = models.CharField(max_length=70)

    realMut = None
    realMutErr = None

    def __unicode__(self):
        return '#%s to mut%d' % (self.job_id, self.mut_id)
    
    class Meta:
        db_table = 'job_to_mut'



############################################################################
# Database: 'data'
# Engine: PostgreSQL

class Protein(models.Model):
    id = models.CharField(max_length=50, primary_key=True, db_index=True, db_column='uniprot_id')
    name = models.CharField(max_length=50, db_column='uniprot_name')
    
    description = models.CharField(max_length=255, db_column='protein_name', blank=True)
    organismName = models.CharField(max_length=255, db_column='organism_name', blank=True)
    geneName = models.CharField(max_length=255, db_column='gene_name', blank=True)
    
    isoforms = models.IntegerField(null=True, blank=True, db_column='protein_existence')
    seqVersion = models.IntegerField(null=True, blank=True, db_column='sequence_version')
    db = models.CharField(max_length=12, db_column='db')
    
    seq = models.TextField(db_column='uniprot_sequence')
    
    
    def desc(self):
        return self.description
        
    def getname(self):
        
        try:
            name = HGNCIdentifier.objects.using('uniprot').get(identifierType='HGNC_genename', uniprotID=self.id).identifierID
        except HGNCIdentifier.DoesNotExist:
            try:
                name = UniprotIdentifier.objects.using('uniprot').get(identifierType='GeneWiki', uniprotID=self.id).identifierID
            except (UniprotIdentifier.DoesNotExist, UniprotIdentifier.MultipleObjectsReturned):
                name = self.name.split('_')[0]
        except HGNCIdentifier.MultipleObjectsReturned:
            name = list(
                HGNCIdentifier
                .objects
                .using('uniprot')
                .filter(identifierType='HGNC_genename', uniprotID=self.id)
            )[0].identifierID
        
        if not '-' in self.id:
            return name
        else:
            return name + ' isoform ' + self.id.split('-')[-1]
    
    def __unicode__(self):
        return '%s (%s)' % (self.id, self.name)
        
    class Meta:
        db_table = 'uniprot_sequence'
        ordering = ['id']

class UniprotIdentifier(models.Model):
    id = models.AutoField(primary_key=True, db_index=True)
    
    identifierID = models.CharField(max_length=255, db_index=True, db_column='identifier_id') # primary_key=True,
    identifierType = models.CharField(max_length=20, db_index=True, db_column='identifier_type')
    uniprotID = models.CharField(max_length=10, db_index=True, db_column='uniprot_id')
    
    def __unicode__(self):
        return "%s: %s (%s)" % (self.identifierType, self.identifierID, self.uniprotID)

    class Meta:
        db_table = 'uniprot_identifier'

#from django.db.models import fields
#from south.modelsinspector import add_introspection_rules
#
#class BigAutoField(fields.AutoField):
#    def db_type(self, connection):
#        if 'mysql' in connection.__class__.__module__:
#            return 'bigint AUTO_INCREMENT'
#        return super(BigAutoField, self).db_type(connection)
#
#add_introspection_rules([], ["^MYAPP\.fields\.BigAutoField"])

class HGNCIdentifier(models.Model):

    identifierID = models.CharField(max_length=255, primary_key=True, db_index=True, db_column='identifier_id')
    identifierType = models.CharField(max_length=20, db_index=True, db_column='identifier_type')
    uniprotID = models.CharField(max_length=10, db_index=True, db_column='uniprot_id')
    
    def __unicode__(self):
        return self.identifierID

    class Meta:
        db_table = 'hgnc_identifiers'

class Domain(models.Model):
    id = models.AutoField(primary_key=True, db_index=True, db_column='uniprot_domain_id')
    
    clan = models.CharField(max_length=255, db_column='pfam_clan')
    name = models.CharField(max_length=255, db_index=True, db_column='pdbfam_name')
    defs = models.CharField(max_length=255, db_column='alignment_def')
    
    data_path = models.TextField(blank=True, db_column='path_to_data')
    
    protein_id = models.CharField(max_length=10, db_column='uniprot_id') #many-to-one
    interactions = models.ManyToManyField('self', symmetrical=False, through='Interaction', null=True, blank=True) #many-to-many
    
    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        self.protein = Protein.objects.using('uniprot').get(id=self.protein_id)

    def getclan(self, chain=1):
        return self.clan if self.clan else '-'

    def getname(self, chain=1):
        return self.name

    def getprot(self, chain=1):
        return self.protein

    def getdefs(self, chain=1):
        try:
            defs = self.template.defs
        except Exception:
            return self.defs
        else:
            if not defs:
                return self.defs

        return defs

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = shema + 'uniprot_domain'
        ordering = ['defs']

class Interaction(models.Model):
    id = models.IntegerField(primary_key=True, db_index=True, db_column='uniprot_domain_pair_id')
    domain1 = models.ForeignKey(Domain, db_index=True, related_name='p1', db_column='uniprot_domain_id_1') #intermediary model
    domain2 = models.ForeignKey(Domain, db_index=True, related_name='p2', db_column='uniprot_domain_id_2') #intermediary model    
    
    data_path = models.TextField(blank=True, db_column='path_to_data')

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
                defs = self.itemplate.domain_def1
            elif chain == 2:
                defs = self.itemplate.domain_def2
            if defs:
                return defs
        except Exception:
            pass
        if chain == 1:
            return self.domain1.defs
        elif chain == 2:
            return self.domain2.defs

    def getdomain(self, chain):
        if chain == 1:
            return self.domain1
        elif chain == 2:
            return self.domain2

    def getprot(self, chain):
        if chain == 1:
            return self.domain1.protein
        elif chain == 2:
            return self.domain2.protein

    def __unicode__(self):
        return '%s-%s' % (self.domain1_id, self.domain2_id)

    class Meta:
        db_table = shema + 'uniprot_domain_pair'

class Template(models.Model):
    domain = models.OneToOneField(Domain, primary_key=True, db_index=True, db_column='uniprot_domain_id') #one-to-one
    #align_file = models.CharField(max_length=255, blank=True, db_column='alignment_filename')
    align_score = models.IntegerField(null=True, blank=True, db_column='alignment_score')
    errors = models.TextField(blank=True, db_column='template_errors')
    defs = models.CharField(max_length=255, blank=True, db_column='domain_def')
    cath = models.CharField(max_length=255, blank=True, db_column='cath_id')
    
    seq_id = models.FloatField(null=True, blank=True, db_column='alignment_identity')

    def getcath(self, chain=1):
        return self.cath[:-2]

    def getSeqId(self, chain=1):
        return self.seq_id

    def getAlnSc(self, chain=1):
        if chain == 1:
            return self.align_score
        elif chain == 2:
            return '-'

    def getAlnFi(self, chain=1):
        if chain == 1:
            return self.model.alignment_filename
        elif chain == 2:
            return '-'

    def getsequenceidentity(self, chain=1):
        return '%0.3f' % self.seq_id

    def getalignscore(self, chain=1):
        return '%0.3f' % self.align_score
        

    def __unicode__(self):
        return '%d' % self.domain_id

    class Meta:
        db_table = shema + 'uniprot_domain_template'
        ordering = ['domain']
        
class Itemplate(models.Model):
    domain = models.OneToOneField(Interaction, primary_key=True, db_index=True, db_column='uniprot_domain_pair_id') #one-to-one
    
    align_score1 = models.IntegerField(null=True, blank=True, db_column='score_1')
    align_score2 = models.IntegerField(null=True, blank=True, db_column='score_2')
    
    cath1 = models.CharField(max_length=255, blank=True, db_column='cath_id_1')
    cath2 = models.CharField(max_length=255, blank=True, db_column='cath_id_2')
    
    seq_id1 = models.FloatField(null=True, blank=True, db_column='identical_1')
    seq_id2 = models.FloatField(null=True, blank=True, db_column='identical_2')
    
    
    errors = models.TextField(blank=True, db_column='template_errors')
    
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

    def getAlnFi(self, chain):
        if chain == 1:
            return self.imodel.alignment_filename_1
        elif chain == 2:
            return self.imodel.alignment_filename_2

    def getsequenceidentity(self, chain):
        if chain == 1:
            return '%0.3f, %0.3f' % (self.seq_id1, self.seq_id2)
        elif chain == 2:
            return '%0.3f, %0.3f' % (self.seq_id2, self.seq_id1)

    def getalignscore(self, chain):
        if chain == 1:
            return '%0.3f, %0.3f' % (self.align_score1, self.align_score2)
        elif chain == 2:
            return '%0.3f, %0.3f' % (self.align_score2, self.align_score1)
    
    def __unicode__(self):
        return '%d' % self.domain_id

    class Meta:
        db_table = shema + 'uniprot_domain_pair_template'
        ordering = ['domain']

class Model(models.Model):
    template = models.OneToOneField(Template, primary_key=True, db_index=True, db_column='uniprot_domain_id') #one-to-one
    errors = models.TextField(blank=True, db_column='model_errors')
    dope_score = models.FloatField(null=True, blank=True, db_column='norm_dope')
    model_filename = models.CharField(max_length=255, blank=True)
    alignment_filename = models.CharField(max_length=255, blank=True)
    chain = models.CharField(max_length=1, null=True)
    
    def getchain(self, chain):    
        return self.chain
    
    def __unicode__(self):
        return '%d' % self.template_id

    class Meta:
        db_table = shema + 'uniprot_domain_model'
        ordering = ['template']


class Imodel(models.Model):
    template = models.OneToOneField(Itemplate, primary_key=True, db_index=True, db_column='uniprot_domain_pair_id') #one-to-one
    errors = models.TextField(null=True, db_column='model_errors')
    dope_score = models.FloatField(null=True, blank=True, db_column='norm_dope')
    model_filename = models.CharField(max_length=255, blank=True)
    
    alignment_filename_1 = models.CharField(max_length=255, blank=True)
    alignment_filename_2 = models.CharField(max_length=255, blank=True)
    
    aa1 = models.TextField(blank=True, db_column='interacting_aa_1')
    aa2 = models.TextField(blank=True, db_column='interacting_aa_2')
    
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

    def __unicode__(self):
        return '%d' % self.template_id

    class Meta:
        db_table = shema + 'uniprot_domain_pair_model'
        ordering = ['template']


class Mutation(models.Model):
    
    mut_date_modified = models.DateField()

    model_filename_wt = models.CharField(max_length=255, primary_key=True)
    model_filename_mut = models.CharField(max_length=255)
    
    mut = models.CharField(max_length=8, db_column='mutation')
    mut_errors = models.TextField(null=True, db_column='mutation_errors')

    pdb_chain = models.CharField(max_length=1, null=True, db_column='chain_modeller')
    pdb_mut = models.CharField(max_length=8, null=True, db_column='mutation_modeller')
    
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
    
    ddG = models.FloatField(null=True, blank=True, db_column='ddg')
    dGwt = None
    dGmut = None


    protein_id = models.CharField(max_length=10, db_column='uniprot_id') #many-to-one
    model = models.ForeignKey(Model, db_column='uniprot_domain_id', db_index=True) #many-to-one 
    
    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        self.protein = Protein.objects.using('uniprot').get(id=self.protein_id)

    def dGwt(self):
        return self.stability_energy_wt.split(',')[0] if self.stability_energy_wt else None
    
    def dGmut(self):
        return self.stability_energy_mut.split(',')[0] if self.stability_energy_mut else None
    
    def getddG(self):
        return self.ddG if self.ddG else '-'
    
    def findChain(self):
        return 1

    def __unicode__(self):
        return '%s.%s' % (self.protein_id, self.mut)
        
    class Meta:
        db_table = shema + 'uniprot_domain_mutation'
        

class Imutation(models.Model):
    
    mut_date_modified = models.DateField()

    model_filename_wt = models.CharField(max_length=255, primary_key=True)
    model_filename_mut = models.CharField(max_length=255)
    
    mut = models.CharField(max_length=8, db_column='mutation')
    mut_errors = models.TextField(null=True, db_column='mutation_errors')

    pdb_chain = models.CharField(max_length=1, null=True, db_column='chain_modeller')
    pdb_mut = models.CharField(max_length=8, null=True, db_column='mutation_modeller')
    
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
    
    ddG = models.FloatField(null=True, blank=True, db_column='ddg')

    protein_id = models.CharField(max_length=10, db_column='uniprot_id') #many-to-one
    model = models.ForeignKey(Imodel, db_column='uniprot_domain_pair_id', db_index=True) #many-to-one  

    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        self.protein = Protein.objects.using('uniprot').get(id=self.protein_id)

    def dGwt(self):
        try:
            dGwt = self.analyse_complex_energy_wt.split(',')[2]
        except AttributeError:
            dGwt = None
        return dGwt
    
    def dGmut(self):
        try:
            dGmut = self.analyse_complex_energy_mut.split(',')[2]
        except AttributeError:
            dGmut = None
        return dGmut
        
    def getddG(self):
        return self.ddG if self.ddG else '-'

    def findChain(self):
        if self.protein == self.model.template.domain.domain1.protein:
            return 1
        elif self.protein == self.model.template.domain.domain2.protein:
            return 2
    
    def getinacprot(self, chain=None):
        c = chain or self.findChain()
        if c == 1:
            return self.model.template.domain.getprot(2)
        elif c == 2:
            return self.model.template.domain.getprot(1)

    def __unicode__(self):
        return '%s.%s' % (self.protein_id, self.mut)
        
    class Meta:
        db_table = shema + 'uniprot_domain_pair_mutation'



############################################################################
# Old stuff




#class VersionControl(models.Model):
#    dbVersion = models.CharField(max_length=15, primary_key=True)
#    dateUpdated = models.DateTimeField(auto_now_add=True)
#    identifierCount = models.PositiveIntegerField(null=True, blank=True)
#    proteinCount = models.PositiveIntegerField(null=True, blank=True)
#    #proteinStructureCount = models.PositiveIntegerField(null=True, blank=True)
#    interactionCount = models.PositiveIntegerField(null=True, blank=True)
#    mutationCount = models.PositiveIntegerField(null=True, blank=True)
#    domainCount = models.PositiveIntegerField(null=True, blank=True)
#    domainUniqueCount = models.PositiveIntegerField(null=True, blank=True)
#    elmCount = models.PositiveIntegerField(null=True, blank=True)
#    elmUniqueCount = models.PositiveIntegerField(null=True, blank=True)
#    jobCount = models.PositiveIntegerField(null=True, blank=True)
#    
#    class Meta:
#        db_table = 'version_control'
#        get_latest_by = 'dateUpdated'
#        
#    def __unicode__(self):
#        return self.dbVersion


#class InteractionInfo(models.Model):
#    THROUGHPUT_CHOICES = (
#        ('H', 'High Throughput'),
#        ('L', 'Low Throughput'),
#    )
#    interaction = models.ForeignKey(Interaction) #many-to-one
#    author = models.CharField(max_length=50, blank=True)
#    year = models.PositiveSmallIntegerField(null=True, blank=True)
#    pubmedID = models.PositiveIntegerField(null=True, blank=True)
#    system = models.CharField(max_length=40, blank=True)
#    database = models.CharField(max_length=8)
#    throughput = models.CharField(max_length=1, choices=THROUGHPUT_CHOICES, blank=True)   
# 
#    def __unicode__(self):
#        return self.database
#        
#    class Meta:
#        db_table = 'interaction_info'
#        ordering = ['database', 'author', 'year', 'system']