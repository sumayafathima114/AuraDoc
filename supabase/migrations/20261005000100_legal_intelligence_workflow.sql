-- AuraDoc legal-source provenance and finding-to-review workflow.
-- Additive and rerunnable; existing evidence, findings, and audit tables are reused.

create table if not exists public.legal_sources (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null default auth.uid() references auth.users(id),
  title text not null check (length(trim(title)) between 1 and 500),
  source_type text not null check (source_type in ('ACT','SECTION','RULE','REGULATION','NOTIFICATION','ORDER','JUDGMENT','OTHER')),
  jurisdiction text not null default 'INDIA',
  authority text not null check (length(trim(authority)) between 1 and 300),
  act_or_regulation text,
  section text,
  subsection text,
  publication_date date,
  effective_date date,
  version_label text,
  official_source_url text not null,
  retrieved_at timestamptz not null default now(),
  verification_status text not null default 'PENDING_VERIFICATION' check (verification_status in ('PENDING_VERIFICATION','VERIFIED_OFFICIAL','REJECTED','OUTDATED')),
  source_text text not null check (length(trim(source_text)) between 1 and 100000),
  source_sha256 text not null check (source_sha256 ~ '^[a-f0-9]{64}$'),
  verified_by uuid references auth.users(id),
  verified_at timestamptz,
  verification_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((verification_status = 'VERIFIED_OFFICIAL') = (verified_by is not null and verified_at is not null))
);
create index if not exists legal_sources_case_status_idx on public.legal_sources(case_id, verification_status, created_at desc);
create index if not exists legal_sources_source_sha_idx on public.legal_sources(source_sha256);

create table if not exists public.legal_analyses (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  finding_id uuid not null references public.findings(id) on delete cascade,
  status text not null check (status in ('COMPLETED','NO_VERIFIED_LEGAL_SOURCE_FOUND')),
  legal_relevance jsonb not null default '[]'::jsonb,
  missing_evidence jsonb not null default '[]'::jsonb,
  provider text,
  model_name text,
  prompt_version text not null,
  requires_human_review boolean not null default true check (requires_human_review),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now()
);
create index if not exists legal_analyses_case_created_idx on public.legal_analyses(case_id, created_at desc);
create index if not exists legal_analyses_finding_created_idx on public.legal_analyses(finding_id, created_at desc);

create table if not exists public.legal_analysis_sources (
  legal_analysis_id uuid not null references public.legal_analyses(id) on delete cascade,
  legal_source_id uuid not null references public.legal_sources(id) on delete restrict,
  primary key(legal_analysis_id, legal_source_id)
);

