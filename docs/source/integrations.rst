Integrations
=============
Integrate your model development pipeline with your favorite machine learning frameworks and libraries,
and prepare your data for ingestion into downstream systems. Most of our integrations come in the form of
`staging bricks <https://unstructured-io.github.io/unstructured/bricks.html#staging>`_,
which take a list of ``Element`` objects as input and return formatted dictionaries as output.


``Integration with Argilla``
----------------------------
You can convert a list of ``Text`` elements to an `Argilla <https://www.argilla.io/>`_ ``Dataset`` using the `stage_for_argilla <https://unstructured-io.github.io/unstructured/bricks.html#stage-for-argilla>`_ staging brick. Specify the type of dataset to be generated using the ``argilla_task`` parameter. Valid values are ``"text_classification"``, ``"token_classification"``, and ``"text2text"``. Follow the link for more details on usage.


``Integration with Datasaur``
------------------------------
You can format a list of ``Text`` elements as input to token based tasks in `Datasaur <https://datasaur.ai/>`_ using the `stage_for_datasaur <https://unstructured-io.github.io/unstructured/bricks.html#stage-for-datasaur>`_ staging brick. You will obtain a list of dictionaries indexed by the keys ``"text"`` with the content of the element, and ``"entities"`` with an empty list. Follow the link to learn how to customise your entities and for more details on usage.


``Integration with Hugging Face``
----------------------------------
You can prepare ``Text`` elements for processing in Hugging Face `Transformers <https://huggingface.co/docs/transformers/index>`_
pipelines by splitting the elements into chunks that fit into the model's attention window using the `stage_for_transformers <https://unstructured-io.github.io/unstructured/bricks.html#stage-for-transformers>`_ staging brick. You can customise the transformation by defining
the ``buffer`` and ``window_size``, the ``split_function`` and the ``chunk_separator``. if you need to operate on
text directly instead of ``unstructured`` ``Text`` objects, use the `chunk_by_attention_window <https://unstructured-io.github.io/unstructured/bricks.html#stage-for-transformers>`_ helper function. Follow the links for more details on usage.


``Integration with Labelbox``
------------------------------
You can format your outputs for use with `LabelBox <https://labelbox.com/>`_ using the `stage_for_label_box <https://unstructured-io.github.io/unstructured/bricks.html#stage-for-label-box>`_ staging brick. LabelBox accepts cloud-hosted data and does not support importing text directly. With this integration you can stage the data files in the ``output_directory`` to be uploaded to a cloud storage service (such as S3 buckets) and get a config of type ``List[Dict[str, Any]]`` that can be written to a ``.json`` file and imported into LabelBox. Follow the link to see how to generate the ``config.json`` file that can be used with LabelBox, how to upload the staged data files to an S3 bucket, and for more details on usage.


``Integration with Label Studio``
----------------------------------
You can format your outputs for upload to `Label Studio <https://labelstud.io/>`_ using the `stage_for_label_studio <https://unstructured-io.github.io/unstructured/bricks.html#stage-for-label-studio>`_ staging brick. After running ``stage_for_label_studio``, you can write the results
to a JSON folder that is ready to be included in a new Label Studio project. You can also include pre-annotations and predictions
as part of your upload.

Check our example notebook to format and upload the risk section from an SEC filing to Label Studio for a sentiment analysis labeling task `here <https://unstructured-io.github.io/unstructured/examples.html#sentiment-analysis-labeling-in-labelstudio>`_ . Follow the link for more details on usage, and check `Label Studio docs <https://labelstud.io/tags/labels.html>`_ for a full list of options for labels and annotations.


``Integration with LangChain``
--------------------------------
Our integration with `LangChain <https://github.com/hwchase17/langchain>`_ makes it incredibly easy to combine language models with your data, no matter what form it is in. The `Unstructured.io File Loader <https://langchain.readthedocs.io/en/latest/modules/document_loaders/examples/unstructured_file.html>`_ extracts the text from a variety of unstructured text files using our ``unstructured`` library. It is designed to be used as a way to load data into `LlamaIndex <https://github.com/jerryjliu/llama_index>`_ and/or subsequently used as a Tool in a LangChain Agent. See `here <https://github.com/emptycrown/llama-hub/tree/main>`_ for more `LlamaHub <https://llamahub.ai/>`_ examples.

To use ``Unstructured.io File Loader`` you will need to have LlamaIndex 🦙 (GPT Index) installed in your environment. Just ``pip install llama-index`` and then pass in a ``Path`` to a local file. Optionally, you may specify split_documents if you want each element generated by ``unstructured`` to be placed in a separate document. Here is a simple example on how to use it:

.. code:: python

  from pathlib import Path
  from llama_index import download_loader


  UnstructuredReader = download_loader("UnstructuredReader")

  loader = UnstructuredReader()
  documents = loader.load_data(file=Path('./10k_filing.html'))


``Integration with Pandas``
----------------------------
You can convert a list of ``Element`` objects to a Pandas dataframe with columns for
the text from each element and their types such as ``NarrativeText`` or ``Title`` using the `convert_to_dataframe <https://unstructured-io.github.io/unstructured/bricks.html#convert-to-dataframe>`_ staging brick. Follow the link for more details on usage.


``Integration with Prodigy``
-----------------------------
You can format your JSON or CSV outputs for use with `Prodigy <https://prodi.gy/docs/api-loaders>`_ using the `stage_for_prodigy <https://unstructured-io.github.io/unstructured/bricks.html#stage-for-prodigy>`_ and `stage_csv_for_prodigy <https://unstructured-io.github.io/unstructured/bricks.html#stage-csv-for-prodigy>`_ staging bricks. After running ``stage_for_prodigy`` |
``stage_csv_for_prodigy``, you can write the results to a ``.json`` | ``.jsonl`` or a ``.csv`` file that is ready to be used with Prodigy. Follow the links for more details on usage.
