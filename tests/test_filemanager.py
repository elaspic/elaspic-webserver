import io

import pandas as pd
import pytest
# from hypothesis import given
# from hypothesis.strategies import text
from faker import Faker

from web_pipeline import filemanager

fake = Faker()


@pytest.fixture(
    scope="module",
    params=[
        ('11f467', [
            'CBL_HUMAN.P417L', 'CBL_HUMAN.P417L_8564833', 'CBL_HUMAN.P417L_8566535',
            'CBL_HUMAN.P417L_8566566', 'CBL_HUMAN.P417L_8566571', 'CBL_HUMAN.P417L_8566813',
            'CBL_HUMAN.P417L_9069942', 'CBL_HUMAN.P417L_9069947', 'CBL_HUMAN.P417L_9069952',
            'CBL_HUMAN.P417L_9069957', 'CBL_HUMAN.P417L_9069962', 'CBL_HUMAN.P417L_12296264',
            'CBL_HUMAN.P417L_12297401', 'CBL_HUMAN.P417L_17363959'])])
def fm(request):
    job_id, muts = request.param
    return filemanager.FileManager(job_id, muts)


@pytest.mark.parametrize("filename", filemanager.FileManager._valid_filenames)
def test_make_file(fm, filename):
    fm.makeFile(filename)


@pytest.mark.parametrize("filename", ['simpleresults.txt', 'allresults.txt'])
def test_csv(fm, filename):
    data = fm.makeFile(filename)
    df = pd.read_csv(io.BytesIO(data), encoding='utf8', sep='\t', na_values=['-'])

    # Correct shape
    assert df.shape[1] in [10, 100]

    # Make sure few nulls
    POTENTIAL_NULL_COLUMNS = ['ClinVar_mut_ID', 'UniProt_mut_ID']
    null_columns = df.columns[df.isnull().all()]
    if df.shape[0] == 1:
        assert not (
            {c for c in null_columns if 'interface' not in c.lower()} -
            set(POTENTIAL_NULL_COLUMNS)
        )
    else:
        assert not set(null_columns) - set(POTENTIAL_NULL_COLUMNS)


# def test_save_zip_file():
#     dtemp = tempfile.mkdtemp()
#     zfh = io.BytesIO()
#     # Generate some random files
#     files = []
#     for i in range(10):
#         file = op.join(dtemp, 'tempfile_{}.txt'.format(i))
#         with open(file, 'w') as ofh:
#             ofh.write(fake.text())
#         files.append(file)
#     filename = op.join(dtemp, 'output.zip')
#     filemanager.save_zip_file(zfh, files, filename)
#     assert op.isfile(filename)