create table if not exists public.investigation_recommendations (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  finding_id uuid not null references public.findings(id) on delete cascade,
  legal_analysis_id uuid not null references public.legal_analyses(id) on delete cascade,
  legal_source_id uuid references public.legal_sources(id) on delete restrict,
  action text not null check (length(trim(action)) between 1 and 1000),
  reason text not null check (length(trim(reason)) between 1 and 2000),
  evidence_basis text not null check (length(trim(evidence_basis)) between 1 and 2000),
  priority text not null check (priority in ('LOW','MEDIUM','HIGH')),
  status text not null default 'OPEN' check (status in ('OPEN','COMPLETED','DISMISSED')),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists recommendations_case_status_idx on public.investigation_recommendations(case_id, status, created_at desc);
create index if not exists recommendations_finding_idx on public.investigation_recommendations(finding_id, created_at desc);

alter table public.review_actions add column if not exists previous_status text;
alter table public.review_actions add column if not exists new_status text;
alter table public.review_actions add column if not exists reviewer_notes text;
alter table public.review_actions drop constraint if exists review_actions_decision_check;
alter table public.review_actions add constraint review_actions_decision_check check (decision in ('VERIFIED','REJECTED','NEEDS_MORE_REVIEW','REQUEST_MORE_EVIDENCE','MARK_RESOLVED','ESCALATE'));
alter table public.findings drop constraint if exists findings_status_check;
alter table public.findings add constraint findings_status_check check (status in ('NEEDS_REVIEW','VERIFIED','REJECTED','NEEDS_MORE_REVIEW','RESOLVED','ESCALATED'));

alter table public.legal_sources enable row level security;
alter table public.legal_analyses enable row level security;
alter table public.legal_analysis_sources enable row level security;
alter table public.investigation_recommendations enable row level security;
revoke all on public.legal_sources, public.legal_analyses, public.legal_analysis_sources, public.investigation_recommendations from anon;
grant select, insert on public.legal_sources to authenticated;
grant update (verification_status, verified_by, verified_at, verification_notes, updated_at) on public.legal_sources to authenticated;
grant select, insert on public.legal_analyses, public.legal_analysis_sources to authenticated;
grant select, insert on public.investigation_recommendations to authenticated;
grant update (status, updated_at) on public.investigation_recommendations to authenticated;

drop policy if exists legal_sources_member_select on public.legal_sources;
create policy legal_sources_member_select on public.legal_sources for select to authenticated using (private.can_access_case(case_id));
drop policy if exists legal_sources_writer_insert on public.legal_sources;
create policy legal_sources_writer_insert on public.legal_sources for insert to authenticated with check (created_by = auth.uid() and private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[]));
drop policy if exists legal_sources_reviewer_update on public.legal_sources;
create policy legal_sources_reviewer_update on public.legal_sources for update to authenticated using (private.has_case_role(case_id, array['OWNER','REVIEWER']::text[])) with check (private.has_case_role(case_id, array['OWNER','REVIEWER']::text[]));
alter table public.legal_sources drop constraint if exists legal_sources_official_url_check;
alter table public.legal_sources add constraint legal_sources_official_url_check check (
  official_source_url ~ '^https://([A-Za-z0-9-]+[.])*indiacode[.]nic[.]in(:443)?(/|$)'
  or official_source_url ~ '^https://([A-Za-z0-9-]+[.])*sci[.]gov[.]in(:443)?(/|$)'
);

create or replace function public.guard_legal_source_insert()
returns trigger language plpgsql security invoker set search_path = ''
as $$
begin
  if new.verification_status <> 'PENDING_VERIFICATION' or new.verified_by is not null or new.verified_at is not null then
    raise exception 'A legal source must begin pending human verification';
  end if;
  if new.created_by is distinct from auth.uid() then
    raise exception 'Legal source creator must match the authenticated user';
  end if;
  if encode(extensions.digest(convert_to(new.source_text, 'UTF8'), 'sha256'), 'hex') <> new.source_sha256 then
    raise exception 'Legal source checksum does not match its source text';
  end if;
  return new;
end;
$$;
drop trigger if exists legal_sources_guard_insert on public.legal_sources;
create trigger legal_sources_guard_insert before insert on public.legal_sources for each row execute function public.guard_legal_source_insert();

create or replace function public.guard_legal_source_integrity()
returns trigger language plpgsql security invoker set search_path = ''
as $$
begin
  if old.verification_status <> 'PENDING_VERIFICATION' then
    raise exception 'A reviewed legal source is immutable; ingest a new version instead';
  end if;
  if new.case_id is distinct from old.case_id or new.title is distinct from old.title
    or new.source_type is distinct from old.source_type or new.jurisdiction is distinct from old.jurisdiction
    or new.authority is distinct from old.authority or new.act_or_regulation is distinct from old.act_or_regulation
    or new.section is distinct from old.section or new.subsection is distinct from old.subsection
    or new.publication_date is distinct from old.publication_date or new.effective_date is distinct from old.effective_date
    or new.version_label is distinct from old.version_label or new.official_source_url is distinct from old.official_source_url
    or new.source_text is distinct from old.source_text or new.source_sha256 is distinct from old.source_sha256
    or new.created_by is distinct from old.created_by or new.retrieved_at is distinct from old.retrieved_at then
    raise exception 'Legal source evidence is immutable';
  end if;
  if new.verification_status = 'VERIFIED_OFFICIAL' then
    if new.verified_by is distinct from auth.uid() or new.verified_at is null or length(trim(coalesce(new.verification_notes,''))) < 20 then
      raise exception 'An authenticated reviewer attestation is required';
    end if;
  else
    new.verified_by := null;
    new.verified_at := null;
  end if;
  new.updated_at := now();
  return new;
