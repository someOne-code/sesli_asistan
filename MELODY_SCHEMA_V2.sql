-- ==========================================================================
-- MELODY - Multi-Tenant Voice AI SaaS Schema (Paste-ready)
-- PostgreSQL / Supabase
-- Includes: RLS hardening, overlap protection, timezone-aware availability,
-- multi-window availability, function security, index tuning, data validation.
-- ==========================================================================

-- =========================
-- 1) Extensions
-- =========================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- =========================
-- 2) Enum types (idempotent)
-- =========================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_status') THEN
    CREATE TYPE booking_status AS ENUM ('PENDING', 'ACCEPTED', 'CANCELLED', 'COMPLETED', 'NO_SHOW');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'call_status') THEN
    CREATE TYPE call_status AS ENUM ('QUEUED', 'RINGING', 'IN_PROGRESS', 'FORWARDING', 'ENDED');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'call_end_reason') THEN
    CREATE TYPE call_end_reason AS ENUM (
      'customer-ended-call',
      'assistant-ended-call',
      'assistant-error',
      'exceeded-max-duration',
      'silence-timeout',
      'unknown'
    );
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'industry_type') THEN
    CREATE TYPE industry_type AS ENUM ('BARBER', 'DENTIST', 'LAWYER', 'SALON', 'CLINIC', 'RESTAURANT', 'GYM', 'OTHER');
  END IF;
END $$;

-- =========================
-- 3) Validation helpers
-- =========================
CREATE OR REPLACE FUNCTION validate_e164_phone(phone TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  IF phone IS NULL THEN
    RETURN TRUE;
  END IF;
  RETURN phone ~ '^\+[1-9][0-9]{6,14}$';
END;
$$;

CREATE OR REPLACE FUNCTION normalize_phone_to_e164(phone TEXT, default_country_code TEXT DEFAULT '+90')
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  cleaned TEXT;
BEGIN
  IF phone IS NULL OR btrim(phone) = '' THEN
    RETURN NULL;
  END IF;

  cleaned := regexp_replace(phone, '[^0-9+]', '', 'g');

  IF cleaned ~ '^\+' THEN
    IF cleaned ~ '^\+[1-9][0-9]{6,14}$' THEN
      RETURN cleaned;
    END IF;
    RAISE EXCEPTION 'Invalid E.164 phone: %', phone;
  END IF;

  IF cleaned ~ '^0' THEN
    cleaned := substr(cleaned, 2);
  END IF;

  cleaned := default_country_code || cleaned;

  IF cleaned ~ '^\+[1-9][0-9]{6,14}$' THEN
    RETURN cleaned;
  END IF;

  RAISE EXCEPTION 'Invalid phone: %', phone;
END;
$$;

CREATE OR REPLACE FUNCTION validate_email(email TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  IF email IS NULL THEN
    RETURN TRUE;
  END IF;

  RETURN email ~* '^[a-zA-Z0-9.!#$%&''*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$';
END;
$$;

CREATE OR REPLACE FUNCTION validate_tenant_config(config JSONB)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  IF config IS NULL THEN
    RETURN TRUE;
  END IF;

  IF config ? 'workday_start' AND NOT (config->>'workday_start' ~ '^([01]?[0-9]|2[0-3]):[0-5][0-9]$') THEN
    RETURN FALSE;
  END IF;

  IF config ? 'workday_end' AND NOT (config->>'workday_end' ~ '^([01]?[0-9]|2[0-3]):[0-5][0-9]$') THEN
    RETURN FALSE;
  END IF;

  RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION validate_call_analysis(analysis JSONB)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  IF analysis IS NULL OR analysis = '{}'::JSONB THEN
    RETURN TRUE;
  END IF;

  IF analysis ? 'successEvaluation' AND jsonb_typeof(analysis->'successEvaluation') NOT IN ('boolean', 'null') THEN
    RETURN FALSE;
  END IF;

  IF analysis ? 'summary' AND jsonb_typeof(analysis->'summary') NOT IN ('string', 'null') THEN
    RETURN FALSE;
  END IF;

  RETURN TRUE;
END;
$$;

-- =========================
-- 4) Tables
-- =========================
CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  business_name TEXT NOT NULL,
  industry_type industry_type NOT NULL DEFAULT 'OTHER',
  phone_number TEXT,
  email TEXT,
  address TEXT,
  config JSONB DEFAULT '{}'::jsonb,
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT tenants_phone_e164 CHECK (validate_e164_phone(phone_number)),
  CONSTRAINT tenants_email_valid CHECK (validate_email(email)),
  CONSTRAINT tenants_config_valid CHECK (validate_tenant_config(config))
);

