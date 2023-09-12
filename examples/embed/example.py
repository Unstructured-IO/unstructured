import os

from unstructured.embed.embedder.open_ai import OpenAIEmbedder, OpenAIEmbedderConfig

config = OpenAIEmbedderConfig(
    api_key=os.environ["OPENAI_API_KEY"],
    list_of_elements_json_paths="Path1 Path2",
    output_dir="embedding_outputs",
)
embedder = OpenAIEmbedder(config)
docs = embedder.get_embed_docs()
for doc in docs:
    doc.embed_and_write_result()
