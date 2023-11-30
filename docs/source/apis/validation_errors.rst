API Validation Errors
=====================

This section details the structure of HTTP validation errors returned by the API.

HTTPValidationError
--------------------

**Type**: object

**Title**: HTTPValidationError

**Detail**

- **Type**: array
- **Description**: An array of `ValidationError` items, providing detailed information about the validation errors encountered.

ValidationError
---------------

**Type**: object

**Title**: ValidationError

**Required Fields**: loc, msg, type

- **Location (loc)**
    - **Type**: array
    - **Description**: The location of the validation error in the request. Each item in the array can be either a string (e.g., field name) or an integer (e.g., array index).

- **Message (msg)**
    - **Type**: string
    - **Description**: A descriptive message about the validation error.

- **Error Type (type)**
    - **Type**: string
    - **Description**: The type of validation error, categorizing the nature of the error.