CREATE TABLE IF NOT EXISTS customers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE NOT NULL,
  full_name TEXT,
  phone_number TEXT NOT NULL,
  email TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT unique_customer_phone_per_tenant UNIQUE (tenant_id, phone_number),
  CONSTRAINT customers_phone_e164 CHECK (validate_e164_phone(phone_number)),
  CONSTRAINT customers_email_valid CHECK (validate_email(email))
);

CREATE TABLE IF NOT EXISTS services (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  duration_minutes INTEGER NOT NULL DEFAULT 30,
  price NUMERIC(10,2),
  currency TEXT DEFAULT 'TRY',
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT positive_duration CHECK (duration_minutes > 0),
  CONSTRAINT positive_price CHECK (price >= 0)
);

CREATE TABLE IF NOT EXISTS schedules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE NOT NULL,
  name TEXT NOT NULL,
  timezone TEXT DEFAULT 'UTC',
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE IF NOT EXISTS availability (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE NOT NULL,
  schedule_id UUID REFERENCES schedules(id) ON DELETE CASCADE,
  days INTEGER[] NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT valid_days CHECK (days <@ ARRAY[0,1,2,3,4,5,6]),
  CONSTRAINT valid_time_range CHECK (end_time > start_time)
);

CREATE TABLE IF NOT EXISTS appointments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE NOT NULL,
  uid TEXT UNIQUE NOT NULL DEFAULT uuid_generate_v4()::TEXT,
  title TEXT NOT NULL,
  description TEXT,
  customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
  service_id UUID REFERENCES services(id) ON DELETE SET NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  status booking_status NOT NULL DEFAULT 'PENDING',
  customer_name TEXT,
  customer_phone TEXT,
  customer_email TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  cancellation_reason TEXT,
  rescheduled_from UUID REFERENCES appointments(id),
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT valid_booking_range CHECK (end_time > start_time),
  CONSTRAINT appointments_phone_e164 CHECK (validate_e164_phone(customer_phone)),
  CONSTRAINT appointments_email_valid CHECK (validate_email(customer_email))
);

-- Replace legacy unique-slot with overlap-safe exclusion constraint
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS unique_tenant_timeslot;
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_no_overlap;
ALTER TABLE appointments
  ADD CONSTRAINT appointments_no_overlap
  EXCLUDE USING gist (
    tenant_id WITH =,
    tstzrange(start_time, end_time, '[)') WITH &&
  )
  WHERE (status <> 'CANCELLED');

CREATE TABLE IF NOT EXISTS calls (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE NOT NULL,
  vapi_call_id TEXT UNIQUE,
  status call_status NOT NULL DEFAULT 'QUEUED',
  ended_reason call_end_reason,
  customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
  customer_number TEXT,
  customer_name TEXT,
  duration_seconds INTEGER,
  recording_url TEXT,
  transcript TEXT,
  analysis JSONB DEFAULT '{}'::jsonb,
  artifact JSONB DEFAULT '{}'::jsonb,
  appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT calls_phone_e164 CHECK (validate_e164_phone(customer_number)),
  CONSTRAINT calls_analysis_valid CHECK (validate_call_analysis(analysis))
);

