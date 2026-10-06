create extension if not exists pgcrypto with schema extensions;

create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.cases (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users (id),
  case_number text not null unique default ('AD-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 10))),
  title text not null check (length(trim(title)) between 1 and 200),
  description text not null default '' check (length(description) <= 5000),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'REVIEW', 'COMPLETED', 'ARCHIVED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.case_members (
  case_id uuid not null references public.cases (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('OWNER', 'INVESTIGATOR', 'REVIEWER', 'VIEWER')),
  created_at timestamptz not null default now(),
  primary key (case_id, user_id)
);

create index case_members_user_case_idx on public.case_members (user_id, case_id);

create function private.can_access_case(target_case uuid, actor uuid default auth.uid())
returns boolean language sql stable security definer set search_path = ''
as $$
  select actor is not null and exists (
    select 1 from public.case_members m
    where m.case_id = target_case and m.user_id = actor
  );
$$;

create function private.has_case_role(target_case uuid, allowed_roles text[], actor uuid default auth.uid())
returns boolean language sql stable security definer set search_path = ''
as $$
  select actor is not null and exists (
    select 1 from public.case_members m
    where m.case_id = target_case and m.user_id = actor and m.role = any(allowed_roles)
  );
$$;

revoke all on function private.can_access_case(uuid, uuid) from public, anon;
revoke all on function private.has_case_role(uuid, text[], uuid) from public, anon;
grant execute on function private.can_access_case(uuid, uuid) to authenticated;
grant execute on function private.has_case_role(uuid, text[], uuid) to authenticated;

create function public.create_owner_case_membership()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.case_members (case_id, user_id, role)
  values (new.id, new.owner_id, 'OWNER');
  return new;
end;
$$;

create trigger cases_add_owner_membership
after insert on public.cases
for each row execute function public.create_owner_case_membership();

create function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', ''))
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_auth_user();

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases (id) on delete cascade,
  uploaded_by uuid not null default auth.uid() references auth.users (id),
  name text not null check (length(name) between 1 and 255),
  document_type text not null default 'CONTRACT',
  created_at timestamptz not null default now()
);

create table public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  version_label text not null default 'v1',
  source_filename text not null,
  mime_type text not null check (mime_type = 'application/pdf'),
  storage_key text not null unique,
  sha256_hash text not null check (sha256_hash ~ '^[a-f0-9]{64}$'),
  effective_from date,
  effective_to date,
  is_current boolean not null default true,
  page_count integer not null check (page_count >= 0),
  processing_status text not null default 'READY' check (processing_status in ('PROCESSING', 'READY', 'FAILED')),
  created_at timestamptz not null default now(),
  unique (document_id, version_label)
);

create unique index document_versions_one_current_idx on public.document_versions (document_id) where is_current;

create table public.document_sections (
  id uuid primary key default gen_random_uuid(),
  document_version_id uuid not null references public.document_versions (id) on delete cascade,
  page_number integer not null check (page_number > 0),
  section_label text,
  clause_label text,
  paragraph_index integer not null default 0 check (paragraph_index >= 0),
  content text not null check (length(content) > 0),
  content_hash text not null check (content_hash ~ '^[a-f0-9]{64}$'),
  search_vector tsvector generated always as (to_tsvector('english', content)) stored,
  created_at timestamptz not null default now(),
  unique (document_version_id, page_number, paragraph_index)
);
create index document_sections_fts_idx on public.document_sections using gin (search_vector);

