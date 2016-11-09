DELIMITER $$
CREATE PROCEDURE `UPDATE_muts`(
  protein_id varchar(255),
  mutation varchar(255))
begin

  START TRANSACTION ;

    CREATE TEMPORARY TABLE bad_ids AS (
        SELECT id
        FROM muts
        LEFT JOIN elaspic_core_mutation db_mut ON (
            muts.protein = db_mut.protein_id and muts.mut = db_mut.mutation)
        LEFT JOIN elaspic_core_mutation_local local_mut ON (
            muts.protein = local_mut.protein_id and muts.mut = local_mut.mutation)
        WHERE muts.protein = protein_id and muts.mut = mutation AND
              db_mut.ddg IS NULL AND local_mut.ddg IS NULL
    );

    CREATE TEMPORARY TABLE good_ids_core AS (
        SELECT id
        FROM muts
        JOIN elaspic_core_mutation db_mut ON (
            muts.protein = db_mut.protein_id and muts.mut = db_mut.mutation)
        WHERE muts.protein = protein_id and muts.mut = mutation AND db_mut.ddg IS NOT NULL
        UNION
        SELECT id
        FROM muts
        JOIN elaspic_core_mutation_local local_mut ON (
            muts.protein = local_mut.protein_id and muts.mut = local_mut.mutation)
        WHERE muts.protein = protein_id and muts.mut = mutation AND local_mut.ddg IS NOT NULL
    );

    CREATE TEMPORARY TABLE good_ids_interface AS (
        SELECT id
        FROM muts
        JOIN elaspic_interface_mutation db_mut ON (
            muts.protein = db_mut.protein_id and muts.mut = db_mut.mutation)
        WHERE muts.protein = protein_id and muts.mut = mutation AND db_mut.ddg IS NOT NULL
        UNION
        SELECT id
        FROM muts
        JOIN elaspic_interface_mutation_local local_mut ON (
            muts.protein = local_mut.protein_id and muts.mut = local_mut.mutation)
        WHERE muts.protein = protein_id and muts.mut = mutation AND local_mut.ddg IS NOT NULL
    );

	UPDATE muts
    SET muts.affectedType='CO', muts.status='error', muts.dateFinished = now(),
        muts.error='1: ddG not calculated'
    WHERE muts.id IN (SELECT distinct id FROM bad_ids order by id);

	UPDATE muts
    SET muts.affectedType='CO', muts.status='done', muts.dateFinished = now(),
        muts.error=Null
	WHERE muts.id IN (SELECT distinct id FROM good_ids_core order by id);

	UPDATE muts web_mut
    SET web_mut.affectedType='IN', web_mut.status='done', web_mut.dateFinished = now(),
        web_mut.error=Null
	JOIN elaspic_interface_mutation db_mut on (
        web_mut.protein = db_mut.protein_id and web_mut.mut = db_mut.mutation)
    WHERE muts.id IN (SELECT distinct id FROM good_ids_interface order by id);

  COMMIT ;

end$$
DELIMITER ;