CREATE TABLE IF NOT EXISTS knowledge_base (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  category TEXT,
  tags TEXT[],
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  priority INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- =========================
-- 5) Indexes
-- =========================
CREATE INDEX IF NOT EXISTS idx_tenants_owner ON tenants(owner_id);
CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(is_active) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_customers_phone_lookup ON customers(tenant_id, phone_number) INCLUDE (full_name, email);

CREATE INDEX IF NOT EXISTS idx_services_active ON services(tenant_id, is_active) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_availability_tenant ON availability(tenant_id);
CREATE INDEX IF NOT EXISTS idx_availability_days ON availability USING GIN(days);
CREATE INDEX IF NOT EXISTS idx_availability_date ON availability(tenant_id, date) WHERE date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_appointments_active_range ON appointments(tenant_id, start_time, end_time) WHERE status <> 'CANCELLED';
CREATE INDEX IF NOT EXISTS idx_appointments_customer ON appointments(customer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_service ON appointments(service_id);
CREATE INDEX IF NOT EXISTS idx_appointments_uid ON appointments(uid);

CREATE INDEX IF NOT EXISTS idx_calls_tenant ON calls(tenant_id);
CREATE INDEX IF NOT EXISTS idx_calls_customer ON calls(customer_id);
CREATE INDEX IF NOT EXISTS idx_calls_time_brin ON calls USING BRIN(created_at);
CREATE INDEX IF NOT EXISTS idx_calls_analysis ON calls USING GIN(analysis);
-- Note: no extra index for vapi_call_id since UNIQUE already creates one.

CREATE INDEX IF NOT EXISTS idx_kb_tenant ON knowledge_base(tenant_id);
CREATE INDEX IF NOT EXISTS idx_kb_active ON knowledge_base(tenant_id, priority DESC) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_kb_question_trgm ON knowledge_base USING GIN(question gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_kb_answer_trgm ON knowledge_base USING GIN(answer gin_trgm_ops);

-- =========================
-- 6) RLS (hardened)
-- =========================
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenants_select ON tenants;
DROP POLICY IF EXISTS tenants_insert ON tenants;
DROP POLICY IF EXISTS tenants_update ON tenants;
DROP POLICY IF EXISTS tenants_delete ON tenants;
CREATE POLICY tenants_select ON tenants FOR SELECT USING (auth.uid() = owner_id);
CREATE POLICY tenants_insert ON tenants FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY tenants_update ON tenants FOR UPDATE USING (auth.uid() = owner_id) WITH CHECK (auth.uid() = owner_id);
CREATE POLICY tenants_delete ON tenants FOR DELETE USING (auth.uid() = owner_id);

DROP POLICY IF EXISTS customers_select ON customers;
DROP POLICY IF EXISTS customers_insert ON customers;
DROP POLICY IF EXISTS customers_update ON customers;
DROP POLICY IF EXISTS customers_delete ON customers;
CREATE POLICY customers_select ON customers FOR SELECT USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY customers_insert ON customers FOR INSERT WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY customers_update ON customers FOR UPDATE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid())) WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY customers_delete ON customers FOR DELETE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

DROP POLICY IF EXISTS services_select ON services;
DROP POLICY IF EXISTS services_insert ON services;
DROP POLICY IF EXISTS services_update ON services;
DROP POLICY IF EXISTS services_delete ON services;
CREATE POLICY services_select ON services FOR SELECT USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY services_insert ON services FOR INSERT WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY services_update ON services FOR UPDATE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid())) WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY services_delete ON services FOR DELETE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

DROP POLICY IF EXISTS schedules_select ON schedules;
DROP POLICY IF EXISTS schedules_insert ON schedules;
DROP POLICY IF EXISTS schedules_update ON schedules;
DROP POLICY IF EXISTS schedules_delete ON schedules;
CREATE POLICY schedules_select ON schedules FOR SELECT USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY schedules_insert ON schedules FOR INSERT WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY schedules_update ON schedules FOR UPDATE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid())) WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY schedules_delete ON schedules FOR DELETE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

