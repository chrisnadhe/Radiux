-- ===========================================================================
-- Skema tabel inti FreeRADIUS (standar rlm_sql untuk PostgreSQL)
-- JANGAN UBAH nama tabel atau kolom yang sudah ada di sini!
-- Lihat AGENT.md rule #1 — perubahan akan merusak integrasi FreeRADIUS.
--
-- Sumber referensi:
--   /etc/freeradius/3.0/mods-config/sql/main/postgresql/schema.sql
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- radcheck — atribut authentication/authorization per user
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radcheck (
    id         BIGSERIAL PRIMARY KEY,
    username   VARCHAR(64) NOT NULL DEFAULT '',
    attribute  VARCHAR(64) NOT NULL DEFAULT '',
    op         VARCHAR(2)  NOT NULL DEFAULT '==',
    value      VARCHAR(253) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS radcheck_username ON radcheck (username, attribute);

-- ---------------------------------------------------------------------------
-- radreply — atribut reply per user (dikirim ke NAS setelah auth berhasil)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radreply (
    id         BIGSERIAL PRIMARY KEY,
    username   VARCHAR(64) NOT NULL DEFAULT '',
    attribute  VARCHAR(64) NOT NULL DEFAULT '',
    op         VARCHAR(2)  NOT NULL DEFAULT '=',
    value      VARCHAR(253) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS radreply_username ON radreply (username, attribute);

-- ---------------------------------------------------------------------------
-- radgroupcheck — atribut check per grup/paket
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radgroupcheck (
    id         BIGSERIAL PRIMARY KEY,
    groupname  VARCHAR(64) NOT NULL DEFAULT '',
    attribute  VARCHAR(64) NOT NULL DEFAULT '',
    op         VARCHAR(2)  NOT NULL DEFAULT '==',
    value      VARCHAR(253) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS radgroupcheck_groupname ON radgroupcheck (groupname, attribute);

-- ---------------------------------------------------------------------------
-- radgroupreply — atribut reply per grup/paket
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radgroupreply (
    id         BIGSERIAL PRIMARY KEY,
    groupname  VARCHAR(64) NOT NULL DEFAULT '',
    attribute  VARCHAR(64) NOT NULL DEFAULT '',
    op         VARCHAR(2)  NOT NULL DEFAULT '=',
    value      VARCHAR(253) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS radgroupreply_groupname ON radgroupreply (groupname, attribute);

-- ---------------------------------------------------------------------------
-- radusergroup — mapping user ke grup/paket (dengan priority)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radusergroup (
    id         BIGSERIAL PRIMARY KEY,
    username   VARCHAR(64) NOT NULL DEFAULT '',
    groupname  VARCHAR(64) NOT NULL DEFAULT '',
    priority   INTEGER     NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS radusergroup_username ON radusergroup (username);

-- ---------------------------------------------------------------------------
-- radacct — accounting records (sesi, durasi, byte in/out)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radacct (
    radacctid              BIGSERIAL PRIMARY KEY,
    acctsessionid          VARCHAR(64)  NOT NULL DEFAULT '',
    acctuniqueid           VARCHAR(32)  NOT NULL DEFAULT '' UNIQUE,
    username               VARCHAR(64)  NOT NULL DEFAULT '',
    groupname              VARCHAR(64)  NOT NULL DEFAULT '',
    realm                  VARCHAR(64)            DEFAULT '',
    nasipaddress           INET         NOT NULL,
    nasportid              VARCHAR(15)            DEFAULT NULL,
    nasporttype            VARCHAR(32)            DEFAULT NULL,
    acctstarttime          TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    acctupdatetime         TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    acctstoptime           TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    acctinterval           BIGINT                 DEFAULT NULL,
    acctsessiontime        BIGINT       NOT NULL DEFAULT 0,
    acctauthentic          VARCHAR(32)            DEFAULT NULL,
    connectinfo_start      VARCHAR(50)            DEFAULT NULL,
    connectinfo_stop       VARCHAR(50)            DEFAULT NULL,
    acctinputoctets        BIGINT       NOT NULL DEFAULT 0,
    acctoutputoctets       BIGINT       NOT NULL DEFAULT 0,
    calledstationid        VARCHAR(50)  NOT NULL DEFAULT '',
    callingstationid       VARCHAR(50)  NOT NULL DEFAULT '',
    acctterminatecause     VARCHAR(32)  NOT NULL DEFAULT '',
    servicetype            VARCHAR(32)            DEFAULT NULL,
    framedprotocol         VARCHAR(32)            DEFAULT NULL,
    framedipaddress        INET                   DEFAULT NULL,
    framedipv6address      INET                   DEFAULT NULL,
    framedipv6prefix       INET                   DEFAULT NULL,
    framedinterfaceid      VARCHAR(44)            DEFAULT NULL,
    delegatedipv6prefix    INET                   DEFAULT NULL,
    class                  VARCHAR(64)            DEFAULT NULL,
    proto                  VARCHAR(6)             DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS radacct_username        ON radacct (username);
CREATE INDEX IF NOT EXISTS radacct_nasipaddress    ON radacct (nasipaddress);
CREATE INDEX IF NOT EXISTS radacct_acctsessionid   ON radacct (acctsessionid);
CREATE INDEX IF NOT EXISTS radacct_acctstarttime   ON radacct (acctstarttime);
CREATE INDEX IF NOT EXISTS radacct_acctstoptime    ON radacct (acctstoptime);
CREATE INDEX IF NOT EXISTS radacct_acctuniqueid    ON radacct (acctuniqueid);
CREATE INDEX IF NOT EXISTS radacct_framedipaddress ON radacct (framedipaddress);

-- ---------------------------------------------------------------------------
-- radpostauth — log percobaan autentikasi (sukses & gagal)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radpostauth (
    id         BIGSERIAL PRIMARY KEY,
    username   VARCHAR(64)  NOT NULL,
    pass       VARCHAR(64)  NOT NULL,
    reply      VARCHAR(32)  NOT NULL,
    nasname    VARCHAR(128) NOT NULL DEFAULT '',
    nasportid  VARCHAR(15)  NOT NULL DEFAULT '',
    authdate   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    class      VARCHAR(64)  DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS radpostauth_username ON radpostauth (username);
CREATE INDEX IF NOT EXISTS radpostauth_authdate ON radpostauth (authdate);

-- ---------------------------------------------------------------------------
-- nas — daftar NAS yang dikenal FreeRADIUS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nas (
    id          BIGSERIAL PRIMARY KEY,
    nasname     VARCHAR(128) NOT NULL,
    shortname   VARCHAR(32)  NOT NULL,
    type        VARCHAR(30)  NOT NULL DEFAULT 'other',
    ports       INTEGER               DEFAULT NULL,
    secret      VARCHAR(60)  NOT NULL DEFAULT 'secret',
    server      VARCHAR(64)           DEFAULT NULL,
    community   VARCHAR(50)           DEFAULT NULL,
    description VARCHAR(200)          DEFAULT 'RADIUS Client'
);

CREATE UNIQUE INDEX IF NOT EXISTS nas_nasname ON nas (nasname);
