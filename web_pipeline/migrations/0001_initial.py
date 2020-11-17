# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CoreModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        db_index=True,
                        db_column="domain_id",
                        serialize=False,
                    ),
                ),
                ("protein_id", models.CharField(max_length=15)),
                ("domain_idx", models.IntegerField(db_index=True)),
                ("clan", models.CharField(max_length=255, db_column="pfam_clan")),
                (
                    "name",
                    models.CharField(
                        max_length=255, db_index=True, db_column="pdbfam_name"
                    ),
                ),
                (
                    "alignment_def",
                    models.CharField(max_length=255, db_column="alignment_def"),
                ),
                ("data_path", models.TextField(blank=True, db_column="path_to_data")),
                (
                    "align_score",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_score"
                    ),
                ),
                (
                    "align_coverage",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_coverage"
                    ),
                ),
                (
                    "template_errors",
                    models.TextField(
                        blank=True, null=True, db_column="template_errors"
                    ),
                ),
                ("domain_def", models.CharField(blank=True, max_length=255)),
                (
                    "cath",
                    models.CharField(blank=True, max_length=255, db_column="cath_id"),
                ),
                (
                    "seq_id",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_identity"
                    ),
                ),
                (
                    "model_errors",
                    models.TextField(blank=True, null=True, db_column="model_errors"),
                ),
                (
                    "dope_score",
                    models.FloatField(blank=True, null=True, db_column="norm_dope"),
                ),
                ("model_filename", models.CharField(blank=True, max_length=255)),
                ("alignment_filename", models.CharField(blank=True, max_length=255)),
                ("chain", models.CharField(null=True, max_length=1)),
                ("model_domain_def", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["id"],
                "abstract": False,
                "db_table": "elaspic_core_model",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="CoreMutation",
            fields=[
                (
                    "protein_id",
                    models.CharField(primary_key=True, max_length=15, serialize=False),
                ),
                ("domain_idx", models.IntegerField(db_index=True)),
                ("mut", models.CharField(max_length=8, db_column="mutation")),
                ("mut_date_modified", models.DateField()),
                ("model_filename_wt", models.CharField(max_length=255)),
                ("model_filename_mut", models.CharField(max_length=255)),
                (
                    "mut_errors",
                    models.TextField(
                        blank=True, null=True, db_column="mutation_errors"
                    ),
                ),
                (
                    "pdb_chain",
                    models.CharField(
                        null=True, max_length=1, db_column="chain_modeller"
                    ),
                ),
                (
                    "pdb_mut",
                    models.CharField(
                        null=True, max_length=8, db_column="mutation_modeller"
                    ),
                ),
                ("stability_energy_wt", models.TextField(null=True)),
                ("stability_energy_mut", models.TextField(null=True)),
                ("physchem_wt", models.CharField(null=True, max_length=255)),
                ("physchem_wt_ownchain", models.CharField(null=True, max_length=255)),
                ("physchem_mut", models.CharField(null=True, max_length=255)),
                ("physchem_mut_ownchain", models.CharField(null=True, max_length=255)),
                ("secondary_structure_wt", models.CharField(null=True, max_length=1)),
                ("secondary_structure_mut", models.CharField(null=True, max_length=1)),
                ("solvent_accessibility_wt", models.FloatField(blank=True, null=True)),
                ("solvent_accessibility_mut", models.FloatField(blank=True, null=True)),
                ("matrix_score", models.FloatField(blank=True, null=True)),
                ("provean_score", models.FloatField(blank=True, null=True)),
                ("ddG", models.FloatField(blank=True, null=True, db_column="ddg")),
            ],
            options={
                "abstract": False,
                "db_table": "elaspic_core_mutation",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="DatabaseClinVar",
            fields=[
                (
                    "id",
                    models.PositiveIntegerField(
                        primary_key=True, db_column="id", serialize=False
                    ),
                ),
                ("protein_id", models.CharField(max_length=50, db_column="uniprot_id")),
                ("mut", models.CharField(max_length=8, db_column="mutation")),
                (
                    "variation",
                    models.CharField(max_length=50, db_column="variation_name"),
                ),
            ],
            options={
                "managed": False,
                "db_table": "clinvar_mutation",
            },
        ),
        migrations.CreateModel(
            name="DatabaseCOSMIC",
            fields=[
                (
                    "id",
                    models.PositiveIntegerField(
                        primary_key=True, db_column="id", serialize=False
                    ),
                ),
                ("protein_id", models.CharField(max_length=50, db_column="uniprot_id")),
                ("mut", models.CharField(max_length=8, db_column="mutation")),
                (
                    "variation",
                    models.CharField(max_length=50, db_column="variation_name"),
                ),
            ],
            options={
                "managed": False,
                "db_table": "cosmic_mutation",
            },
        ),
        migrations.CreateModel(
            name="DatabaseUniProt",
            fields=[
                (
                    "id",
                    models.PositiveIntegerField(
                        primary_key=True, db_column="id", serialize=False
                    ),
                ),
                ("protein_id", models.CharField(max_length=50, db_column="uniprot_id")),
                ("mut", models.CharField(max_length=8, db_column="mutation")),
                (
                    "variation",
                    models.CharField(max_length=50, db_column="variation_name"),
                ),
            ],
            options={
                "managed": False,
                "db_table": "uniprot_mutation",
            },
        ),
        migrations.CreateModel(
            name="HGNCIdentifier",
            fields=[
                (
                    "identifierID",
                    models.CharField(
                        primary_key=True,
                        max_length=255,
                        db_index=True,
                        db_column="identifier_id",
                        serialize=False,
                    ),
                ),
                (
                    "identifierType",
                    models.CharField(
                        max_length=20, db_index=True, db_column="identifier_type"
                    ),
                ),
                (
                    "uniprotID",
                    models.CharField(
                        max_length=10, db_index=True, db_column="uniprot_id"
                    ),
                ),
            ],
            options={
                "managed": False,
                "db_table": "hgnc_identifiers",
            },
        ),
        migrations.CreateModel(
            name="InterfaceModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        db_index=True,
                        db_column="interface_id",
                        serialize=False,
                    ),
                ),
                ("protein_id_1", models.CharField(max_length=15)),
                ("protein_id_2", models.CharField(max_length=15)),
                ("data_path", models.TextField(blank=True, db_column="path_to_data")),
                (
                    "align_score1",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_score_1"
                    ),
                ),
                (
                    "align_score2",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_score_2"
                    ),
                ),
                (
                    "align_coverage_1",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_coverage_1"
                    ),
                ),
                (
                    "align_coverage_2",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_coverage_2"
                    ),
                ),
                (
                    "cath1",
                    models.CharField(blank=True, max_length=255, db_column="cath_id_1"),
                ),
                (
                    "cath2",
                    models.CharField(blank=True, max_length=255, db_column="cath_id_2"),
                ),
                (
                    "seq_id1",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_identity_1"
                    ),
                ),
                (
                    "seq_id2",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_identity_2"
                    ),
                ),
                (
                    "errors",
                    models.TextField(
                        blank=True, null=True, db_column="template_errors"
                    ),
                ),
                ("model_domain_def_1", models.CharField(max_length=255)),
                ("model_domain_def_2", models.CharField(max_length=255)),
                ("model_errors", models.TextField(blank=True, null=True)),
                (
                    "dope_score",
                    models.FloatField(blank=True, null=True, db_column="norm_dope"),
                ),
                ("model_filename", models.CharField(blank=True, max_length=255)),
                ("alignment_filename_1", models.CharField(blank=True, max_length=255)),
                ("alignment_filename_2", models.CharField(blank=True, max_length=255)),
                ("aa1", models.TextField(blank=True, db_column="interacting_aa_1")),
                ("aa2", models.TextField(blank=True, db_column="interacting_aa_2")),
                ("chain_1", models.CharField(null=True, max_length=1)),
                ("chain_2", models.CharField(null=True, max_length=1)),
                (
                    "interface_area_hydrophobic",
                    models.FloatField(blank=True, null=True),
                ),
                (
                    "interface_area_hydrophilic",
                    models.FloatField(blank=True, null=True),
                ),
                ("interface_area_total", models.FloatField(blank=True, null=True)),
            ],
            options={
                "ordering": ["id"],
                "abstract": False,
                "db_table": "elaspic_interface_model",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="InterfaceMutation",
            fields=[
                (
                    "protein_id",
                    models.CharField(primary_key=True, max_length=15, serialize=False),
                ),
                ("mut", models.CharField(max_length=8, db_column="mutation")),
                ("chain_idx", models.IntegerField()),
                ("mut_date_modified", models.DateField()),
                ("model_filename_wt", models.CharField(max_length=255)),
                ("model_filename_mut", models.CharField(max_length=255)),
                (
                    "mut_errors",
                    models.TextField(
                        blank=True, null=True, db_column="mutation_errors"
                    ),
                ),
                (
                    "pdb_chain",
                    models.CharField(
                        null=True, max_length=1, db_column="chain_modeller"
                    ),
                ),
                (
                    "pdb_mut",
                    models.CharField(
                        null=True, max_length=8, db_column="mutation_modeller"
                    ),
                ),
                ("stability_energy_wt", models.TextField(null=True)),
                ("stability_energy_mut", models.TextField(null=True)),
                ("analyse_complex_energy_wt", models.TextField(null=True)),
                ("analyse_complex_energy_mut", models.TextField(null=True)),
                ("physchem_wt", models.CharField(null=True, max_length=255)),
                ("physchem_wt_ownchain", models.CharField(null=True, max_length=255)),
                ("physchem_mut", models.CharField(null=True, max_length=255)),
                ("physchem_mut_ownchain", models.CharField(null=True, max_length=255)),
                ("secondary_structure_wt", models.CharField(null=True, max_length=1)),
                ("secondary_structure_mut", models.CharField(null=True, max_length=1)),
                ("solvent_accessibility_wt", models.FloatField(blank=True, null=True)),
                ("solvent_accessibility_mut", models.FloatField(blank=True, null=True)),
                ("contact_distance_wt", models.FloatField(blank=True, null=True)),
                ("contact_distance_mut", models.FloatField(blank=True, null=True)),
                ("matrix_score", models.FloatField(blank=True, null=True)),
                ("provean_score", models.FloatField(blank=True, null=True)),
                ("ddG", models.FloatField(blank=True, null=True, db_column="ddg")),
            ],
            options={
                "abstract": False,
                "db_table": "elaspic_interface_mutation",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Protein",
            fields=[
                (
                    "id",
                    models.CharField(
                        primary_key=True,
                        max_length=50,
                        db_column="protein_id",
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=50, db_column="protein_name")),
                ("description", models.CharField(blank=True, max_length=255)),
                ("organism_name", models.CharField(blank=True, max_length=255)),
                ("seq", models.TextField(db_column="sequence")),
                ("provean_supset_file", models.TextField()),
                ("provean_supset_length", models.IntegerField()),
            ],
            options={
                "ordering": ["id"],
                "abstract": False,
                "db_table": "elaspic_sequence",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="UniprotIdentifier",
            fields=[
                (
                    "id",
                    models.AutoField(primary_key=True, db_index=True, serialize=False),
                ),
                (
                    "identifierID",
                    models.CharField(
                        max_length=255, db_index=True, db_column="identifier_id"
                    ),
                ),
                (
                    "identifierType",
                    models.CharField(
                        max_length=20, db_index=True, db_column="identifier_type"
                    ),
                ),
                (
                    "uniprotID",
                    models.CharField(
                        max_length=10, db_index=True, db_column="uniprot_id"
                    ),
                ),
            ],
            options={
                "managed": False,
                "db_table": "uniprot_identifier",
            },
        ),
        migrations.CreateModel(
            name="CoreModelLocal",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        db_index=True,
                        db_column="domain_id",
                        serialize=False,
                    ),
                ),
                ("protein_id", models.CharField(max_length=15)),
                ("domain_idx", models.IntegerField(db_index=True)),
                ("clan", models.CharField(max_length=255, db_column="pfam_clan")),
                (
                    "name",
                    models.CharField(
                        max_length=255, db_index=True, db_column="pdbfam_name"
                    ),
                ),
                (
                    "alignment_def",
                    models.CharField(max_length=255, db_column="alignment_def"),
                ),
                ("data_path", models.TextField(blank=True, db_column="path_to_data")),
                (
                    "align_score",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_score"
                    ),
                ),
                (
                    "align_coverage",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_coverage"
                    ),
                ),
                (
                    "template_errors",
                    models.TextField(
                        blank=True, null=True, db_column="template_errors"
                    ),
                ),
                ("domain_def", models.CharField(blank=True, max_length=255)),
                (
                    "cath",
                    models.CharField(blank=True, max_length=255, db_column="cath_id"),
                ),
                (
                    "seq_id",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_identity"
                    ),
                ),
                (
                    "model_errors",
                    models.TextField(blank=True, null=True, db_column="model_errors"),
                ),
                (
                    "dope_score",
                    models.FloatField(blank=True, null=True, db_column="norm_dope"),
                ),
                ("model_filename", models.CharField(blank=True, max_length=255)),
                ("alignment_filename", models.CharField(blank=True, max_length=255)),
                ("chain", models.CharField(null=True, max_length=1)),
                ("model_domain_def", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["id"],
                "abstract": False,
                "db_table": "elaspic_core_model_local",
            },
        ),
        migrations.CreateModel(
            name="CoreMutationLocal",
            fields=[
                (
                    "protein_id",
                    models.CharField(primary_key=True, max_length=15, serialize=False),
                ),
                ("domain_idx", models.IntegerField(db_index=True)),
                ("mut", models.CharField(max_length=8, db_column="mutation")),
                ("mut_date_modified", models.DateField()),
                ("model_filename_wt", models.CharField(max_length=255)),
                ("model_filename_mut", models.CharField(max_length=255)),
                (
                    "mut_errors",
                    models.TextField(
                        blank=True, null=True, db_column="mutation_errors"
                    ),
                ),
                (
                    "pdb_chain",
                    models.CharField(
                        null=True, max_length=1, db_column="chain_modeller"
                    ),
                ),
                (
                    "pdb_mut",
                    models.CharField(
                        null=True, max_length=8, db_column="mutation_modeller"
                    ),
                ),
                ("stability_energy_wt", models.TextField(null=True)),
                ("stability_energy_mut", models.TextField(null=True)),
                ("physchem_wt", models.CharField(null=True, max_length=255)),
                ("physchem_wt_ownchain", models.CharField(null=True, max_length=255)),
                ("physchem_mut", models.CharField(null=True, max_length=255)),
                ("physchem_mut_ownchain", models.CharField(null=True, max_length=255)),
                ("secondary_structure_wt", models.CharField(null=True, max_length=1)),
                ("secondary_structure_mut", models.CharField(null=True, max_length=1)),
                ("solvent_accessibility_wt", models.FloatField(blank=True, null=True)),
                ("solvent_accessibility_mut", models.FloatField(blank=True, null=True)),
                ("matrix_score", models.FloatField(blank=True, null=True)),
                ("provean_score", models.FloatField(blank=True, null=True)),
                ("ddG", models.FloatField(blank=True, null=True, db_column="ddg")),
                (
                    "model",
                    models.ForeignKey(
                        related_name="muts",
                        db_column="domain_id",
                        to="web_pipeline.CoreModelLocal",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "abstract": False,
                "db_table": "elaspic_core_mutation_local",
            },
        ),
        migrations.CreateModel(
            name="InterfaceModelLocal",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        db_index=True,
                        db_column="interface_id",
                        serialize=False,
                    ),
                ),
                ("protein_id_1", models.CharField(max_length=15)),
                ("protein_id_2", models.CharField(max_length=15)),
                ("data_path", models.TextField(blank=True, db_column="path_to_data")),
                (
                    "align_score1",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_score_1"
                    ),
                ),
                (
                    "align_score2",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_score_2"
                    ),
                ),
                (
                    "align_coverage_1",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_coverage_1"
                    ),
                ),
                (
                    "align_coverage_2",
                    models.IntegerField(
                        blank=True, null=True, db_column="alignment_coverage_2"
                    ),
                ),
                (
                    "cath1",
                    models.CharField(blank=True, max_length=255, db_column="cath_id_1"),
                ),
                (
                    "cath2",
                    models.CharField(blank=True, max_length=255, db_column="cath_id_2"),
                ),
                (
                    "seq_id1",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_identity_1"
                    ),
                ),
                (
                    "seq_id2",
                    models.FloatField(
                        blank=True, null=True, db_column="alignment_identity_2"
                    ),
                ),
                (
                    "errors",
                    models.TextField(
                        blank=True, null=True, db_column="template_errors"
                    ),
                ),
                ("model_domain_def_1", models.CharField(max_length=255)),
                ("model_domain_def_2", models.CharField(max_length=255)),
                ("model_errors", models.TextField(blank=True, null=True)),
                (
                    "dope_score",
                    models.FloatField(blank=True, null=True, db_column="norm_dope"),
                ),
                ("model_filename", models.CharField(blank=True, max_length=255)),
                ("alignment_filename_1", models.CharField(blank=True, max_length=255)),
                ("alignment_filename_2", models.CharField(blank=True, max_length=255)),
                ("aa1", models.TextField(blank=True, db_column="interacting_aa_1")),
                ("aa2", models.TextField(blank=True, db_column="interacting_aa_2")),
                ("chain_1", models.CharField(null=True, max_length=1)),
                ("chain_2", models.CharField(null=True, max_length=1)),
                (
                    "interface_area_hydrophobic",
                    models.FloatField(blank=True, null=True),
                ),
                (
                    "interface_area_hydrophilic",
                    models.FloatField(blank=True, null=True),
                ),
                ("interface_area_total", models.FloatField(blank=True, null=True)),
                (
                    "domain1",
                    models.ForeignKey(
                        related_name="p1",
                        db_column="domain_id_1",
                        to="web_pipeline.CoreModelLocal",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "domain2",
                    models.ForeignKey(
                        related_name="p2",
                        db_column="domain_id_2",
                        to="web_pipeline.CoreModelLocal",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
                "abstract": False,
                "db_table": "elaspic_interface_model_local",
            },
        ),
        migrations.CreateModel(
            name="InterfaceMutationLocal",
            fields=[
                (
                    "protein_id",
                    models.CharField(primary_key=True, max_length=15, serialize=False),
                ),
                ("mut", models.CharField(max_length=8, db_column="mutation")),
                ("chain_idx", models.IntegerField()),
                ("mut_date_modified", models.DateField()),
                ("model_filename_wt", models.CharField(max_length=255)),
                ("model_filename_mut", models.CharField(max_length=255)),
                (
                    "mut_errors",
                    models.TextField(
                        blank=True, null=True, db_column="mutation_errors"
                    ),
                ),
                (
                    "pdb_chain",
                    models.CharField(
                        null=True, max_length=1, db_column="chain_modeller"
                    ),
                ),
                (
                    "pdb_mut",
                    models.CharField(
                        null=True, max_length=8, db_column="mutation_modeller"
                    ),
                ),
                ("stability_energy_wt", models.TextField(null=True)),
                ("stability_energy_mut", models.TextField(null=True)),
                ("analyse_complex_energy_wt", models.TextField(null=True)),
                ("analyse_complex_energy_mut", models.TextField(null=True)),
                ("physchem_wt", models.CharField(null=True, max_length=255)),
                ("physchem_wt_ownchain", models.CharField(null=True, max_length=255)),
                ("physchem_mut", models.CharField(null=True, max_length=255)),
                ("physchem_mut_ownchain", models.CharField(null=True, max_length=255)),
                ("secondary_structure_wt", models.CharField(null=True, max_length=1)),
                ("secondary_structure_mut", models.CharField(null=True, max_length=1)),
                ("solvent_accessibility_wt", models.FloatField(blank=True, null=True)),
                ("solvent_accessibility_mut", models.FloatField(blank=True, null=True)),
                ("contact_distance_wt", models.FloatField(blank=True, null=True)),
                ("contact_distance_mut", models.FloatField(blank=True, null=True)),
                ("matrix_score", models.FloatField(blank=True, null=True)),
                ("provean_score", models.FloatField(blank=True, null=True)),
                ("ddG", models.FloatField(blank=True, null=True, db_column="ddg")),
                (
                    "model",
                    models.ForeignKey(
                        related_name="muts",
                        db_column="interface_id",
                        to="web_pipeline.InterfaceModelLocal",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "abstract": False,
                "db_table": "elaspic_interface_mutation_local",
            },
        ),
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "jobID",
                    models.CharField(primary_key=True, max_length=10, serialize=False),
                ),
                ("dateRun", models.DateTimeField(auto_now_add=True)),
                ("dateFinished", models.DateTimeField(blank=True, null=True)),
                ("dateVisited", models.DateTimeField(auto_now_add=True)),
                ("isDone", models.BooleanField(default=False)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("localID", models.CharField(blank=True, null=True, max_length=50)),
                ("browser", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["jobID"],
                "get_latest_by": "dateRun",
                "db_table": "jobs",
            },
        ),
        migrations.CreateModel(
            name="JobToMut",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                        auto_created=True,
                    ),
                ),
                ("inputIdentifier", models.CharField(max_length=70)),
                (
                    "job",
                    models.ForeignKey(to="web_pipeline.Job", on_delete=models.CASCADE),
                ),
            ],
            options={
                "db_table": "job_to_mut",
            },
        ),
        migrations.CreateModel(
            name="Mut",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                        auto_created=True,
                    ),
                ),
                ("protein", models.CharField(max_length=50, db_index=True)),
                ("mut", models.CharField(max_length=8)),
                ("chain", models.SmallIntegerField(blank=True, null=True)),
                (
                    "affectedType",
                    models.CharField(
                        blank=True,
                        max_length=2,
                        choices=[("NO", "None"), ("CO", "Core"), ("IN", "Interaction")],
                    ),
                ),
                ("dateAdded", models.DateTimeField(auto_now_add=True)),
                ("dateFinished", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(max_length=12, default="queued")),
                ("rerun", models.SmallIntegerField(default=0)),
                ("taskId", models.CharField(blank=True, max_length=50)),
                ("error", models.TextField(blank=True, null=True)),
            ],
            options={
                "db_table": "muts",
            },
        ),
        migrations.CreateModel(
            name="ProteinLocal",
            fields=[
                (
                    "id",
                    models.CharField(
                        primary_key=True,
                        max_length=50,
                        db_column="protein_id",
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=50, db_column="protein_name")),
                ("description", models.CharField(blank=True, max_length=255)),
                ("organism_name", models.CharField(blank=True, max_length=255)),
                ("seq", models.TextField(db_column="sequence")),
                ("provean_supset_file", models.TextField()),
                ("provean_supset_length", models.IntegerField()),
            ],
            options={
                "ordering": ["id"],
                "abstract": False,
                "db_table": "elaspic_sequence_local",
            },
        ),
        migrations.AddField(
            model_name="jobtomut",
            name="mut",
            field=models.ForeignKey(to="web_pipeline.Mut", on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name="job",
            name="muts",
            field=models.ManyToManyField(
                related_name="jobs",
                through="web_pipeline.JobToMut",
                to="web_pipeline.Mut",
            ),
        ),
        migrations.AddField(
            model_name="coremodellocal",
            name="interactions",
            field=models.ManyToManyField(
                blank=True,
                through="web_pipeline.InterfaceModelLocal",
                to="web_pipeline.CoreModelLocal",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="coremutationlocal",
            unique_together=set([("protein_id", "model", "mut")]),
        ),
        migrations.AlterUniqueTogether(
            name="coremodellocal",
            unique_together=set([("protein_id", "domain_idx")]),
        ),
    ]
