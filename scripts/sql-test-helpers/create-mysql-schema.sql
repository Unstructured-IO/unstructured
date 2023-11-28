CREATE TABLE coordinates (
    id VARCHAR(36) PRIMARY KEY,
    `system` VARCHAR(255),
    layout_width DECIMAL,
    layout_height DECIMAL,
    points TEXT
);

CREATE TABLE data_source (
    id VARCHAR(36) PRIMARY KEY,
    `url` TEXT,
    `version` VARCHAR(255),
    date_created DATETIME,
    date_modified DATETIME,
    date_processed DATETIME,
    permissions_data TEXT,
    record_locator TEXT
);

CREATE TABLE metadata (
    id VARCHAR(36) PRIMARY KEY,
    category_depth INT,
    parent_id VARCHAR(255),
    attached_filename TEXT,
    filetype VARCHAR(255),
    last_modified DATETIME,
    file_directory TEXT,
    `filename` TEXT,
    languages JSON,
    page_number VARCHAR(255),
    links TEXT,
    page_name VARCHAR(255),
    `url` TEXT,
    link_urls JSON,
    link_texts JSON,
    sent_from JSON,
    sent_to JSON,
    `subject` TEXT,
    section TEXT,
    header_footer_type VARCHAR(255),
    emphasized_text_contents JSON,
    emphasized_text_tags JSON,
    text_as_html TEXT,
    regex_metadata TEXT,
    detection_class_prob DECIMAL,
    data_source_id VARCHAR(36),
    coordinates_id VARCHAR(36),
    CONSTRAINT fk_data_source FOREIGN KEY (data_source_id) REFERENCES data_source(id),
    CONSTRAINT fk_coordinates FOREIGN KEY (coordinates_id) REFERENCES coordinates(id)
);

CREATE TABLE elements (
    id VARCHAR(36) PRIMARY KEY,
    element_id VARCHAR(255),
    text TEXT,
    embeddings JSON,
    type VARCHAR(255),
    metadata_id VARCHAR(36),
    CONSTRAINT fk_datasource FOREIGN KEY (metadata_id) REFERENCES metadata(id)
);
