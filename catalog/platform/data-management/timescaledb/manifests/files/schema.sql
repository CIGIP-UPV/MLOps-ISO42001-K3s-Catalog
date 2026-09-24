-- =============================================================================
-- Schema of the platform data stock (TimescaleDB), idempotent.
-- Applied by the schema Job of this chart on every install and upgrade, so an
-- existing installation receives the objects added by later versions. The
-- init script (templates/configmap-init.yaml) creates the first version of
-- the schema when the database starts for the first time.
-- psql variables: sync_pw, ml_pw, grafana_pw, feedback_pw.
-- ISO/IEC 42001: B.6.2.6.1, B.6.2.6.3, B.6.1.3.3, B.6.2.8.1
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Consolidated edge sensor readings (target of edge-postgresql-sync).
-- (site_id, source_id, time) makes each batch idempotent.
CREATE TABLE IF NOT EXISTS sensor_readings (
  time        TIMESTAMPTZ NOT NULL,
  site_id     TEXT NOT NULL,
  machine_id  TEXT NOT NULL,
  signal_name TEXT NOT NULL,
  value       DOUBLE PRECISION,
  source_id   BIGINT NOT NULL,
  batch_id    BIGINT,
  UNIQUE (site_id, source_id, time)
);
SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);

-- Consolidated edge predictions.
CREATE TABLE IF NOT EXISTS predictions (
  time          TIMESTAMPTZ NOT NULL,
  site_id       TEXT NOT NULL,
  machine_id    TEXT NOT NULL,
  model_name    TEXT,
  model_version TEXT NOT NULL,
  score         DOUBLE PRECISION,
  label         TEXT,
  source_id     BIGINT NOT NULL,
  batch_id      BIGINT,
  UNIQUE (site_id, source_id, time)
);
SELECT create_hypertable('predictions', 'time', if_not_exists => TRUE);

-- Goal-oriented KPIs (B.6.2.6.3).
CREATE TABLE IF NOT EXISTS oee_kpis (
  time         TIMESTAMPTZ NOT NULL,
  machine_id   TEXT NOT NULL,
  oee          DOUBLE PRECISION,
  availability DOUBLE PRECISION,
  performance  DOUBLE PRECISION,
  quality      DOUBLE PRECISION
);
SELECT create_hypertable('oee_kpis', 'time', if_not_exists => TRUE);

-- Provenance of every consolidation batch (edge -> platform data flow).
CREATE TABLE IF NOT EXISTS consolidation_batches (
  id           BIGSERIAL PRIMARY KEY,
  site_id      TEXT NOT NULL,
  source_table TEXT NOT NULL,
  started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at  TIMESTAMPTZ,
  from_id      BIGINT,
  to_id        BIGINT,
  rows_read    BIGINT DEFAULT 0,
  rows_written BIGINT DEFAULT 0,
  status       TEXT NOT NULL,
  message      TEXT
);

-- Drift checks and retraining recommendations (CMP-14).
CREATE TABLE IF NOT EXISTS retraining_recommendations (
  id               BIGSERIAL PRIMARY KEY,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  model_name       TEXT NOT NULL,
  model_version    TEXT,
  reference_window TEXT,
  current_window   TEXT,
  drift_share      DOUBLE PRECISION,
  drifted_columns  TEXT[],
  threshold        DOUBLE PRECISION,
  recommended      BOOLEAN NOT NULL,
  action           TEXT,
  report_uri       TEXT
);

-- Input features of every prediction (consolidated from the edge), so that
-- operator feedback can be used as labels by the training job.
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS features JSONB;

-- Operator feedback on predictions (CMP-12, B.6.1.3.3), written by the
-- feedback interface. Append-only: a new verdict adds a row; the latest row
-- of an operator for a prediction is the one in force.
CREATE TABLE IF NOT EXISTS operator_feedback (
  id                   BIGSERIAL PRIMARY KEY,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  site_id              TEXT NOT NULL,
  prediction_source_id BIGINT NOT NULL,
  prediction_time      TIMESTAMPTZ NOT NULL,
  machine_id           TEXT NOT NULL,
  model_name           TEXT,
  model_version        TEXT NOT NULL,
  predicted_label      TEXT NOT NULL,
  verdict              TEXT NOT NULL CHECK (verdict IN ('correct', 'incorrect', 'uncertain')),
  corrected_label      TEXT CHECK (corrected_label IN ('normal', 'anomaly')),
  comment              TEXT CHECK (char_length(comment) <= 1000),
  operator             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_prediction
  ON operator_feedback (site_id, prediction_source_id, prediction_time);
CREATE INDEX IF NOT EXISTS idx_feedback_version ON operator_feedback (model_version, created_at DESC);

-- Least-privilege roles; passwords are (re)set from the chart Secret.
SELECT format('CREATE ROLE %I LOGIN', r) FROM unnest(ARRAY['sync', 'ml', 'grafana', 'feedback']) AS r
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) \gexec
SELECT format('ALTER ROLE sync PASSWORD %L', :'sync_pw') \gexec
SELECT format('ALTER ROLE ml PASSWORD %L', :'ml_pw') \gexec
SELECT format('ALTER ROLE grafana PASSWORD %L', :'grafana_pw') \gexec
SELECT format('ALTER ROLE feedback PASSWORD %L', :'feedback_pw') \gexec

GRANT SELECT, INSERT ON sensor_readings, predictions TO sync;
GRANT SELECT, INSERT, UPDATE ON consolidation_batches TO sync;
GRANT USAGE ON SEQUENCE consolidation_batches_id_seq TO sync;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ml, grafana;
GRANT INSERT ON retraining_recommendations TO ml;
GRANT USAGE ON SEQUENCE retraining_recommendations_id_seq TO ml;
GRANT SELECT ON predictions TO feedback;
GRANT SELECT, INSERT ON operator_feedback TO feedback;
GRANT USAGE ON SEQUENCE operator_feedback_id_seq TO feedback;
