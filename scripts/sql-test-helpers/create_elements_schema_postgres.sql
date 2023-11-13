CREATE TABLE data_source (
    id                  VARCHAR PRIMARY KEY,
    url                 VARCHAR,
    version             VARCHAR,
    date_created        TIMESTAMPTZ,
    date_modified       TIMESTAMPTZ,
    date_processed      TIMESTAMPTZ,
    permissions_data    VARCHAR,
    record_locator      VARCHAR
);

CREATE TABLE coordinates (
    id              VARCHAR PRIMARY KEY,
    system          VARCHAR,
    layout_width    DECIMAL,
    layout_height   DECIMAL,
    points          VARCHAR
);

CREATE TABLE metadata (
    id                          VARCHAR(36) PRIMARY KEY,
    category_depth              INT,
    parent_id                   VARCHAR,
    attached_to_filename        VARCHAR,
    filetype                    VARCHAR,
    last_modified               TIMESTAMPTZ,
    file_directory              VARCHAR,
    filename                    VARCHAR,
    page_number                 VARCHAR,
    links                       VARCHAR [],
    url                         VARCHAR,
    link_urls                   VARCHAR [],
    link_texts                  VARCHAR [],
    sent_from                   VARCHAR [],
    sent_to                     VARCHAR [],
    subject                     VARCHAR,
    section                     VARCHAR,
    header_footer_type          VARCHAR,
    emphasized_text_contents    VARCHAR [],
    text_as_html                VARCHAR,
    regex_metadata              VARCHAR,
    detection_class_prob        DECIMAL,
    data_source_id              VARCHAR references data_source(id),
    coordinates_id              VARCHAR references coordinates(id)
);

CREATE TABLE elements (
    id          VARCHAR(36) PRIMARY KEY,
    element_id  VARCHAR(36),
    text        VARCHAR,
    embeddings  DECIMAL [],
    type        VARCHAR,
    metadata_id VARCHAR(36) REFERENCES metadata(id)
);
