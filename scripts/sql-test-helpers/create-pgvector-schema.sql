CREATE EXTENSION vector;

CREATE TABLE coordinates (
    id UUID PRIMARY KEY,
    system VARCHAR,
    layout_width DECIMAL,
    layout_height DECIMAL,
    points TEXT
);

CREATE TABLE data_source (
    id UUID PRIMARY KEY,
    url TEXT,
    version VARCHAR,
    date_created TIMESTAMPTZ,
    date_modified TIMESTAMPTZ,
    date_processed TIMESTAMPTZ,
    permissions_data TEXT,
    record_locator TEXT
);

CREATE TABLE metadata (
    id UUID PRIMARY KEY,
    category_depth INTEGER,
    parent_id VARCHAR,
    attached_filename VARCHAR,
    filetype VARCHAR,
    last_modified TIMESTAMPTZ,
    file_directory VARCHAR,
    filename VARCHAR,
    languages TEXT,
    page_number VARCHAR,
    links TEXT,
    page_name VARCHAR,
    url TEXT,
    link_urls TEXT,
    link_texts TEXT,
    sent_from TEXT,
    sent_to TEXT,
    subject VARCHAR,
    section VARCHAR,
    header_footer_type VARCHAR,
    emphasized_text_contents TEXT,
    emphasized_text_tags TEXT,
    text_as_html TEXT,
    regex_metadata TEXT,
    detection_class_prob DECIMAL,
    data_source_id UUID REFERENCES data_source(id),
    coordinates_id UUID REFERENCES coordinates(id)
);

CREATE TABLE elements (
    id UUID PRIMARY KEY,
    element_id VARCHAR,
    text TEXT,
    embeddings vector(384),
    type VARCHAR,
    metadata_id UUID REFERENCES metadata(id)
);