end;
$$;
drop trigger if exists legal_sources_guard_update on public.legal_sources;
create trigger legal_sources_guard_update before update on public.legal_sources for each row execute function public.guard_legal_source_integrity();

drop policy if exists legal_analyses_member_select on public.legal_analyses;
create policy legal_analyses_member_select on public.legal_analyses for select to authenticated using (private.can_access_case(case_id));
drop policy if exists legal_analyses_writer_insert on public.legal_analyses;
create policy legal_analyses_writer_insert on public.legal_analyses for insert to authenticated with check (
  created_by = auth.uid()
  and private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[])
  and private.finding_case_id(finding_id) = case_id
);

create or replace function private.legal_source_case_id(source_id uuid)
returns uuid language sql stable security definer set search_path = ''
as $$ select s.case_id from public.legal_sources s where s.id = source_id $$;
create or replace function private.legal_analysis_case_id(analysis_id uuid)
returns uuid language sql stable security definer set search_path = ''
as $$ select a.case_id from public.legal_analyses a where a.id = analysis_id $$;

drop policy if exists legal_analysis_sources_member_select on public.legal_analysis_sources;
create policy legal_analysis_sources_member_select on public.legal_analysis_sources for select to authenticated using (private.can_access_case(private.legal_analysis_case_id(legal_analysis_id)));
drop policy if exists legal_analysis_sources_writer_insert on public.legal_analysis_sources;
create policy legal_analysis_sources_writer_insert on public.legal_analysis_sources for insert to authenticated with check (
  private.has_case_role(private.legal_analysis_case_id(legal_analysis_id), array['OWNER','INVESTIGATOR']::text[])
  and private.legal_analysis_case_id(legal_analysis_id) = private.legal_source_case_id(legal_source_id)
);

