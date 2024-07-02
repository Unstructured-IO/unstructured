from unstructured.metrics.table.table_alignment import TableAlignment


def test_get_element_level_alignment_when_no_match():
    example_table = [{"row_index": 0, "col_index": 0, "content": "a"}]
    metrics = TableAlignment.get_element_level_alignment(
        predicted_table_data=[example_table],
        ground_truth_table_data=[example_table],
        matched_indices=[-1],
    )
    assert metrics["col_index_acc"] == 0
    assert metrics["row_index_acc"] == 0
    assert metrics["row_content_acc"] == 0
    assert metrics["col_content_acc"] == 0