create table public.recordings (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases (id) on delete cascade,
  uploaded_by uuid not null default auth.uid() references auth.users (id),
  original_filename text not null,
  mime_type text not null check (mime_type = 'audio/wav'),
  storage_key text not null unique,
  sha256_hash text not null check (sha256_hash ~ '^[a-f0-9]{64}$'),
  file_size_bytes bigint not null check (file_size_bytes > 0),
  duration_ms bigint,
  processing_status text not null default 'UPLOADED' check (processing_status in ('UPLOADED', 'PROCESSING', 'READY', 'FAILED')),
  asr_provider text,
  asr_model text,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

create table public.transcript_segments (
  id uuid primary key default gen_random_uuid(),
  recording_id uuid not null references public.recordings (id) on delete cascade,
  sequence_number integer not null check (sequence_number >= 0),
  speaker_label text,
  start_ms bigint not null check (start_ms >= 0),
  end_ms bigint not null check (end_ms >= start_ms),
  text text not null,
  source_hash text not null check (source_hash ~ '^[a-f0-9]{64}$'),
  quality_score numeric check (quality_score between 0 and 1),
  created_at timestamptz not null default now(),
  unique (recording_id, sequence_number)
);

create table public.findings (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases (id) on delete cascade,
  recording_id uuid not null references public.recordings (id),
  transcript_segment_id uuid not null references public.transcript_segments (id),
  document_version_id uuid not null references public.document_versions (id),
  relation_type text not null check (relation_type in ('CONSISTENT', 'POSSIBLE_DISCREPANCY', 'CONDITIONAL', 'TEMPORAL_VERSION_MISMATCH', 'DEFINITION_EXCEPTION_MISMATCH', 'INSUFFICIENT_EVIDENCE', 'NEEDS_HUMAN_REVIEW')),
  status text not null default 'NEEDS_REVIEW' check (status in ('NEEDS_REVIEW', 'VERIFIED', 'REJECTED', 'NEEDS_MORE_REVIEW')),
  summary text not null,
  explanation text not null,
  uncertainties jsonb not null default '[]'::jsonb,
  human_review_required boolean not null default true check (human_review_required),
  provider text not null,
  model_name text not null,
  model_version text,
  prompt_version text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.finding_evidence (
  id uuid primary key default gen_random_uuid(),
  finding_id uuid not null references public.findings (id) on delete cascade,
  document_section_id uuid references public.document_sections (id),
  transcript_segment_id uuid references public.transcript_segments (id),
  quoted_text text not null,
  start_ms bigint,
  end_ms bigint,
  page_number integer,
  section_label text,
  clause_label text,
  source_hash text not null check (source_hash ~ '^[a-f0-9]{64}$'),
  created_at timestamptz not null default now(),
  check ((document_section_id is not null) <> (transcript_segment_id is not null))
);

create table public.review_actions (
  id uuid primary key default gen_random_uuid(),
  finding_id uuid not null references public.findings (id) on delete cascade,
  reviewer_user_id uuid not null default auth.uid() references auth.users (id),
  decision text not null check (decision in ('VERIFIED', 'REJECTED', 'NEEDS_MORE_REVIEW')),
  comment text check (length(comment) <= 5000),
  reviewed_at timestamptz not null default now()
);

create table public.audit_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases (id) on delete cascade,
  actor_user_id uuid not null default auth.uid() references auth.users (id),
  action text not null,
  entity_type text not null,
  entity_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index documents_case_idx on public.documents (case_id, created_at desc);
create index document_versions_document_idx on public.document_versions (document_id, created_at desc);
create index recordings_case_idx on public.recordings (case_id, created_at desc);
create index transcript_segments_recording_idx on public.transcript_segments (recording_id, sequence_number);
create index findings_case_status_idx on public.findings (case_id, status, created_at desc);
create index finding_evidence_finding_idx on public.finding_evidence (finding_id);
create index review_actions_finding_idx on public.review_actions (finding_id, reviewed_at desc);
create index audit_events_case_idx on public.audit_events (case_id, created_at desc);

create function private.document_case_id(document_id uuid)
returns uuid language sql stable security definer set search_path = ''
as $$ select d.case_id from public.documents d where d.id = document_id $$;

create function private.version_case_id(version_id uuid)
returns uuid language sql stable security definer set search_path = ''
as $$ select d.case_id from public.document_versions v join public.documents d on d.id = v.document_id where v.id = version_id $$;

create function private.recording_case_id(recording_id uuid)
returns uuid language sql stable security definer set search_path = ''
as $$ select r.case_id from public.recordings r where r.id = recording_id $$;

create function private.finding_case_id(finding_id uuid)
returns uuid language sql stable security definer set search_path = ''
as $$ select f.case_id from public.findings f where f.id = finding_id $$;

revoke all on function private.document_case_id(uuid) from public, anon;
revoke all on function private.version_case_id(uuid) from public, anon;
revoke all on function private.recording_case_id(uuid) from public, anon;
revoke all on function private.finding_case_id(uuid) from public, anon;
grant execute on function private.document_case_id(uuid) to authenticated;
grant execute on function private.version_case_id(uuid) to authenticated;
grant execute on function private.recording_case_id(uuid) to authenticated;
grant execute on function private.finding_case_id(uuid) to authenticated;

create function private.storage_case_id(object_name text)
returns uuid language plpgsql immutable set search_path = ''
as $$
begin
  return nullif((storage.foldername(object_name))[1], '')::uuid;
exception when invalid_text_representation then
  return null;
end;
$$;
revoke all on function private.storage_case_id(text) from public, anon;
grant execute on function private.storage_case_id(text) to authenticated;

alter table public.profiles enable row level security;
alter table public.cases enable row level security;
alter table public.case_members enable row level security;
alter table public.documents enable row level security;
alter table public.document_versions enable row level security;
alter table public.document_sections enable row level security;
alter table public.recordings enable row level security;
alter table public.transcript_segments enable row level security;
alter table public.findings enable row level security;
alter table public.finding_evidence enable row level security;
alter table public.review_actions enable row level security;
alter table public.audit_events enable row level security;

revoke all on public.profiles, public.cases, public.case_members, public.documents,
  public.document_versions, public.document_sections, public.recordings,
  public.transcript_segments, public.findings, public.finding_evidence,
  public.review_actions, public.audit_events from anon;
grant select, insert, update on public.profiles to authenticated;
grant select, insert, update on public.cases to authenticated;
grant select, insert, update, delete on public.case_members to authenticated;
grant select, insert, update on public.documents, public.document_versions, public.recordings to authenticated;
grant select, insert on public.document_sections, public.transcript_segments to authenticated;
grant select on public.finding_evidence, public.audit_events, public.findings to authenticated;
grant select, insert on public.review_actions to authenticated;

create policy profiles_self_select on public.profiles for select to authenticated using (id = (select auth.uid()));
create policy profiles_self_update on public.profiles for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy cases_member_select on public.cases for select to authenticated using (private.can_access_case(id));
create policy cases_self_insert on public.cases for insert to authenticated with check (owner_id = (select auth.uid()));
create policy cases_owner_update on public.cases for update to authenticated using (private.has_case_role(id, array['OWNER']::text[])) with check (private.has_case_role(id, array['OWNER']::text[]));

create policy members_case_select on public.case_members for select to authenticated using (private.can_access_case(case_id));
create policy members_owner_insert on public.case_members for insert to authenticated with check (private.has_case_role(case_id, array['OWNER']::text[]));
create policy members_owner_update on public.case_members for update to authenticated using (private.has_case_role(case_id, array['OWNER']::text[])) with check (private.has_case_role(case_id, array['OWNER']::text[]));
create policy members_owner_delete on public.case_members for delete to authenticated using (private.has_case_role(case_id, array['OWNER']::text[]) and user_id <> auth.uid());

create policy documents_member_select on public.documents for select to authenticated using (private.can_access_case(case_id));
create policy documents_writer_insert on public.documents for insert to authenticated with check (uploaded_by = auth.uid() and private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[]));
create policy documents_writer_update on public.documents for update to authenticated using (private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[])) with check (private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[]));

