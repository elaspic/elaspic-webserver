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

cd "/home/kimlab1/database_data/elaspic_v2/user_input/${protein_id}"
mkdir -p "./pbs-output"
exec >"./pbs-output/${JOB_ID}.out" 2>"./pbs-output/${JOB_ID}.err"

echo `hostname`
# source activate elaspic
export PATH="/home/kimlab1/jobsubmitter/anaconda3/envs/elaspic/bin:$PATH"
elaspic run \
    --pdb_dir='/home/kimlab1/database_data/pdb/data/data/structures/all/pdb/' \
    --blast_db_dir='/home/kimlab1/database_data/blast/db' \
    --archive_dir='/home/kimlab1/database_data/elaspic_v2/' \
    -p "${structure_file}" -s "${sequence_file}" -m "${mutations}" -n 3 -t ${elaspic_run_type}

python "${SCRIPTS_DIR}/local.py" -u "${protein_id}" -m "${mutations}" -t ${run_type}

echo "Finished successfully!"

exit 0
