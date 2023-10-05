# Analyzing Layout Elements

This directory contains examples of how to analyze layout elements.

## How to run

Run `pip install -r requirements.txt` to install the Python dependencies.

### Visualization
- Python script (visualization.py)
```
$ PYTHONPATH=. python examples/layout-analysis/visualization.py <file_path> <strategy>
```
The strategy can be one of "auto", "hi_res", "ocr_only", or "fast". For example,
```
$ PYTHONPATH=. python examples/layout-analysis/visualization.py example-docs/loremipsum.pdf hi_res
```