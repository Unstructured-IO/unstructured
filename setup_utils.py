from pathlib import Path
from typing import List, Union


def load_requirements(file_list: Union[str, List[str]]) -> List[str]:
    file_list = list(file_list)
    requirements: List[str] = []
    for file in file_list:
        path = Path(file)
        file_dir = path.parent.resolve()
        with open(file, encoding="utf-8") as f:
            raw = f.read().splitlines()
            requirements.extend([r for r in raw if not r.startswith("#") and not r.startswith("-")])
            recursive_reqs = [r for r in raw if r.startswith("-r")]
            if recursive_reqs:
                filenames = []
                for recursive_req in recursive_reqs:
                    file_spec = recursive_req.split()[-1]
                    file_path = Path(file_dir) / file_spec
                    filenames.append(str(file_path.resolve()))
                requirements.extend(load_requirements(file_list=filenames))
    # Remove duplicates and any blank entries
    return list({r for r in requirements if r})


def get_base_reqs() -> List[str]:
    file = "requirements/base.in"
    return load_requirements(file)


def get_doc_reqs() -> dict[str, List[str]]:
    return {
        "csv": load_requirements("requirements/extra-csv.in"),
        "doc": load_requirements("requirements/extra-docx.in"),
        "docx": load_requirements("requirements/extra-docx.in"),
        "epub": load_requirements("requirements/extra-epub.in"),
        "image": load_requirements("requirements/extra-pdf-image.in"),
        "markdown": load_requirements("requirements/extra-markdown.in"),
        "msg": load_requirements("requirements/extra-msg.in"),
        "odt": load_requirements("requirements/extra-odt.in"),
        "org": load_requirements("requirements/extra-pandoc.in"),
        "pdf": load_requirements("requirements/extra-pdf-image.in"),
        "ppt": load_requirements("requirements/extra-pptx.in"),
        "pptx": load_requirements("requirements/extra-pptx.in"),
        "rtf": load_requirements("requirements/extra-pandoc.in"),
        "rst": load_requirements("requirements/extra-pandoc.in"),
        "tsv": load_requirements("requirements/extra-csv.in"),
        "xlsx": load_requirements("requirements/extra-xlsx.in"),
    }


def get_all_doc_reqs() -> List[str]:
    reqs = []
    for req in get_doc_reqs().values():
        reqs.extend(req)
    return list(set(reqs))


def get_connector_reqs() -> dict[str, List[str]]:
    return {
        "airtable": load_requirements("requirements/ingest/airtable.in"),
        "astra": load_requirements("requirements/ingest/astra.in"),
        "azure": load_requirements("requirements/ingest/azure.in"),
        "azure-cognitive-search": load_requirements(
            "requirements/ingest/azure-cognitive-search.in",
        ),
        "biomed": load_requirements("requirements/ingest/biomed.in"),
        "box": load_requirements("requirements/ingest/box.in"),
        "chroma": load_requirements("requirements/ingest/chroma.in"),
        "clarifai": load_requirements("requirements/ingest/clarifai.in"),
        "confluence": load_requirements("requirements/ingest/confluence.in"),
        "delta-table": load_requirements("requirements/ingest/delta-table.in"),
        "discord": load_requirements("requirements/ingest/discord.in"),
        "dropbox": load_requirements("requirements/ingest/dropbox.in"),
        "elasticsearch": load_requirements("requirements/ingest/elasticsearch.in"),
        "gcs": load_requirements("requirements/ingest/gcs.in"),
        "github": load_requirements("requirements/ingest/github.in"),
        "gitlab": load_requirements("requirements/ingest/gitlab.in"),
        "google-drive": load_requirements("requirements/ingest/google-drive.in"),
        "hubspot": load_requirements("requirements/ingest/hubspot.in"),
        "jira": load_requirements("requirements/ingest/jira.in"),
        "mongodb": load_requirements("requirements/ingest/mongodb.in"),
        "notion": load_requirements("requirements/ingest/notion.in"),
        "onedrive": load_requirements("requirements/ingest/onedrive.in"),
        "opensearch": load_requirements("requirements/ingest/opensearch.in"),
        "outlook": load_requirements("requirements/ingest/outlook.in"),
        "pinecone": load_requirements("requirements/ingest/pinecone.in"),
        "postgres": load_requirements("requirements/ingest/postgres.in"),
        "qdrant": load_requirements("requirements/ingest/qdrant.in"),
        "reddit": load_requirements("requirements/ingest/reddit.in"),
        "s3": load_requirements("requirements/ingest/s3.in"),
        "sharepoint": load_requirements("requirements/ingest/sharepoint.in"),
        "salesforce": load_requirements("requirements/ingest/salesforce.in"),
        "sftp": load_requirements("requirements/ingest/sftp.in"),
        "slack": load_requirements("requirements/ingest/slack.in"),
        "wikipedia": load_requirements("requirements/ingest/wikipedia.in"),
        "weaviate": load_requirements("requirements/ingest/weaviate.in"),
        # Legacy extra requirements
        "huggingface": load_requirements("requirements/huggingface.in"),
        "local-inference": get_all_doc_reqs(),
        "paddleocr": load_requirements("requirements/extra-paddleocr.in"),
        "embed-huggingface": load_requirements("requirements/ingest/embed-huggingface.in"),
        "embed-octoai": load_requirements("requirements/ingest/embed-octoai.in"),
        "embed-vertexai": load_requirements("requirements/ingest/embed-vertexai.in"),
        "openai": load_requirements("requirements/ingest/embed-openai.in"),
        "bedrock": load_requirements("requirements/ingest/embed-aws-bedrock.in"),
        "databricks-volumes": load_requirements("requirements/ingest/databricks-volumes.in"),
    }


def get_extras() -> dict[str, List[str]]:
    reqs = get_doc_reqs()
    reqs["all-docs"] = get_all_doc_reqs()
    reqs.update(get_connector_reqs())
    return reqs
