-- Document-only review is distinct from a statement comparison. Findings may
-- have document provenance without inventing a recording or transcript.
alter table public.findings
  alter column recording_id drop not null,
  alter column transcript_segment_id drop not null;

alter table public.findings
  add column if not exists analysis_mode text not null default 'STATEMENT_COMPARISON';

alter table public.findings
  drop constraint if exists findings_analysis_mode_check;
alter table public.findings
  add constraint findings_analysis_mode_check
    check (analysis_mode in ('STATEMENT_COMPARISON', 'DOCUMENT_REVIEW'));

create or replace function public.register_document_finding(
  p_case_id uuid,
  p_document_version_id uuid,
  p_summary text,
  p_explanation text,
  p_uncertainties jsonb,
  p_provider text,
  p_model_name text,
  p_prompt_version text,
  p_evidence jsonb
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare new_finding_id uuid; item jsonb; evidence_count integer := 0;
begin
  if auth.uid() is null or not private.has_case_role(p_case_id, array['OWNER','INVESTIGATOR']::text[]) then
    raise insufficient_privilege using message = 'Case access denied';
  end if;
  if private.version_case_id(p_document_version_id) is distinct from p_case_id then
    raise check_violation using message = 'Document does not belong to the requested case';
  end if;
  if jsonb_typeof(p_evidence) <> 'array' or jsonb_array_length(p_evidence) = 0 then
    raise check_violation using message = 'Document review requires source evidence';
  end if;
  insert into public.findings (
    case_id, recording_id, transcript_segment_id, document_version_id,
    relation_type, analysis_mode, summary, explanation, uncertainties,
    provider, model_name, prompt_version
  ) values (
    p_case_id, null, null, p_document_version_id,
    'NEEDS_HUMAN_REVIEW', 'DOCUMENT_REVIEW', p_summary, p_explanation,
    coalesce(p_uncertainties, '[]'::jsonb), p_provider, p_model_name, p_prompt_version
  ) returning id into new_finding_id;

  for item in select value from jsonb_array_elements(p_evidence) loop
    if nullif(item->>'document_section_id', '') is null
       or nullif(item->>'transcript_segment_id', '') is not null
       or not exists (
         select 1 from public.document_sections ds
         where ds.id = (item->>'document_section_id')::uuid
           and ds.document_version_id = p_document_version_id
           and ds.content_hash = item->>'source_hash'
           and ds.content = item->>'quoted_text'
       ) then
      raise check_violation using message = 'Document evidence does not match the source';
    end if;
    insert into public.finding_evidence (
      finding_id, document_section_id, transcript_segment_id, quoted_text,
      page_number, section_label, clause_label, source_hash
    ) values (
      new_finding_id, (item->>'document_section_id')::uuid, null,
      item->>'quoted_text', (item->>'page_number')::integer,
      nullif(item->>'section_label', ''), nullif(item->>'clause_label', ''),
      item->>'source_hash'
    );
    evidence_count := evidence_count + 1;
  end loop;
  return jsonb_build_object('finding_id', new_finding_id, 'evidence_count', evidence_count);
end;
$$;

revoke all on function public.register_document_finding(uuid, uuid, text, text, jsonb, text, text, text, jsonb) from public, anon;
grant execute on function public.register_document_finding(uuid, uuid, text, text, jsonb, text, text, text, jsonb) to authenticated;

-- The legal-analysis registration RPC is the only permitted write path. It
-- executes with its owner privileges but validates the caller, case, finding,
-- verified source set, status, and recommendation/source relationships itself.
revoke insert on public.legal_analyses, public.legal_analysis_sources from authenticated;

create or replace function public.register_legal_analysis(
  p_case_id uuid,
  p_finding_id uuid,
  p_status text,
  p_legal_relevance jsonb,
  p_missing_evidence jsonb,
  p_provider text,
  p_model_name text,
  p_prompt_version text,
  p_source_ids uuid[],
  p_recommendations jsonb
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare analysis_id uuid; recommendation_ids uuid[] := '{}'; item jsonb; source_id uuid; recommendation_id uuid;
begin
  if auth.uid() is null or not private.has_case_role(p_case_id, array['OWNER','INVESTIGATOR']::text[]) then
    raise insufficient_privilege using message = 'Case access denied';
  end if;
  if not exists (select 1 from public.findings f where f.id = p_finding_id and f.case_id = p_case_id) then
    raise exception 'Finding is unavailable';
  end if;
  if p_status is null
     or (cardinality(coalesce(p_source_ids, '{}'::uuid[])) = 0 and p_status <> 'NO_VERIFIED_LEGAL_SOURCE_FOUND')
     or (cardinality(coalesce(p_source_ids, '{}'::uuid[])) > 0 and p_status <> 'COMPLETED')
     or p_status not in ('COMPLETED','NO_VERIFIED_LEGAL_SOURCE_FOUND') then
    raise check_violation using message = 'Legal analysis status does not match its verified source set';
  end if;
  if exists (select 1 from unnest(coalesce(p_source_ids, '{}'::uuid[])) as x(sid)
    where not exists (select 1 from public.legal_sources s where s.id = x.sid and s.case_id = p_case_id and s.verification_status = 'VERIFIED_OFFICIAL')) then
    raise exception 'A legal source is unavailable or not verified';
  end if;
  if exists (
    select 1 from jsonb_array_elements(coalesce(p_legal_relevance, '[]'::jsonb)) as x(item)
    where not ((x.item->>'legal_source_id')::uuid = any(coalesce(p_source_ids, '{}'::uuid[])))
  ) then raise exception 'Legal relevance references a source outside the verified set'; end if;

  insert into public.legal_analyses(case_id, finding_id, status, legal_relevance, missing_evidence, provider, model_name, prompt_version, created_by)
  values(p_case_id, p_finding_id, p_status, coalesce(p_legal_relevance, '[]'::jsonb), coalesce(p_missing_evidence, '[]'::jsonb), p_provider, p_model_name, p_prompt_version, auth.uid())
  returning id into analysis_id;
  foreach source_id in array coalesce(p_source_ids, '{}'::uuid[]) loop
    insert into public.legal_analysis_sources(legal_analysis_id, legal_source_id) values(analysis_id, source_id);
  end loop;
  for item in select value from jsonb_array_elements(coalesce(p_recommendations, '[]'::jsonb)) loop
    if item->>'legal_source_id' is not null and not exists (
      select 1 from public.legal_sources s where s.id = (item->>'legal_source_id')::uuid and s.case_id = p_case_id and s.verification_status = 'VERIFIED_OFFICIAL'
    ) then raise exception 'Recommendation source is unavailable or not verified'; end if;
    insert into public.investigation_recommendations(case_id, finding_id, legal_analysis_id, legal_source_id, action, reason, evidence_basis, priority, created_by)
    values(p_case_id, p_finding_id, analysis_id, nullif(item->>'legal_source_id','')::uuid,
      item->>'action', item->>'reason', item->>'evidence_basis', item->>'priority', auth.uid())
    returning id into recommendation_id;
    recommendation_ids := array_append(recommendation_ids, recommendation_id);
  end loop;
  return jsonb_build_object('legal_analysis_id', analysis_id, 'recommendation_ids', to_jsonb(recommendation_ids));
end;
$$;

revoke all on function public.register_legal_analysis(uuid, uuid, text, jsonb, jsonb, text, text, text, uuid[], jsonb) from public, anon;
grant execute on function public.register_legal_analysis(uuid, uuid, text, jsonb, jsonb, text, text, text, uuid[], jsonb) to authenticated;