create policy versions_member_select on public.document_versions for select to authenticated using (private.can_access_case(private.document_case_id(document_id)));
create policy versions_writer_insert on public.document_versions for insert to authenticated with check (private.has_case_role(private.document_case_id(document_id), array['OWNER','INVESTIGATOR']::text[]));
create policy versions_writer_update on public.document_versions for update to authenticated using (private.has_case_role(private.document_case_id(document_id), array['OWNER','INVESTIGATOR']::text[])) with check (private.has_case_role(private.document_case_id(document_id), array['OWNER','INVESTIGATOR']::text[]));

create policy sections_member_select on public.document_sections for select to authenticated using (private.can_access_case(private.version_case_id(document_version_id)));
create policy sections_writer_insert on public.document_sections for insert to authenticated with check (private.has_case_role(private.version_case_id(document_version_id), array['OWNER','INVESTIGATOR']::text[]));

create policy recordings_member_select on public.recordings for select to authenticated using (private.can_access_case(case_id));
create policy recordings_writer_insert on public.recordings for insert to authenticated with check (uploaded_by = auth.uid() and private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[]));
create policy recordings_writer_update on public.recordings for update to authenticated using (private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[])) with check (private.has_case_role(case_id, array['OWNER','INVESTIGATOR']::text[]));

