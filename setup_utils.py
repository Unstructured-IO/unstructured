from pathlib import Path
from typing import List, Union

current_dir = Path(__file__).parent.absolute()
requirements_dir = current_dir / "requirements"
ingest_requirements_dir = requirements_dir / "ingest"


def load_requirements(file: Union[str, Path]) -> List[str]:
    path = file if isinstance(file, Path) else Path(file)
    requirements: List[str] = []
    if not path.is_file():
        raise FileNotFoundError(f"path does not point to a valid file: {path}")
    file_dir = path.parent.resolve()
    with open(file, encoding="utf-8") as f:
        raw = f.read().splitlines()
        requirements.extend([r for r in raw if not r.startswith("#") and not r.startswith("-")])
        recursive_reqs = [r for r in raw if r.startswith("-r")]
    for recursive_req in recursive_reqs:
        file_spec = recursive_req.split()[-1]
        file_path = Path(file_dir) / file_spec
        requirements.extend(load_requirements(file=file_path.resolve()))
    # Remove duplicates and any blank entries
    return list({r for r in requirements if r})


def get_base_reqs() -> List[str]:
    file = requirements_dir / "base.in"
    return load_requirements(file)


def get_doc_reqs() -> dict[str, List[str]]:
    return {
        "csv": load_requirements(requirements_dir / "extra-csv.in"),
        "doc": load_requirements(requirements_dir / "extra-docx.in"),
        "docx": load_requirements(requirements_dir / "extra-docx.in"),
        "epub": load_requirements(requirements_dir / "extra-epub.in"),
        "image": load_requirements(requirements_dir / "extra-pdf-image.in"),
        "markdown": load_requirements(requirements_dir / "extra-markdown.in"),
        "msg": load_requirements(requirements_dir / "extra-msg.in"),
        "odt": load_requirements(requirements_dir / "extra-odt.in"),
        "org": load_requirements(requirements_dir / "extra-pandoc.in"),
        "pdf": load_requirements(requirements_dir / "extra-pdf-image.in"),
        "ppt": load_requirements(requirements_dir / "extra-pptx.in"),
        "pptx": load_requirements(requirements_dir / "extra-pptx.in"),
        "rtf": load_requirements(requirements_dir / "extra-pandoc.in"),
        "rst": load_requirements(requirements_dir / "extra-pandoc.in"),
        "tsv": load_requirements(requirements_dir / "extra-csv.in"),
        "xlsx": load_requirements(requirements_dir / "extra-xlsx.in"),
    }


def get_all_doc_reqs() -> List[str]:
    reqs = []
    for req in get_doc_reqs().values():
        reqs.extend(req)
    return list(set(reqs))


def get_connector_reqs() -> dict[str, List[str]]:
    return {
        "airtable": load_requirements(ingest_requirements_dir / "airtable.in"),
        "astra": load_requirements(ingest_requirements_dir / "astra.in"),
        "azure": load_requirements(ingest_requirements_dir / "azure.in"),
        "azure-cognitive-search": load_requirements(
            ingest_requirements_dir / "azure-cognitive-search.in",
        ),
        "biomed": load_requirements(ingest_requirements_dir / "biomed.in"),
        "box": load_requirements(ingest_requirements_dir / "box.in"),
        "chroma": load_requirements(ingest_requirements_dir / "chroma.in"),
        "clarifai": load_requirements(ingest_requirements_dir / "clarifai.in"),
        "confluence": load_requirements(ingest_requirements_dir / "confluence.in"),
        "delta-table": load_requirements(ingest_requirements_dir / "delta-table.in"),
        "discord": load_requirements(ingest_requirements_dir / "discord.in"),
        "dropbox": load_requirements(ingest_requirements_dir / "dropbox.in"),
        "elasticsearch": load_requirements(ingest_requirements_dir / "elasticsearch.in"),
        "gcs": load_requirements(ingest_requirements_dir / "gcs.in"),
        "github": load_requirements(ingest_requirements_dir / "github.in"),
        "gitlab": load_requirements(ingest_requirements_dir / "gitlab.in"),
        "google-drive": load_requirements(ingest_requirements_dir / "google-drive.in"),
        "hubspot": load_requirements(ingest_requirements_dir / "hubspot.in"),
        "jira": load_requirements(ingest_requirements_dir / "jira.in"),
        "mongodb": load_requirements(ingest_requirements_dir / "mongodb.in"),
        "notion": load_requirements(ingest_requirements_dir / "notion.in"),
        "onedrive": load_requirements(ingest_requirements_dir / "onedrive.in"),
        "opensearch": load_requirements(ingest_requirements_dir / "opensearch.in"),
        "outlook": load_requirements(ingest_requirements_dir / "outlook.in"),
        "pinecone": load_requirements(ingest_requirements_dir / "pinecone.in"),
        "postgres": load_requirements(ingest_requirements_dir / "postgres.in"),
        "qdrant": load_requirements(ingest_requirements_dir / "qdrant.in"),
        "reddit": load_requirements(ingest_requirements_dir / "reddit.in"),
        "s3": load_requirements(ingest_requirements_dir / "s3.in"),
        "sharepoint": load_requirements(ingest_requirements_dir / "sharepoint.in"),
        "salesforce": load_requirements(ingest_requirements_dir / "salesforce.in"),
        "sftp": load_requirements(ingest_requirements_dir / "sftp.in"),
        "slack": load_requirements(ingest_requirements_dir / "slack.in"),
        "wikipedia": load_requirements(ingest_requirements_dir / "wikipedia.in"),
        "weaviate": load_requirements(ingest_requirements_dir / "weaviate.in"),
        "embed-huggingface": load_requirements(ingest_requirements_dir / "embed-huggingface.in"),
        "embed-octoai": load_requirements(ingest_requirements_dir / "embed-octoai.in"),
        "embed-vertexai": load_requirements(ingest_requirements_dir / "embed-vertexai.in"),
        "openai": load_requirements(ingest_requirements_dir / "embed-openai.in"),
        "bedrock": load_requirements(ingest_requirements_dir / "embed-aws-bedrock.in"),
        "databricks-volumes": load_requirements(ingest_requirements_dir / "databricks-volumes.in"),
    }


def get_extras() -> dict[str, List[str]]:
    reqs = get_doc_reqs()
    reqs.update(
        {
            "all-docs": get_all_doc_reqs(),
            # Legacy extra requirements
            "huggingface": load_requirements(requirements_dir / "huggingface.in"),
            "local-inference": get_all_doc_reqs(),
            "paddleocr": load_requirements(requirements_dir / "extra-paddleocr.in"),
        }
    )
    reqs.update(get_connector_reqs())
    return reqs