drop policy if exists recommendations_member_select on public.investigation_recommendations;
create policy recommendations_member_select on public.investigation_recommendations for select to authenticated using (private.can_access_case(case_id));
drop policy if exists recommendations_writer_insert on public.investigation_recommendations;
create policy recommendations_writer_insert on public.investigation_recommendations for insert to authenticated with check (
  created_by = auth.uid()
  and private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[])
  and private.finding_case_id(finding_id) = case_id
  and private.legal_analysis_case_id(legal_analysis_id) = case_id
  and (legal_source_id is null or private.legal_source_case_id(legal_source_id) = case_id)
);
drop policy if exists recommendations_reviewer_update on public.investigation_recommendations;
create policy recommendations_reviewer_update on public.investigation_recommendations for update to authenticated using (private.has_case_role(case_id, array['OWNER','REVIEWER']::text[])) with check (
  private.has_case_role(case_id, array['OWNER','REVIEWER']::text[])
  and private.finding_case_id(finding_id) = case_id
  and private.legal_analysis_case_id(legal_analysis_id) = case_id
  and (legal_source_id is null or private.legal_source_case_id(legal_source_id) = case_id)
);

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
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare analysis_id uuid; recommendation_ids uuid[] := '{}'; item jsonb; source_id uuid; recommendation_id uuid;
begin
  if not private.has_case_role(p_case_id, array['OWNER','INVESTIGATOR']::text[]) then
    raise exception 'Case access denied';
  end if;
  if not exists (select 1 from public.findings f where f.id = p_finding_id and f.case_id = p_case_id) then
    raise exception 'Finding is unavailable';
  end if;
  if exists (select 1 from unnest(coalesce(p_source_ids, '{}'::uuid[])) as x(sid)
    where not exists (select 1 from public.legal_sources s where s.id = x.sid and s.case_id = p_case_id and s.verification_status = 'VERIFIED_OFFICIAL')) then
    raise exception 'A legal source is unavailable or not verified';
  end if;
  insert into public.legal_analyses(case_id, finding_id, status, legal_relevance, missing_evidence, provider, model_name, prompt_version)
  values(p_case_id, p_finding_id, p_status, p_legal_relevance, p_missing_evidence, p_provider, p_model_name, p_prompt_version)
  returning id into analysis_id;
  foreach source_id in array coalesce(p_source_ids, '{}'::uuid[]) loop
    insert into public.legal_analysis_sources(legal_analysis_id, legal_source_id) values(analysis_id, source_id);
  end loop;
  for item in select value from jsonb_array_elements(coalesce(p_recommendations, '[]'::jsonb)) loop
    if item->>'legal_source_id' is not null and not exists (
      select 1 from public.legal_sources s where s.id = (item->>'legal_source_id')::uuid and s.case_id = p_case_id and s.verification_status = 'VERIFIED_OFFICIAL'
    ) then raise exception 'Recommendation source is unavailable or not verified'; end if;
    insert into public.investigation_recommendations(case_id, finding_id, legal_analysis_id, legal_source_id, action, reason, evidence_basis, priority)
    values(p_case_id, p_finding_id, analysis_id, nullif(item->>'legal_source_id','')::uuid,
      item->>'action', item->>'reason', item->>'evidence_basis', item->>'priority')
    returning id into recommendation_id;
    recommendation_ids := array_append(recommendation_ids, recommendation_id);
  end loop;
  return jsonb_build_object('legal_analysis_id', analysis_id, 'recommendation_ids', to_jsonb(recommendation_ids));
end;
$$;

create or replace function public.populate_review_statuses()
returns trigger language plpgsql security invoker set search_path = ''
as $$
declare prior_status text;
begin
  select f.status into prior_status from public.findings f where f.id = new.finding_id;
  if prior_status is null then raise exception 'Finding is unavailable'; end if;
  new.previous_status := prior_status;
  new.new_status := case new.decision
    when 'VERIFIED' then 'VERIFIED'
    when 'REJECTED' then 'REJECTED'
    when 'NEEDS_MORE_REVIEW' then 'NEEDS_MORE_REVIEW'
    when 'REQUEST_MORE_EVIDENCE' then 'NEEDS_MORE_REVIEW'
    when 'MARK_RESOLVED' then 'RESOLVED'
    when 'ESCALATE' then 'ESCALATED'
  end;
  new.reviewer_notes := coalesce(new.reviewer_notes, new.comment);
  return new;
end;
$$;
drop trigger if exists populate_review_statuses_before_insert on public.review_actions;
create trigger populate_review_statuses_before_insert before insert on public.review_actions for each row execute function public.populate_review_statuses();

create or replace function public.audit_review_action()
returns trigger language plpgsql security definer set search_path = ''
as $$
declare target_case uuid;
begin
  select f.case_id into target_case from public.findings f where f.id = new.finding_id;
  update public.findings set status = new.new_status, updated_at = now() where id = new.finding_id;
  insert into public.audit_events (case_id, actor_user_id, action, entity_type, entity_id, metadata)
  values (target_case, new.reviewer_user_id, 'HUMAN_REVIEWED', 'finding', new.finding_id,
    jsonb_build_object('decision', new.decision, 'previous_status', new.previous_status, 'new_status', new.new_status));
  if new.decision = 'MARK_RESOLVED' then
    insert into public.audit_events (case_id, actor_user_id, action, entity_type, entity_id)
    values (target_case, new.reviewer_user_id, 'FINDING_RESOLVED', 'finding', new.finding_id);
  end if;
  return new;
