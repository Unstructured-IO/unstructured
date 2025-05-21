---
# For reference on model card metadata, see the spec: https://github.com/huggingface/hub-docs/blob/main/modelcard.md?plain=1
# Doc / guide: https://huggingface.co/docs/hub/model-cards
PaddleOCR
---

# Model Card for PaddleOCR

<!-- Provide a quick summary of what the model is/does. -->

PaddleOCR is an Optical Character Recognition (OCR) model developed by PaddlePaddle, an open-source deep learning platform. It is designed to recognize and extract text from images, including complex documents, natural scenes, and various types of textual data. The model is particularly well-suited for multilingual text recognition, providing high accuracy in detecting and recognizing both printed and handwritten text.

## Model Details

PaddleOCR employs a multi-stage pipeline for OCR tasks:

1. **Text Detection**: Detects text regions within an image using a text detection network, typically based on advanced convolutional neural networks (CNNs).
2. **Text Recognition**: Converts the detected text regions into readable strings, often using a sequence-to-sequence model or a recurrent neural network (RNN) with attention mechanisms.
3. **Post-Processing**: Enhances the output text through error correction and formatting for better readability and accuracy.

### Model Description

<!-- Provide a longer summary of what this model is. -->

PaddleOCR is an end-to-end OCR solution that integrates text detection, recognition, and post-processing to deliver accurate and efficient text extraction from various image types. It is particularly useful in multilingual contexts, supporting over 80 languages, and excels in recognizing both printed and handwritten text.

- **Developed by:** PaddlePaddle Team 
- **Model type:** Optical Character Recognition (OCR)
- **Language(s) (NLP):** Supports 80+ languages, including English, Chinese, Japanese, Korean, etc.
- **License:** Apache-2.0

### Model Sources [optional]

<!-- Provide the basic links for the model. -->

