# Loading `unstructured` outputs into Postgres with `pgvector`

The following example shows how to load `unstructured` output into Postgres with the
`pgvector` extension installed. Combining the similarity search functionality of
`pgvector` with the traditional RDBMS capabilities of Postgres allow users to performing
similarity searches that are conditioned on metadata or biased toward more recent documents.
Use cases include document discovery and more sophisticated retrieval augmented generation
for LLMs.
The [`langchain` docs](https://docs.langchain.com/docs/components/memory/) have more information
about retrieval augmented generation.

## Running the example
1. Install [Postgres](https://www.postgresql.org/docs/15/tutorial-install.html).
1. Install [`pgvector`](https://github.com/pgvector/pgvector)
1. Run `pip install -r requirements.txt` to install the Python dependencies.
1. Run `jupyter-notebook to start.
1. Run the `pgvector.ipynb` notebook.
