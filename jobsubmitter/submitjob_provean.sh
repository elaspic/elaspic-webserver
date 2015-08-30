#!/bin/bash
# Submission script for the ELASPIC pipeline
# Requires `input_file` to be passed in as a variable
# 
#$ -S /bin/bash
#$ -N elaspic
#$ -pe smp 1
#$ -l s_rt=23:30:00
#$ -l h_rt=24:00:00
#$ -l h_vmem=5850M
#$ -l mem_free=5850M
#$ -l virtual_free=5850M
#
#$ -cwd
#$ -o /dev/null
#$ -e /dev/null
#$ -M ostrokach@gmail.com
#$ -V
#$ -p 0

cd "/home/kimlab1/strokach/jobsubmitter/elaspic"

exec >./pbs-output/$JOB_ID.out 2>./pbs-output/$JOB_ID.err

source activate elaspic

elaspic -c "config_file_mysql.ini" -u "${uniprot_id}" -m "${mutations}" -t 1
