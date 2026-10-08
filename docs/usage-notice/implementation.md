# Implementation record

The recovered Oracle proposal is the working design. The source lane was clean at
`d621285e1b45b6ddbf2e16b62777231cdb268427`; this continuation uses the same snapshot.
There were no earlier source changes to duplicate. No AGENTS.md, crag-AGENTS.md,
or matching local repository shim was present.

The implementation follows the proposed helper, nonblocking ownership claim,
child fork reset, shared copy, stdout inspection, and pre-telemetry-opt-out hook.
It adds no dependency, handler, persistent storage, thread, or notice transport.
Only ordinary notice failures are suppressed; partition results and errors remain intact.
Failed or filtered attempts are consumed. Logging destinations and latency remain
under application control. Native extension forks that bypass Python callbacks
are outside the lifecycle guarantee.

The prepared commit history contains recent fixes, including pptx and chunking.
The README says the open source library will stay free and describes higher quality
commercial output. No evidence establishes a maintenance-mode start date or duration.
Maintenance duration, offer eligibility, final wording, and the placeholder URL need
owner review before publication. This branch is an illustration.

## Oracle evidence and recovery

Conversation: https://chatgpt.com/c/6ac80ad7-c208-83e8-8174-357e57b37b92
Session: `usage-notice-proposal`. The repository copy removes trailing whitespace only; the original recovered artifact
is preserved in the delivery directory. The complete recovered response is
[oracle-proposal.md](oracle-proposal.md). Existing before/during evidence proves
Pro composer selection. Generation identity was not independently confirmed.
The prior blocker was a false negative from outdated Oracle message selectors;
no new Oracle submission or transport repair was made.

## Coverage audit

AST inspection of the actual prepared checkout found these decorated functions.
Standalone cleaning, chunking, serialization, CLI help, and diagnostics have no
new hooks. A registry entry alone was not used as coverage evidence.

- `unstructured/partition/api.py`: `partition_via_api()`
- `unstructured/partition/api.py`: `partition_multiple_via_api()`
- `unstructured/partition/audio.py`: `partition_audio()`
- `unstructured/partition/auto.py`: `partition()`
- `unstructured/partition/csv.py`: `partition_csv()`
- `unstructured/partition/doc.py`: `partition_doc()`
- `unstructured/partition/docx.py`: `partition_docx()`
- `unstructured/partition/email.py`: `partition_email()`
- `unstructured/partition/epub.py`: `partition_epub()`
- `unstructured/partition/html/partition.py`: `partition_html()`
- `unstructured/partition/image.py`: `partition_image()`
- `unstructured/partition/json.py`: `partition_json()`
- `unstructured/partition/md.py`: `partition_md()`
- `unstructured/partition/msg.py`: `partition_msg()`
- `unstructured/partition/ndjson.py`: `partition_ndjson()`
- `unstructured/partition/odt.py`: `partition_odt()`
- `unstructured/partition/org.py`: `partition_org()`
- `unstructured/partition/pdf.py`: `partition_pdf()`
- `unstructured/partition/ppt.py`: `partition_ppt()`
- `unstructured/partition/pptx.py`: `partition_pptx()`
- `unstructured/partition/rst.py`: `partition_rst()`
- `unstructured/partition/rtf.py`: `partition_rtf()`
- `unstructured/partition/text.py`: `partition_text()`
- `unstructured/partition/tsv.py`: `partition_tsv()`
- `unstructured/partition/xlsx.py`: `partition_xlsx()`
- `unstructured/partition/xml.py`: `partition_xml()`