DROP POLICY IF EXISTS availability_select ON availability;
DROP POLICY IF EXISTS availability_insert ON availability;
DROP POLICY IF EXISTS availability_update ON availability;
DROP POLICY IF EXISTS availability_delete ON availability;
CREATE POLICY availability_select ON availability FOR SELECT USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY availability_insert ON availability FOR INSERT WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY availability_update ON availability FOR UPDATE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid())) WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY availability_delete ON availability FOR DELETE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

DROP POLICY IF EXISTS appointments_select ON appointments;
DROP POLICY IF EXISTS appointments_insert ON appointments;
DROP POLICY IF EXISTS appointments_update ON appointments;
DROP POLICY IF EXISTS appointments_delete ON appointments;
CREATE POLICY appointments_select ON appointments FOR SELECT USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY appointments_insert ON appointments FOR INSERT WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY appointments_update ON appointments FOR UPDATE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid())) WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY appointments_delete ON appointments FOR DELETE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

DROP POLICY IF EXISTS calls_select ON calls;
DROP POLICY IF EXISTS calls_insert ON calls;
DROP POLICY IF EXISTS calls_update ON calls;
DROP POLICY IF EXISTS calls_delete ON calls;
CREATE POLICY calls_select ON calls FOR SELECT USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY calls_insert ON calls FOR INSERT WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY calls_update ON calls FOR UPDATE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid())) WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY calls_delete ON calls FOR DELETE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

DROP POLICY IF EXISTS knowledge_base_select ON knowledge_base;
DROP POLICY IF EXISTS knowledge_base_insert ON knowledge_base;
DROP POLICY IF EXISTS knowledge_base_update ON knowledge_base;
DROP POLICY IF EXISTS knowledge_base_delete ON knowledge_base;
CREATE POLICY knowledge_base_select ON knowledge_base FOR SELECT USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY knowledge_base_insert ON knowledge_base FOR INSERT WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY knowledge_base_update ON knowledge_base FOR UPDATE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid())) WITH CHECK (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));
CREATE POLICY knowledge_base_delete ON knowledge_base FOR DELETE USING (tenant_id IN (SELECT id FROM tenants WHERE owner_id = auth.uid()));

-- =========================
-- 7) Triggers
-- =========================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tenants_updated ON tenants;
DROP TRIGGER IF EXISTS trg_customers_updated ON customers;
DROP TRIGGER IF EXISTS trg_services_updated ON services;
DROP TRIGGER IF EXISTS trg_schedules_updated ON schedules;
DROP TRIGGER IF EXISTS trg_appointments_updated ON appointments;
DROP TRIGGER IF EXISTS trg_calls_updated ON calls;
DROP TRIGGER IF EXISTS trg_kb_updated ON knowledge_base;

CREATE TRIGGER trg_tenants_updated BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_customers_updated BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_services_updated BEFORE UPDATE ON services FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_schedules_updated BEFORE UPDATE ON schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_appointments_updated BEFORE UPDATE ON appointments FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_calls_updated BEFORE UPDATE ON calls FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_kb_updated BEFORE UPDATE ON knowledge_base FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE FUNCTION normalize_phone_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  IF TG_TABLE_NAME = 'customers' THEN
    NEW.phone_number := normalize_phone_to_e164(NEW.phone_number);
  ELSIF TG_TABLE_NAME = 'appointments' AND NEW.customer_phone IS NOT NULL THEN
    NEW.customer_phone := normalize_phone_to_e164(NEW.customer_phone);
  ELSIF TG_TABLE_NAME = 'calls' AND NEW.customer_number IS NOT NULL THEN
    NEW.customer_number := normalize_phone_to_e164(NEW.customer_number);
  ELSIF TG_TABLE_NAME = 'tenants' AND NEW.phone_number IS NOT NULL THEN
    NEW.phone_number := normalize_phone_to_e164(NEW.phone_number);
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_customers_phone ON customers;
DROP TRIGGER IF EXISTS trg_appointments_phone ON appointments;
DROP TRIGGER IF EXISTS trg_calls_phone ON calls;
DROP TRIGGER IF EXISTS trg_tenants_phone ON tenants;

