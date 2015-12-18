#!/bin/bash
# Submission script for the ELASPIC pipeline
# Requires `input_file` to be passed in as a variable
# 
#$ -S /bin/bash
#$ -N elaspic
# #$ -pe smp 1
# #$ -l s_rt=23:30:00
# #$ -l h_rt=24:00:00
# #$ -l s_vmem=5650M
# #$ -l h_vmem=5850M
# #$ -l mem_free=5850M
# #$ -l virtual_free=5850M
#
#$ -cwd
#$ -o /dev/null
#$ -e /dev/null
#$ -M ostrokach@gmail.com
#$ -V
#$ -p 0

set -ex

function finish {
  echo "Moving lock file to the finished folder..."
  mv -f "${lock_filename}" "${lock_filename_finished}"
}
trap finish INT TERM EXIT

cd "/home/kimlab1/database_data/elaspic_v2"
mkdir -p "./pbs-output"
exec >"./pbs-output/${JOB_ID}.out" 2>"./pbs-output/${JOB_ID}.err"

echo `hostname`
source activate elaspic_2
elaspic -c "./config_file_mysql.ini" \
  -u "${uniprot_id}" -m "${mutations}" -i "${uniprot_domain_pair_ids}" -t ${elaspic_run_type}

python "${SCRIPTS_DIR}/database.py" -u "${uniprot_id}" -m "${mutations}" -t ${run_type}

echo "Finished successfully!"

exit 0
 