create policy segments_member_select on public.transcript_segments for select to authenticated using (private.can_access_case(private.recording_case_id(recording_id)));
create policy segments_writer_insert on public.transcript_segments for insert to authenticated with check (private.has_case_role(private.recording_case_id(recording_id), array['OWNER','INVESTIGATOR']::text[]));

create policy findings_member_select on public.findings for select to authenticated using (private.can_access_case(case_id));

create policy evidence_member_select on public.finding_evidence for select to authenticated using (private.can_access_case(private.finding_case_id(finding_id)));

create policy reviews_member_select on public.review_actions for select to authenticated using (private.can_access_case(private.finding_case_id(finding_id)));
create policy reviewers_insert on public.review_actions for insert to authenticated with check (
  reviewer_user_id = (select auth.uid())
  and private.has_case_role(private.finding_case_id(finding_id), array['OWNER','REVIEWER']::text[])
);

create policy audit_member_select on public.audit_events for select to authenticated using (private.can_access_case(case_id));

create function public.register_document_ingest(
  p_case_id uuid,
  p_name text,
  p_source_filename text,
  p_storage_key text,
  p_sha256_hash text,
  p_page_count integer,
  p_sections jsonb
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare new_document_id uuid; new_version_id uuid; section jsonb; section_count integer := 0;
begin
  insert into public.documents (case_id, name) values (p_case_id, p_name)
    returning id into new_document_id;
  insert into public.document_versions (
    document_id, version_label, source_filename, mime_type, storage_key,
    sha256_hash, page_count
  ) values (
    new_document_id, 'v1', p_source_filename, 'application/pdf', p_storage_key,
    p_sha256_hash, p_page_count
  ) returning id into new_version_id;
  for section in select value from jsonb_array_elements(p_sections) loop
    insert into public.document_sections (
      document_version_id, page_number, section_label, clause_label,
      paragraph_index, content, content_hash
    ) values (
      new_version_id, (section->>'page_number')::integer,
      nullif(section->>'section_label', ''), nullif(section->>'clause_label', ''),
      (section->>'paragraph_index')::integer, section->>'content', section->>'content_hash'
    );
    section_count := section_count + 1;
  end loop;
  return jsonb_build_object('document_id', new_document_id, 'version_id', new_version_id, 'section_count', section_count);
end;
$$;

create function public.register_audio_ingest(
  p_case_id uuid,
  p_original_filename text,
  p_storage_key text,
  p_sha256_hash text,
  p_file_size_bytes bigint,
  p_duration_ms bigint,
  p_asr_provider text,
  p_asr_model text,
  p_segments jsonb
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare new_recording_id uuid; segment jsonb; segment_count integer := 0;
begin
  insert into public.recordings (
    case_id, original_filename, mime_type, storage_key, sha256_hash,
    file_size_bytes, duration_ms, processing_status, asr_provider, asr_model, processed_at
  ) values (
    p_case_id, p_original_filename, 'audio/wav', p_storage_key, p_sha256_hash,
    p_file_size_bytes, p_duration_ms, 'READY', p_asr_provider, p_asr_model, now()
  ) returning id into new_recording_id;
  for segment in select value from jsonb_array_elements(p_segments) loop
    insert into public.transcript_segments (
      recording_id, sequence_number, speaker_label, start_ms, end_ms, text, source_hash, quality_score
    ) values (
      new_recording_id, (segment->>'sequence_number')::integer,
      nullif(segment->>'speaker_label', ''), (segment->>'start_ms')::bigint,
      (segment->>'end_ms')::bigint, segment->>'text',
      encode(extensions.digest(convert_to(segment->>'text', 'UTF8'), 'sha256'), 'hex'),
      nullif(segment->>'quality_score', '')::numeric
    );
    segment_count := segment_count + 1;
  end loop;
  return jsonb_build_object('recording_id', new_recording_id, 'segment_count', segment_count);
end;
$$;

create function public.register_finding(
  p_case_id uuid,
  p_recording_id uuid,
  p_transcript_segment_id uuid,
  p_document_version_id uuid,
  p_relation_type text,
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
  if not private.has_case_role(p_case_id, array['OWNER','INVESTIGATOR']::text[]) then
    raise insufficient_privilege using message = 'Case access denied';
  end if;
  if not exists (select 1 from public.recordings r where r.id = p_recording_id and r.case_id = p_case_id)
     or not exists (select 1 from public.transcript_segments s where s.id = p_transcript_segment_id and s.recording_id = p_recording_id)
     or private.version_case_id(p_document_version_id) is distinct from p_case_id then
    raise check_violation using message = 'Evidence does not belong to the requested case';
  end if;
  insert into public.findings (
    case_id, recording_id, transcript_segment_id, document_version_id,
    relation_type, summary, explanation, uncertainties, provider, model_name, prompt_version
  ) values (
    p_case_id, p_recording_id, p_transcript_segment_id, p_document_version_id,
    p_relation_type, p_summary, p_explanation, coalesce(p_uncertainties, '[]'::jsonb),
    p_provider, p_model_name, p_prompt_version
  ) returning id into new_finding_id;
  for item in select value from jsonb_array_elements(p_evidence) loop
    if nullif(item->>'document_section_id', '') is not null and not exists (
      select 1 from public.document_sections ds
      where ds.id = (item->>'document_section_id')::uuid
        and ds.document_version_id = p_document_version_id
        and ds.content_hash = item->>'source_hash'
        and ds.content = item->>'quoted_text'
    ) then
      raise check_violation using message = 'Document evidence does not match the source';
    end if;
    if nullif(item->>'transcript_segment_id', '') is not null and not exists (
      select 1 from public.transcript_segments ts
      where ts.id = (item->>'transcript_segment_id')::uuid
        and ts.id = p_transcript_segment_id
        and ts.source_hash = item->>'source_hash'
        and ts.text = item->>'quoted_text'
    ) then
      raise check_violation using message = 'Transcript evidence does not match the source';
    end if;
    insert into public.finding_evidence (
      finding_id, document_section_id, transcript_segment_id, quoted_text,
      start_ms, end_ms, page_number, section_label, clause_label, source_hash
    ) values (
      new_finding_id, nullif(item->>'document_section_id', '')::uuid,
      nullif(item->>'transcript_segment_id', '')::uuid, item->>'quoted_text',
      nullif(item->>'start_ms', '')::bigint, nullif(item->>'end_ms', '')::bigint,
      nullif(item->>'page_number', '')::integer, nullif(item->>'section_label', ''),
      nullif(item->>'clause_label', ''), item->>'source_hash'
    );
    evidence_count := evidence_count + 1;
  end loop;
  return jsonb_build_object('finding_id', new_finding_id, 'evidence_count', evidence_count);
end;
$$;

grant execute on function public.register_document_ingest(uuid, text, text, text, text, integer, jsonb) to authenticated;
grant execute on function public.register_audio_ingest(uuid, text, text, text, bigint, bigint, text, text, jsonb) to authenticated;
grant execute on function public.register_finding(uuid, uuid, uuid, uuid, text, text, text, jsonb, text, text, text, jsonb) to authenticated;
revoke all on function public.register_document_ingest(uuid, text, text, text, text, integer, jsonb) from public, anon;
revoke all on function public.register_audio_ingest(uuid, text, text, text, bigint, bigint, text, text, jsonb) from public, anon;
revoke all on function public.register_finding(uuid, uuid, uuid, uuid, text, text, text, jsonb, text, text, text, jsonb) from public, anon;
revoke insert, update, delete on public.findings, public.finding_evidence, public.audit_events from authenticated;

create function public.audit_finding_creation()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.audit_events (case_id, actor_user_id, action, entity_type, entity_id, metadata)
  values (new.case_id, auth.uid(), 'FINDING_CREATED', 'finding', new.id,
    jsonb_build_object('relation_type', new.relation_type, 'provider', new.provider, 'model', new.model_name));
  return new;
end;
$$;
create trigger findings_audit_creation after insert on public.findings
for each row execute function public.audit_finding_creation();

create function public.audit_case_creation()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.audit_events (case_id, actor_user_id, action, entity_type, entity_id)
  values (new.id, new.owner_id, 'CASE_CREATED', 'case', new.id);
  return new;
end;
$$;

create trigger cases_audit_creation after insert on public.cases
for each row execute function public.audit_case_creation();

create function public.audit_review_action()
returns trigger language plpgsql security definer set search_path = ''
as $$
declare target_case uuid;
begin
  select f.case_id into target_case from public.findings f where f.id = new.finding_id;
  update public.findings set status = new.decision, updated_at = now() where id = new.finding_id;
  insert into public.audit_events (case_id, actor_user_id, action, entity_type, entity_id, metadata)
  values (target_case, new.reviewer_user_id, 'FINDING_REVIEWED', 'finding', new.finding_id,
    jsonb_build_object('decision', new.decision));
  return new;
end;
$$;

create trigger finding_reviews_audit after insert on public.review_actions
for each row execute function public.audit_review_action();

revoke all on function public.create_owner_case_membership() from public, anon;
revoke all on function public.handle_new_auth_user() from public, anon;
revoke all on function public.audit_case_creation() from public, anon;
revoke all on function public.audit_review_action() from public, anon;
revoke all on function public.audit_finding_creation() from public, anon;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('evidence', 'evidence', false, 52428800, array['application/pdf', 'audio/wav'])
on conflict (id) do update set public = false, file_size_limit = 52428800,
  allowed_mime_types = array['application/pdf', 'audio/wav'];

create policy evidence_storage_member_select on storage.objects for select to authenticated
using (bucket_id = 'evidence' and private.can_access_case(private.storage_case_id(name)));
create policy evidence_storage_writer_insert on storage.objects for insert to authenticated
with check (bucket_id = 'evidence' and private.has_case_role(private.storage_case_id(name), array['OWNER','INVESTIGATOR']::text[]));
create policy evidence_storage_writer_update on storage.objects for update to authenticated
using (bucket_id = 'evidence' and private.has_case_role(private.storage_case_id(name), array['OWNER','INVESTIGATOR']::text[]))
with check (bucket_id = 'evidence' and private.has_case_role(private.storage_case_id(name), array['OWNER','INVESTIGATOR']::text[]));
create policy evidence_storage_writer_delete on storage.objects for delete to authenticated
using (bucket_id = 'evidence' and private.has_case_role(private.storage_case_id(name), array['OWNER','INVESTIGATOR']::text[]));
