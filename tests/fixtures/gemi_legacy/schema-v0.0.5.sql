-- Schema created by GEMI v0.0.5's own SQLModel.metadata.create_all (backend/app/models),
-- captured for importer tests. v0.0.4's schema is identical to v0.0.3's.
CREATE TABLE appsetting (
	"key" VARCHAR(255) NOT NULL, 
	value VARCHAR(4096) NOT NULL, 
	PRIMARY KEY ("key")
);
CREATE TABLE user (
	email VARCHAR(255) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	is_superuser BOOLEAN NOT NULL, 
	full_name VARCHAR(255), 
	id CHAR(32) NOT NULL, 
	hashed_password VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_user_email ON user (email);
CREATE TABLE plotrecord (
	id CHAR(32) NOT NULL, 
	trait_record_id CHAR(32) NOT NULL, 
	run_id CHAR(32) NOT NULL, 
	pipeline_id VARCHAR(100) NOT NULL, 
	pipeline_type VARCHAR(20) NOT NULL, 
	pipeline_name VARCHAR(255) NOT NULL, 
	workspace_id VARCHAR(100) NOT NULL, 
	workspace_name VARCHAR(255) NOT NULL, 
	date VARCHAR(50) NOT NULL, 
	experiment VARCHAR(255) NOT NULL, 
	location VARCHAR(255) NOT NULL, 
	population VARCHAR(255) NOT NULL, 
	platform VARCHAR(255) NOT NULL, 
	sensor VARCHAR(255) NOT NULL, 
	trait_record_version INTEGER NOT NULL, 
	ortho_version INTEGER, 
	ortho_name VARCHAR(255), 
	stitch_version INTEGER, 
	stitch_name VARCHAR(255), 
	boundary_version INTEGER, 
	boundary_name VARCHAR(255), 
	plot_id VARCHAR(255) NOT NULL, 
	accession VARCHAR(255), 
	col VARCHAR(100), 
	"row" VARCHAR(100), 
	geometry_wkt VARCHAR, 
	traits JSON, 
	extra_properties JSON, 
	image_rel_path VARCHAR(1000), 
	detection_count INTEGER, 
	detection_class_summary JSON, 
	created_at VARCHAR NOT NULL, 
	updated_at VARCHAR, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_plotrecord_trait_plot UNIQUE (trait_record_id, plot_id)
);
CREATE INDEX ix_plotrecord_trait_record_id ON plotrecord (trait_record_id);
CREATE INDEX ix_plotrecord_accession ON plotrecord (accession);
CREATE INDEX ix_plotrecord_plot_id ON plotrecord (plot_id);
CREATE INDEX ix_plotrecord_run_id ON plotrecord (run_id);
CREATE TABLE referencedataset (
	id CHAR(32) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	experiment VARCHAR(255) NOT NULL, 
	location VARCHAR(255) NOT NULL, 
	population VARCHAR(255) NOT NULL, 
	date VARCHAR(50) NOT NULL, 
	column_mapping JSON, 
	plot_count INTEGER NOT NULL, 
	trait_columns JSON, 
	original_filename VARCHAR(500), 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE fileupload (
	data_type VARCHAR(100) NOT NULL, 
	experiment VARCHAR(255) NOT NULL, 
	location VARCHAR(255) NOT NULL, 
	population VARCHAR(255) NOT NULL, 
	date VARCHAR(50) NOT NULL, 
	platform VARCHAR(255), 
	sensor VARCHAR(255), 
	storage_path VARCHAR(1000) NOT NULL, 
	msgs_synced_path VARCHAR(1000), 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	original_filename VARCHAR(500), 
	file_count INTEGER NOT NULL, 
	file_size_bytes INTEGER, 
	status VARCHAR(50) NOT NULL, 
	notes VARCHAR(1000), 
	created_at VARCHAR NOT NULL, 
	updated_at VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES user (id) ON DELETE CASCADE
);
CREATE TABLE item (
	title VARCHAR(255) NOT NULL, 
	description VARCHAR(255), 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES user (id) ON DELETE CASCADE
);
CREATE TABLE workspace (
	name VARCHAR(255) NOT NULL, 
	description VARCHAR(1000), 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES user (id) ON DELETE CASCADE
);
CREATE TABLE referenceplot (
	id CHAR(32) NOT NULL, 
	dataset_id CHAR(32) NOT NULL, 
	plot_id VARCHAR(255) NOT NULL, 
	col VARCHAR(100), 
	"row" VARCHAR(100), 
	accession VARCHAR(255), 
	traits JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dataset_id) REFERENCES referencedataset (id) ON DELETE CASCADE
);
CREATE INDEX ix_referenceplot_dataset_id ON referenceplot (dataset_id);
CREATE INDEX ix_referenceplot_plot_id ON referenceplot (plot_id);
CREATE TABLE workspacereferencedataset (
	workspace_id CHAR(32) NOT NULL, 
	dataset_id CHAR(32) NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (workspace_id, dataset_id), 
	CONSTRAINT uq_workspace_refdataset UNIQUE (workspace_id, dataset_id), 
	FOREIGN KEY(workspace_id) REFERENCES workspace (id) ON DELETE CASCADE, 
	FOREIGN KEY(dataset_id) REFERENCES referencedataset (id) ON DELETE CASCADE
);
CREATE TABLE pipeline (
	name VARCHAR(255) NOT NULL, 
	type VARCHAR(50) NOT NULL, 
	config JSON, 
	id CHAR(32) NOT NULL, 
	workspace_id CHAR(32) NOT NULL, 
	created_at VARCHAR NOT NULL, 
	updated_at VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspace (id) ON DELETE CASCADE
);
CREATE TABLE pipelinerun (
	date VARCHAR(50) NOT NULL, 
	experiment VARCHAR(255) NOT NULL, 
	location VARCHAR(255) NOT NULL, 
	population VARCHAR(255) NOT NULL, 
	platform VARCHAR(255) NOT NULL, 
	sensor VARCHAR(255) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	current_step VARCHAR(100), 
	steps_completed JSON, 
	outputs JSON, 
	error VARCHAR(2000), 
	id CHAR(32) NOT NULL, 
	pipeline_id CHAR(32) NOT NULL, 
	file_upload_id CHAR(32), 
	created_at VARCHAR NOT NULL, 
	completed_at VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pipeline_id) REFERENCES pipeline (id) ON DELETE CASCADE, 
	FOREIGN KEY(file_upload_id) REFERENCES fileupload (id) ON DELETE SET NULL
);
CREATE TABLE traitrecord (
	id CHAR(32) NOT NULL, 
	run_id CHAR(32) NOT NULL, 
	geojson_path VARCHAR(1000) NOT NULL, 
	ortho_version INTEGER, 
	ortho_name VARCHAR(255), 
	boundary_version INTEGER, 
	boundary_name VARCHAR(255), 
	version INTEGER NOT NULL, 
	plot_count INTEGER NOT NULL, 
	trait_columns JSON, 
	vf_avg FLOAT, 
	height_avg FLOAT, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES pipelinerun (id) ON DELETE CASCADE
);
