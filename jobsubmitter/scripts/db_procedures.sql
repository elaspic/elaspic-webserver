delimiter //

create procedure update_muts(
  protein_id varchar(255), 
  mutation varchar(255)
  out all_ok boolean)
begin
  start transaction
    set all_ok = true;
    
    update table elaspic_webserver.muts
    set affectedType="CO" and status='error'
    where protein = protein_id and mut = protein_id and 
    (protein, mut) in (
      select uniprot_id protein, mutation mut
      from elaspic.uniprot_domain_mutation m
      where ddg is null and mutation_errors is not null
    );
    
    update table elaspic_webserver.muts
    set affectedType="CO" and status='done'
    where protein = protein_id and mut = protein_id and 
    (protein, mut) in (
      select uniprot_id protein, mutation mut
      from elaspic.uniprot_domain_mutation m
      where ddg is not null
    );
    
    update table elaspic_webserver.muts
    set affectedType="IN" and status='done'
    where protein = protein_id and mut = protein_id and 
    (protein, mut) in (
      select uniprot_id protein, mutation mut
      from elaspic.uniprot_domain_pair_mutation m
      where ddg is not null
    );
    
    set all_ok = true;
  commit;
end//
