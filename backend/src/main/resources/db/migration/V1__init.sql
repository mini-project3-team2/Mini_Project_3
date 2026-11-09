-- AskNote 초기 스키마 (docs/3.데이터베이스설계서.md v0.2 기준)
-- JPA 는 ddl-auto: validate 로 검증만 하고, 스키마 변경은 새 V{n}__*.sql 로만 한다

CREATE TABLE members (
    id                 BIGINT       NOT NULL AUTO_INCREMENT,
    uuid               CHAR(36)     NOT NULL,
    email              VARCHAR(100) NOT NULL,
    password           VARCHAR(255) NOT NULL,
    role               VARCHAR(20)  NOT NULL DEFAULT 'MEMBER',
    failed_login_count INT          NOT NULL DEFAULT 0,
    locked_until       DATETIME(6)  NULL,
    created_at         DATETIME(6)  NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uk_members_uuid  UNIQUE (uuid),
    CONSTRAINT uk_members_email UNIQUE (email)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

CREATE TABLE refresh_tokens (
    id         BIGINT      NOT NULL AUTO_INCREMENT,
    member_id  BIGINT      NOT NULL,
    token_hash CHAR(64)    NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uk_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_refresh_tokens_member FOREIGN KEY (member_id) REFERENCES members (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

CREATE INDEX idx_refresh_member ON refresh_tokens (member_id);

CREATE TABLE documents (
    id                BIGINT       NOT NULL AUTO_INCREMENT,
    member_id         BIGINT       NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size         BIGINT       NOT NULL,
    status            VARCHAR(20)  NOT NULL DEFAULT 'INDEXING',
    created_at        DATETIME(6)  NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_documents_member FOREIGN KEY (member_id) REFERENCES members (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

CREATE INDEX idx_documents_member_created ON documents (member_id, created_at);
CREATE INDEX idx_documents_member_status  ON documents (member_id, status);

CREATE TABLE chat_histories (
    id         BIGINT        NOT NULL AUTO_INCREMENT,
    member_id  BIGINT        NOT NULL,
    question   VARCHAR(1000) NOT NULL,
    answer     TEXT          NOT NULL,
    sources    LONGTEXT      NULL CHECK (sources IS NULL OR JSON_VALID(sources)),
    feedback   VARCHAR(20)   NULL,
    created_at DATETIME(6)   NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_chat_histories_member FOREIGN KEY (member_id) REFERENCES members (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

CREATE INDEX idx_chat_member_created ON chat_histories (member_id, created_at);