CREATE TRIGGER trg_customers_phone BEFORE INSERT OR UPDATE OF phone_number ON customers FOR EACH ROW EXECUTE FUNCTION normalize_phone_trigger();
CREATE TRIGGER trg_appointments_phone BEFORE INSERT OR UPDATE OF customer_phone ON appointments FOR EACH ROW EXECUTE FUNCTION normalize_phone_trigger();
CREATE TRIGGER trg_calls_phone BEFORE INSERT OR UPDATE OF customer_number ON calls FOR EACH ROW EXECUTE FUNCTION normalize_phone_trigger();
CREATE TRIGGER trg_tenants_phone BEFORE INSERT OR UPDATE OF phone_number ON tenants FOR EACH ROW EXECUTE FUNCTION normalize_phone_trigger();

-- =========================
-- 8) Business functions
-- =========================
CREATE OR REPLACE FUNCTION is_time_slot_available(
  p_tenant_id UUID,
  p_start_time TIMESTAMPTZ,
  p_end_time TIMESTAMPTZ,
  p_exclude_appointment_id UUID DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  RETURN NOT EXISTS (
    SELECT 1
    FROM appointments
    WHERE tenant_id = p_tenant_id
      AND status <> 'CANCELLED'
      AND (p_exclude_appointment_id IS NULL OR id <> p_exclude_appointment_id)
      AND tstzrange(start_time, end_time, '[)') && tstzrange(p_start_time, p_end_time, '[)')
  );
END;
$$;

CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT id FROM tenants WHERE owner_id = auth.uid() LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION check_availability(
  p_tenant_id UUID,
  p_service_id UUID,
  p_start_date DATE,
  p_end_date DATE DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_service_duration INTEGER;
  v_service_title TEXT;
  v_timezone TEXT;
  v_default_start TIME;
  v_default_end TIME;
  v_current_date DATE;
  v_day_of_week INTEGER;
  v_available_slots JSONB := '[]'::jsonb;
  v_day_slots JSONB;
  v_has_date_override BOOLEAN;
  v_workday_start_tz TIMESTAMPTZ;
  v_workday_end_tz TIMESTAMPTZ;
  v_last_end TIMESTAMPTZ;
  v_gap_minutes INTEGER;
  r_avail RECORD;
  r_app RECORD;
  v_had_window BOOLEAN;
BEGIN
  IF p_end_date IS NULL THEN
    p_end_date := p_start_date;
  END IF;

  IF p_end_date < p_start_date THEN
    RETURN jsonb_build_object('success', false, 'error', 'end_date cannot be before start_date');
  END IF;

  SELECT duration_minutes, title
  INTO v_service_duration, v_service_title
  FROM services
  WHERE id = p_service_id
    AND tenant_id = p_tenant_id
    AND is_active = TRUE;

  IF v_service_duration IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'Service not found or inactive');
  END IF;

  SELECT
    COALESCE(config->>'timezone', 'UTC'),
    COALESCE((config->>'workday_start')::TIME, '09:00'::TIME),
    COALESCE((config->>'workday_end')::TIME, '17:00'::TIME)
  INTO v_timezone, v_default_start, v_default_end
  FROM tenants
  WHERE id = p_tenant_id;

  IF v_timezone IS NULL THEN
    v_timezone := 'UTC';
  END IF;

  v_current_date := p_start_date;
  WHILE v_current_date <= p_end_date LOOP
    v_day_of_week := EXTRACT(DOW FROM v_current_date)::INTEGER;
    v_day_slots := '[]'::jsonb;
    v_had_window := FALSE;

    v_has_date_override := EXISTS (
      SELECT 1
      FROM availability
      WHERE tenant_id = p_tenant_id
        AND date = v_current_date
    );

    FOR r_avail IN
      SELECT start_time, end_time
      FROM availability
      WHERE tenant_id = p_tenant_id
        AND (
          (v_has_date_override AND date = v_current_date)
          OR
          (NOT v_has_date_override AND date IS NULL AND v_day_of_week = ANY(days))
        )
      ORDER BY start_time ASC
    LOOP
      v_had_window := TRUE;

      v_workday_start_tz := (v_current_date || ' ' || r_avail.start_time)::TIMESTAMP AT TIME ZONE v_timezone;
      v_workday_end_tz := (v_current_date || ' ' || r_avail.end_time)::TIMESTAMP AT TIME ZONE v_timezone;
      v_last_end := v_workday_start_tz;

      FOR r_app IN
        SELECT start_time, end_time
        FROM appointments
        WHERE tenant_id = p_tenant_id
          AND status <> 'CANCELLED'
          AND start_time < v_workday_end_tz
          AND end_time > v_workday_start_tz
        ORDER BY start_time
      LOOP
        IF r_app.start_time < v_workday_start_tz THEN
          v_last_end := GREATEST(v_last_end, LEAST(r_app.end_time, v_workday_end_tz));
          CONTINUE;
        END IF;

        IF r_app.start_time > v_last_end THEN
          v_gap_minutes := EXTRACT(EPOCH FROM (r_app.start_time - v_last_end)) / 60;
          IF v_gap_minutes >= v_service_duration THEN
            v_day_slots := v_day_slots || jsonb_build_object(
              'start_utc', to_char(v_last_end AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
              'end_utc', to_char(r_app.start_time AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
              'start_local', to_char(v_last_end AT TIME ZONE v_timezone, 'HH24:MI'),
              'end_local', to_char(r_app.start_time AT TIME ZONE v_timezone, 'HH24:MI'),
              'duration_minutes', v_gap_minutes
            );
          END IF;
        END IF;

        v_last_end := GREATEST(v_last_end, LEAST(r_app.end_time, v_workday_end_tz));
      END LOOP;

      IF v_workday_end_tz > v_last_end THEN
        v_gap_minutes := EXTRACT(EPOCH FROM (v_workday_end_tz - v_last_end)) / 60;
        IF v_gap_minutes >= v_service_duration THEN
          v_day_slots := v_day_slots || jsonb_build_object(
            'start_utc', to_char(v_last_end AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
            'end_utc', to_char(v_workday_end_tz AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
            'start_local', to_char(v_last_end AT TIME ZONE v_timezone, 'HH24:MI'),
            'end_local', to_char(v_workday_end_tz AT TIME ZONE v_timezone, 'HH24:MI'),
            'duration_minutes', v_gap_minutes
          );
        END IF;
      END IF;
    END LOOP;

    -- fallback: tenant default workday if no explicit availability window exists
    IF NOT v_had_window THEN
      v_workday_start_tz := (v_current_date || ' ' || v_default_start)::TIMESTAMP AT TIME ZONE v_timezone;
      v_workday_end_tz := (v_current_date || ' ' || v_default_end)::TIMESTAMP AT TIME ZONE v_timezone;
      v_last_end := v_workday_start_tz;

      FOR r_app IN
        SELECT start_time, end_time
        FROM appointments
        WHERE tenant_id = p_tenant_id
          AND status <> 'CANCELLED'
          AND start_time < v_workday_end_tz
          AND end_time > v_workday_start_tz
        ORDER BY start_time
      LOOP
        IF r_app.start_time < v_workday_start_tz THEN
          v_last_end := GREATEST(v_last_end, LEAST(r_app.end_time, v_workday_end_tz));
          CONTINUE;
        END IF;

        IF r_app.start_time > v_last_end THEN
          v_gap_minutes := EXTRACT(EPOCH FROM (r_app.start_time - v_last_end)) / 60;
          IF v_gap_minutes >= v_service_duration THEN
            v_day_slots := v_day_slots || jsonb_build_object(
              'start_utc', to_char(v_last_end AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
              'end_utc', to_char(r_app.start_time AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
              'start_local', to_char(v_last_end AT TIME ZONE v_timezone, 'HH24:MI'),
              'end_local', to_char(r_app.start_time AT TIME ZONE v_timezone, 'HH24:MI'),
              'duration_minutes', v_gap_minutes
            );
          END IF;
        END IF;

        v_last_end := GREATEST(v_last_end, LEAST(r_app.end_time, v_workday_end_tz));
      END LOOP;

      IF v_workday_end_tz > v_last_end THEN
        v_gap_minutes := EXTRACT(EPOCH FROM (v_workday_end_tz - v_last_end)) / 60;
        IF v_gap_minutes >= v_service_duration THEN
          v_day_slots := v_day_slots || jsonb_build_object(
            'start_utc', to_char(v_last_end AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
            'end_utc', to_char(v_workday_end_tz AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
            'start_local', to_char(v_last_end AT TIME ZONE v_timezone, 'HH24:MI'),
            'end_local', to_char(v_workday_end_tz AT TIME ZONE v_timezone, 'HH24:MI'),
            'duration_minutes', v_gap_minutes
          );
        END IF;
      END IF;
    END IF;

    IF jsonb_array_length(v_day_slots) > 0 THEN
      v_available_slots := v_available_slots || jsonb_build_object(
        'date', v_current_date::TEXT,
        'day_name', trim(to_char(v_current_date, 'Day')),
        'slots', v_day_slots
      );
    END IF;

    v_current_date := v_current_date + INTERVAL '1 day';
  END LOOP;

  RETURN jsonb_build_object(
    'success', TRUE,
    'service_id', p_service_id,
    'service_title', v_service_title,
    'service_duration_minutes', v_service_duration,
    'timezone', v_timezone,
    'date_range', jsonb_build_object('start', p_start_date, 'end', p_end_date),
    'available_slots', v_available_slots,
    'total_days_checked', (p_end_date - p_start_date + 1)::INTEGER
  );
END;
$$;

CREATE OR REPLACE FUNCTION get_llm_friendly_availability(
  p_tenant_id UUID,
  p_service_id UUID,
  p_start_date DATE,
  p_end_date DATE DEFAULT NULL
)
RETURNS TEXT
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_result JSONB;
  v_day JSONB;
  v_slot JSONB;
  v_out TEXT := '';
BEGIN
  v_result := check_availability(p_tenant_id, p_service_id, p_start_date, p_end_date);

  IF COALESCE((v_result->>'success')::BOOLEAN, FALSE) = FALSE THEN
    RETURN COALESCE(v_result->>'error', 'Bilinmeyen hata.');
  END IF;

  IF jsonb_array_length(v_result->'available_slots') = 0 THEN
    RETURN 'Seçilen tarih aralığında müsait randevu bulunamadı.';
  END IF;

  FOR v_day IN SELECT * FROM jsonb_array_elements(v_result->'available_slots') LOOP
    v_out := v_out || trim(v_day->>'day_name') || ' (' || (v_day->>'date') || '): ';
    FOR v_slot IN SELECT * FROM jsonb_array_elements(v_day->'slots') LOOP
      v_out := v_out || (v_slot->>'start_local') || '-' || (v_slot->>'end_local') || ', ';
    END LOOP;
    v_out := rtrim(v_out, ', ') || '. ';
  END LOOP;

  RETURN rtrim(v_out);
END;
$$;

CREATE OR REPLACE FUNCTION create_appointment_from_call(
  p_tenant_id UUID,
  p_call_id UUID,
  p_service_id UUID,
  p_start_time TIMESTAMPTZ,
  p_customer_phone TEXT,
  p_customer_name TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_customer_id UUID;
  v_service_duration INTEGER;
  v_service_title TEXT;
  v_end_time TIMESTAMPTZ;
  v_appointment_id UUID;
  v_normalized_phone TEXT;
BEGIN
  v_normalized_phone := normalize_phone_to_e164(p_customer_phone);

  SELECT id INTO v_customer_id
  FROM customers
  WHERE tenant_id = p_tenant_id
    AND phone_number = v_normalized_phone;

  IF v_customer_id IS NULL THEN
    INSERT INTO customers (tenant_id, phone_number, full_name)
    VALUES (p_tenant_id, v_normalized_phone, p_customer_name)
    RETURNING id INTO v_customer_id;
  ELSIF p_customer_name IS NOT NULL THEN
    UPDATE customers
    SET full_name = p_customer_name,
        updated_at = NOW()
    WHERE id = v_customer_id;
  END IF;

  SELECT duration_minutes, title
  INTO v_service_duration, v_service_title
  FROM services
  WHERE id = p_service_id
    AND tenant_id = p_tenant_id
    AND is_active = TRUE;

  IF v_service_duration IS NULL THEN
    RETURN jsonb_build_object('success', FALSE, 'error', 'Service not found');
  END IF;

  v_end_time := p_start_time + (v_service_duration || ' minutes')::INTERVAL;

  IF NOT is_time_slot_available(p_tenant_id, p_start_time, v_end_time) THEN
    RETURN jsonb_build_object('success', FALSE, 'error', 'Time slot is already booked');
  END IF;

  BEGIN
    INSERT INTO appointments (
      tenant_id, customer_id, service_id, title,
      start_time, end_time, customer_name, customer_phone, status
    ) VALUES (
      p_tenant_id, v_customer_id, p_service_id, v_service_title,
      p_start_time, v_end_time, p_customer_name, v_normalized_phone, 'ACCEPTED'
    )
    RETURNING id INTO v_appointment_id;
  EXCEPTION
    WHEN exclusion_violation THEN
      RETURN jsonb_build_object('success', FALSE, 'error', 'Time slot is already booked');
  END;

  UPDATE calls
  SET appointment_id = v_appointment_id,
      updated_at = NOW()
  WHERE id = p_call_id
    AND tenant_id = p_tenant_id;

  RETURN jsonb_build_object(
    'success', TRUE,
    'appointment_id', v_appointment_id,
    'customer_id', v_customer_id,
    'start_time', p_start_time,
    'end_time', v_end_time
  );
END;
$$;

-- =========================
-- 9) Function permissions
-- =========================
REVOKE ALL ON FUNCTION check_availability(UUID, UUID, DATE, DATE) FROM PUBLIC;
REVOKE ALL ON FUNCTION get_llm_friendly_availability(UUID, UUID, DATE, DATE) FROM PUBLIC;
REVOKE ALL ON FUNCTION create_appointment_from_call(UUID, UUID, UUID, TIMESTAMPTZ, TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION is_time_slot_available(UUID, TIMESTAMPTZ, TIMESTAMPTZ, UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION get_current_tenant_id() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION check_availability(UUID, UUID, DATE, DATE) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_llm_friendly_availability(UUID, UUID, DATE, DATE) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION create_appointment_from_call(UUID, UUID, UUID, TIMESTAMPTZ, TEXT, TEXT) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION is_time_slot_available(UUID, TIMESTAMPTZ, TIMESTAMPTZ, UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_current_tenant_id() TO authenticated, service_role;

-- =========================
-- 10) Realtime publication
-- =========================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    CREATE PUBLICATION supabase_realtime;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND tablename = 'appointments'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE appointments;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND tablename = 'calls'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE calls;
  END IF;
END $$;

-- ==========================================================================
-- End
-- ==========================================================================