- **Repository:** [PaddleOCR GitHub Repository](https://github.com/PaddlePaddle/PaddleOCR)
- **Paper [optional]:** [More Information Needed]
- **Demo [optional]:** [More Information Needed]

## Uses

<!-- Address questions around how the model is intended to be used, including the foreseeable users of the model and those affected by the model. -->

PaddleOCR is designed for:
- Text detection in images
- Text recognition (OCR)
- Layout analysis
- Table recognition

### Direct Use

<!-- This section is for the model use without fine-tuning or plugging into a larger ecosystem/app. -->

PaddleOCR can be used directly for tasks like:

- Document digitization and archiving
- Automated data entry and form processing
- Text extraction from natural scenes (e.g., street signs, product labels)
- Translation services requiring text extraction from images

It can be used in various scenarios such as:
- Document digitization
- ID card recognition
- License plate recognition
- Scene text detection and recognition

### Downstream Use [optional]

<!-- This section is for the model use when fine-tuned for a task, or when plugged into a larger ecosystem/app -->


When fine-tuned or integrated into larger applications, PaddleOCR can be used for:

- Enhanced OCR in specific domains like healthcare, legal, and finance
- Multilingual text recognition in mobile apps and web platforms
- Automated processing in machine translation systems

### Out-of-Scope Use

<!-- This section addresses misuse, malicious use, and uses that the model will not work well for. -->

PaddleOCR may not perform well in cases with:

- Highly distorted or illegible text
- Text in low-resource languages that are not well supported by the training data
- Malicious use cases like unauthorized data extraction or privacy violations

## Bias, Risks, and Limitations

<!-- This section is meant to convey both technical and sociotechnical limitations. -->

The model may exhibit biases depending on the language or script, particularly for underrepresented languages. Additionally, while PaddleOCR is highly accurate, it may struggle with highly curved or distorted text, or in scenarios with very poor image quality.

### Recommendations

<!-- This section is meant to convey recommendations with respect to the bias, risk, and technical limitations. -->

Users (both direct and downstream) should be made aware of the risks, biases, and limitations of the model. For best results, consider fine-tuning the model on domain-specific data and validating its performance in your specific use case.

## How to Get Started with the Model

Use the code below to get started with the model.

```
from paddleocr import PaddleOCR, draw_ocr
import cv2

# Initialize the PaddleOCR model
ocr = PaddleOCR(use_angle_cls=True, lang='en') # Set the language

# Load an image
image_path = 'path/to/your/image.jpg'
img = cv2.imread(image_path)

# Perform OCR
result = ocr.ocr(image_path)

# Print the results
for line in result:
    print(line)

# Optional: Draw the OCR results on the image
image_with_boxes = draw_ocr(img, result)
cv2.imwrite('path/to/save/result.jpg', image_with_boxes)
```

## Training Details

### Training Data

<!-- This should link to a Dataset Card, perhaps with a short stub of information on what the training data is all about as well as documentation related to data pre-processing or additional filtering. -->

PaddleOCR is trained on a large dataset that includes ICDAR datasets, diverse types of text from various languages and contexts, including both synthetic and real-world images to ensure robust performance in practical applications.

### Training Procedure

<!-- This relates heavily to the Technical Specifications. Content here should link to that section when it is relevant to the training procedure. -->

The model is trained using a combination of supervised learning techniques, where text detection and recognition tasks are optimized separately before being integrated into the final OCR pipeline.


#### Preprocessing [optional]

Standard image preprocessing steps such as resizing, normalization, and data augmentation are applied to the training data to improve model robustness and generalization.

#### Training Hyperparameters

- **Training regime:** <!--fp32, fp16 mixed precision, bf16 mixed precision, bf16 non-mixed precision, fp16 non-mixed precision, fp8 mixed precision -->

- Training regime: Mixed precision (fp16) for faster and more memory-efficient training.
- Optimizer: Adam with a learning rate scheduler.
- Batch size: Dependent on the hardware configuration.

#### Speeds, Sizes, Times [optional]

<!-- This section provides information about throughput, start/end time, checkpoint size if relevant, etc. -->

PaddleOCR is optimized for both speed and accuracy, with training times and model sizes varying based on the language and complexity of the dataset.

## Evaluation

<!-- This section describes the evaluation protocols and provides the results. -->

### Testing Data, Factors & Metrics

#### Testing Data

<!-- This should link to a Dataset Card if possible. -->

PaddleOCR is tested on standard OCR benchmarks and datasets, including multilingual text recognition datasets.

#### Factors

<!-- These are the things the evaluation is disaggregating by, e.g., subpopulations or domains. -->

Evaluation is disaggregated by language, text type (printed vs. handwritten), and image quality.

#### Metrics

<!-- These are the evaluation metrics being used, ideally with a description of why. -->

Common evaluation metrics include accuracy, character error rate (CER), and word error rate (WER).

### Results

PaddleOCR consistently achieves high accuracy across multiple benchmarks, particularly in multilingual and complex scene text recognition tasks.

#### Summary

PaddleOCR is a state-of-the-art OCR solution that excels in both accuracy and efficiency, making it a versatile tool for a wide range of text recognition tasks.

## Model Examination [optional]

<!-- Relevant interpretability work for the model goes here -->

PaddleOCR includes visualization tools to help interpret model decisions, particularly in text detection and recognition stages.

## Environmental Impact [optional]

<!-- Total emissions (in grams of CO2eq) and additional considerations, such as electricity usage, go here. Edit the suggested text below accordingly -->

Carbon emissions can be estimated using the [Machine Learning Impact calculator](https://mlco2.github.io/impact#compute) presented in [Lacoste et al. (2019)](https://arxiv.org/abs/1910.09700).

- **Hardware Type:** GPU (NVIDIA V100 or similar)
- **Hours used:** [More Information Needed]
- **Cloud Provider:** AWS, Google Cloud, etc.
- **Compute Region:** [More Information Needed]
- **Carbon Emitted:** [More Information Needed]

## Technical Specifications [optional]

### Model Architecture and Objective

PaddleOCR is built using a combination of CNNs, RNNs, and attention mechanisms to accurately detect and recognize text in images.

### Compute Infrastructure

PaddleOCR is optimized for both cloud and edge devices, supporting a wide range of hardware configurations.

#### Hardware

PaddleOCR can run on various hardware platforms, from high-end GPUs in cloud environments to mobile CPUs.
We have found issues running PaddleOCR on Apple Silicon cpus.

#### Software

PaddleOCR is implemented in PaddlePaddle, and it supports easy integration with other PaddlePaddle ecosystem tools.

## Citation [optional]

<!-- If there is a paper or blog post introducing the model, the APA and Bibtex information for that should go in this section. -->

**BibTeX:** **[optional]**

@article{paddleocr2021,
  title={PaddleOCR: An Awesome Multilingual OCR Toolkits based on PaddlePaddle},
  author={PaddleOCR team},
  year={2021},
  journal={PaddleOCR Repository},
  url={https://github.com/PaddlePaddle/PaddleOCR}
}

**APA:** **[optional]**

[More Information Needed]

## Glossary [optional]

<!-- If relevant, include terms and calculations in this section that can help readers understand the model or model card. -->

[More Information Needed]

## More Information [optional]

[More Information Needed]

## Model Card Authors [optional]

[More Information Needed]

## Model Card Contact

[More Information Needed]