end;
$$;

create or replace function public.audit_legal_source_event()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    insert into public.audit_events(case_id, actor_user_id, action, entity_type, entity_id, metadata)
    values(new.case_id, auth.uid(), 'LEGAL_SOURCE_INGESTED', 'legal_source', new.id,
      jsonb_build_object('verification_status', new.verification_status, 'source_sha256', new.source_sha256));
  elsif new.verification_status is distinct from old.verification_status then
    insert into public.audit_events(case_id, actor_user_id, action, entity_type, entity_id, metadata)
    values(new.case_id, auth.uid(), case when new.verification_status = 'VERIFIED_OFFICIAL' then 'LEGAL_SOURCE_VERIFIED' else 'LEGAL_SOURCE_REVIEWED' end, 'legal_source', new.id,
      jsonb_build_object('previous_status', old.verification_status, 'new_status', new.verification_status, 'review_notes', new.verification_notes));
  end if;
  return new;
end;
$$;
drop trigger if exists legal_sources_audit_insert on public.legal_sources;
create trigger legal_sources_audit_insert after insert on public.legal_sources for each row execute function public.audit_legal_source_event();
drop trigger if exists legal_sources_audit_update on public.legal_sources;
create trigger legal_sources_audit_update after update on public.legal_sources for each row execute function public.audit_legal_source_event();

create or replace function public.audit_legal_analysis_event()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.audit_events(case_id, actor_user_id, action, entity_type, entity_id, metadata)
  values(new.case_id, auth.uid(), 'LEGAL_ANALYSIS_GENERATED', 'legal_analysis', new.id,
    jsonb_build_object('status', new.status, 'provider', new.provider, 'model_name', new.model_name, 'human_review_required', new.requires_human_review));
  return new;
end;
$$;
drop trigger if exists legal_analyses_audit_insert on public.legal_analyses;
create trigger legal_analyses_audit_insert after insert on public.legal_analyses for each row execute function public.audit_legal_analysis_event();

create or replace function public.audit_recommendation_event()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    insert into public.audit_events(case_id, actor_user_id, action, entity_type, entity_id, metadata)
    values(new.case_id, auth.uid(), 'RECOMMENDATION_GENERATED', 'recommendation', new.id,
      jsonb_build_object('priority', new.priority, 'finding_id', new.finding_id));
  elsif new.status is distinct from old.status then
    insert into public.audit_events(case_id, actor_user_id, action, entity_type, entity_id, metadata)
    values(new.case_id, auth.uid(), 'RECOMMENDATION_REVIEWED', 'recommendation', new.id,
      jsonb_build_object('previous_status', old.status, 'new_status', new.status));
  end if;
  return new;
end;
$$;
drop trigger if exists recommendations_audit_insert on public.investigation_recommendations;
create trigger recommendations_audit_insert after insert on public.investigation_recommendations for each row execute function public.audit_recommendation_event();
drop trigger if exists recommendations_audit_update on public.investigation_recommendations;
create trigger recommendations_audit_update after update on public.investigation_recommendations for each row execute function public.audit_recommendation_event();

revoke all on function private.legal_source_case_id(uuid), private.legal_analysis_case_id(uuid) from public, anon;
grant execute on function private.legal_source_case_id(uuid), private.legal_analysis_case_id(uuid) to authenticated;
revoke all on function public.register_legal_analysis(uuid,uuid,text,jsonb,jsonb,text,text,text,uuid[],jsonb) from public, anon;
grant execute on function public.register_legal_analysis(uuid,uuid,text,jsonb,jsonb,text,text,text,uuid[],jsonb) to authenticated;
revoke all on function public.populate_review_statuses(), public.guard_legal_source_insert(), public.guard_legal_source_integrity(), public.audit_legal_source_event(), public.audit_legal_analysis_event(), public.audit_recommendation_event() from public, anon;
