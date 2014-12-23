import os
from argparse import ArgumentParser

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, String, BigInteger, Integer
from sqlalchemy.orm import sessionmaker


engine = create_engine('postgresql://elaspic:elaspic@192.168.6.19:5432/kimlab')
Session = sessionmaker(bind=engine)

Base = declarative_base()



#class Protein(Base):
#    __tablename__ = 'uniprot_sequence'
#    __table_args__ = ({'schema': 'uniprot_kb'},)
#
#    uniprot_id = Column(String(50, collation='en_US.utf8'), primary_key=True, nullable=False)
#    uniprot_name = Column(String(255, collation='en_US.utf8'), nullable=False)
#    #uniprot_description = Column(String(255, collation='en_US.utf8'))
#    uniprot_sequence = Column(Text, nullable=False)
#
#
#class Identifier(Base):
#    __tablename__ = 'identifiers'
#    __table_args__ = ({'schema': 'elaspic'},)
#    
#    identifier_id = Column(String(255, collation='en_US.utf8'), primary_key=True, index=True, nullable=False)
#    identifier_type = Column(String(50, collation='en_US.utf8'), nullable=False)
#
#    uniprotID_id = Column(String(50, collation='en_US.utf8'), ForeignKey(Protein.uniprot_id), index=True, nullable=False)
#    uniprot_sequence = relationship(Protein, backref='identifier') # many to one
#    

class UniprotIdentifier(Base):
    __tablename__ = 'uniprot_identifier'
    __table_args__ = ({'sqlite_autoincrement': True, 'schema': 'uniprot_kb'},)
    
    id = Column(BigInteger, primary_key=True)   
    
    identifier_id = Column(String(255, collation='en_US.utf8'), primary_key=True, index=True, nullable=False)
    identifier_type = Column(String(20, collation='en_US.utf8'), index=True, nullable=False)
    uniprot_id = Column(String(10, collation='en_US.utf8'), index=True, nullable=False)

class HGNCIdentifier(Base):
    __tablename__ = 'hgnc_identifiers'
    __table_args__ = ({'sqlite_autoincrement': True, 'schema': 'uniprot_kb'},)
    
    identifier_id = Column(String(255, collation='en_US.utf8'), primary_key=True, unique=True, index=True, nullable=False)
    identifier_type = Column(String(20, collation='en_US.utf8'), index=True, nullable=False)
    uniprot_id = Column(String(10, collation='en_US.utf8'), index=True, nullable=False)

Base.metadata.create_all(engine)

class Importer(object):
    
    def __init__(self, path, files):
        self.files = files
        
        self.session = Session()
    
    def importUniprot(self):
        
#        print 'Deleting old uniprot identifiers.'
#        self.session.query(UniprotIdentifier).delete()
#        self.session.commit()
#        
#        whitelist = ['neXtProt', 'PeroxiBase', 'H-InvDB', 'DIP', 'STRING', 'DisProt', 'EMBL', 'EMBL-CDS', 
#                     'MINT', 'OMA',  'REBASE', 'BioCyc', 'GeneWiki', 'UCSC', 'RefSeq', 'RefSeq_NT',
#                     'UniProtKB-ID', 'Ensembl', 'Ensembl_TRS', 'Ensembl_PRO','UniRef100']
    
#        # Count lines in file.
#        print 'Counting lines in uniprot file.'
        numLines = sum(1 for line in open(self.uniprotFile))
        print numLines
