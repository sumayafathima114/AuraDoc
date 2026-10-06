-- Append-only human conclusions snapshot the reviewed finding context and
-- remain separate from all AI-generated assessments and recommendations.
create table public.case_conclusions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  finding_id uuid not null references public.findings(id) on delete cascade,
  reviewer_user_id uuid not null default auth.uid() references auth.users(id),
  lawyer_recommendation text not null default '' check (length(lawyer_recommendation) <= 10000),
  human_conclusion text not null check (length(trim(human_conclusion)) between 20 and 20000),
  limitations text not null default '' check (length(limitations) <= 10000),
  finding_snapshot jsonb not null,
  evidence_snapshot jsonb not null,
  verified_sources_snapshot jsonb not null,
  recommendations_snapshot jsonb not null,
  created_at timestamptz not null default now()
);

create index case_conclusions_case_created_idx on public.case_conclusions(case_id, created_at desc);
create index case_conclusions_finding_created_idx on public.case_conclusions(finding_id, created_at desc);

alter table public.case_conclusions enable row level security;
grant select on public.case_conclusions to authenticated;
revoke insert, update, delete on public.case_conclusions from anon, authenticated;
create policy case_conclusions_member_select on public.case_conclusions
  for select to authenticated using (private.can_access_case(case_id));

create or replace function public.register_human_conclusion(
  p_case_id uuid,
  p_finding_id uuid,
  p_lawyer_recommendation text,
  p_human_conclusion text,
  p_limitations text
)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare
  conclusion_id uuid;
  finding_data jsonb;
  evidence_data jsonb;
  verified_sources_data jsonb;
  recommendations_data jsonb;
begin
  if auth.uid() is null or not private.has_case_role(p_case_id, array['OWNER','REVIEWER']::text[]) then
    raise insufficient_privilege using message = 'Case review access denied';
  end if;
  select to_jsonb(f) into finding_data
    from public.findings f where f.id = p_finding_id and f.case_id = p_case_id;
  if finding_data is null then
    raise check_violation using message = 'Finding is unavailable for this case';
  end if;
  if length(trim(coalesce(p_human_conclusion, ''))) < 20 then
    raise check_violation using message = 'Human conclusion must contain at least 20 characters';
  end if;

  select coalesce(jsonb_agg(to_jsonb(fe) order by fe.id), '[]'::jsonb)
    into evidence_data from public.finding_evidence fe where fe.finding_id = p_finding_id;
  select coalesce(jsonb_agg(to_jsonb(s) order by s.id), '[]'::jsonb)
    into verified_sources_data
    from public.legal_analyses la
    join public.legal_analysis_sources las on las.legal_analysis_id = la.id
    join public.legal_sources s on s.id = las.legal_source_id
    where la.finding_id = p_finding_id and la.case_id = p_case_id
      and s.case_id = p_case_id and s.verification_status = 'VERIFIED_OFFICIAL';
  select coalesce(jsonb_agg(to_jsonb(r) order by r.created_at, r.id), '[]'::jsonb)
    into recommendations_data
    from public.investigation_recommendations r
    where r.finding_id = p_finding_id and r.case_id = p_case_id;

  insert into public.case_conclusions (
    case_id, finding_id, reviewer_user_id, lawyer_recommendation, human_conclusion,
    limitations, finding_snapshot, evidence_snapshot, verified_sources_snapshot,
    recommendations_snapshot
  ) values (
    p_case_id, p_finding_id, auth.uid(), coalesce(p_lawyer_recommendation, ''),
    trim(p_human_conclusion), coalesce(p_limitations, ''), finding_data,
    evidence_data, verified_sources_data, recommendations_data
  ) returning id into conclusion_id;

  insert into public.audit_events(case_id, actor_user_id, action, entity_type, entity_id, metadata)
  values (p_case_id, auth.uid(), 'HUMAN_CONCLUSION_CREATED', 'case_conclusion', conclusion_id,
          jsonb_build_object('finding_id', p_finding_id));

  return jsonb_build_object('conclusion_id', conclusion_id, 'finding_id', p_finding_id);
end;
$$;

revoke all on function public.register_human_conclusion(uuid, uuid, text, text, text) from public, anon;
grant execute on function public.register_human_conclusion(uuid, uuid, text, text, text) to authenticated;