#        
#
#        print 'Importing %d uniprot identifiers to database.' % numLines
#        toImport = []
#        zeroPointOne = int(numLines / 1000)
#        haveDone = 0.0
#        #iDict = {}
#        with open(self.uniprotFile) as f:
#            for i, l in enumerate(f):
#                if not i:
#                    print l
#                line = l.split('\t')
#                if len(line) != 3:
#                    print 'oh no'
#                # 0: Uniprot ID
#                # 1: Type
#                # 2: Identifier/n
#
##                if line[1] not in whitelist:
##                    continue
#                
#                iden = line[2].strip()
#                if iden == '-':
#                    continue
#                toImport.append(UniprotIdentifier(identifier_id=iden, 
#                                                  identifier_type=line[1], 
#                                                  uniprot_id=line[0]))
#                # Upload every 10000.
#                if i % 10000 == 0:
#                    self.session.add_all(toImport)
#                    self.session.commit()
#                    del toImport[:]
#                # Print every 0.1% done.
#                if i % zeroPointOne == 0:
#                    print "%d (%0.1f%%) uploaded.." % (i, haveDone)
#                    haveDone += 0.1
#        
#            self.session.add_all(toImport)
#            self.session.commit()
#            print "%d (%0.1f%%) uploaded.." % (i, haveDone)

    
    def importHGNC(self):
        
        # HGNC identifiers.   # Old goes first to ensure overwrite. 

        self.session.query(HGNCIdentifier).delete()
        self.session.commit()

        idict = {}
        
        numLines = sum(1 for line in open(self.hgncFile))
        print "Processing HGNC identifiers. %d lines." % numLines
        
        # Old gene names.
        with open(self.hgncFile) as f:
            for i, l in enumerate(f):
                if not i:
                    continue
                line = l.split('\t')
                
                if line[3] == '\n':
                    continue
                prot = line[3].strip()
                
                if line[1]:
                    for iden in line[1].split(', '):
                        idict[iden] = [prot, 'HGNC_old']

        # Gene names and synonyms.
        with open(self.hgncFile) as f:
            for i, l in enumerate(f): 
                if not i:
                    continue
                line = l.split('\t')

                if line[3] == '\n':
                    continue
                prot = line[3].strip()
                
                if line[2]:
                    for iden in line[2].split(', '):
                        idict[iden] = [prot, 'HGNC_synonyms']
                
                idict[line[0]] = [prot, 'HGNC_genename']
    
        
        toImport = []
        for i, key in enumerate(idict):
            toImport.append(HGNCIdentifier(identifier_id=key, 
                                           identifier_type=idict[key][1], 
                                           uniprot_id=idict[key][0]))
            if i % 10000 == 0:
                self.session.add_all(toImport)
                self.session.commit()
                del toImport[:]
                print "%d uploaded.." % (i)
    
        self.session.add_all(toImport)
        self.session.commit()
        print 'All uploaded'
        
if __name__ == '__main__':
    
    # Set files.
    # 0 uniprot: ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/ 'idmapping.dat.gz'
    # 1 hgnc: http://www.genenames.org/cgi-bin/hgnc_downloads?col=gd_app_sym&col=gd_prev_sym&col=gd_aliases&col=md_prot_id&status=Approved&status_opt=2&where=%28%28gd_pub_chrom_map+not+like+%27%25patch%25%27+and+gd_pub_chrom_map+not+like+%27%25ALT_REF%25%27%29+or+gd_pub_chrom_map+IS+NULL%29&order_by=md_prot_id&format=text&limit=&hgnc_dbtag=on&submit=submit
    # 2 wormbase: ftp://ftp.wormbase.org/pub/wormbase/datasets-wormbase/gene_ids/
    path = '/home/witvliet/working/identifiers/'
    files = {'uniprot': 'idmapping.dat',
             'human': 'hgnc_downloads.txt',
             'worm': 'wormbase.gene_ids.txt'}
    
    # Load arguments.
    parser = ArgumentParser()
    parser.add_argument('-i', '--importtodb')
    args = parser.parse_args()
    
    # Import.
    i = Importer(path, files=files)
    
#    if not args.importtodb or args.importtodb == 'all' or args.importtodb == 'uniprot':
#        i.importUniprot()
#    if not args.importtodb or args.importtodb == 'all' or args.importtodb == 'hgnc':
#        i.importHGNC()
    