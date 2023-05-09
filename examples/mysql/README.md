# Loading `unstructured` outputs into MySQL

The following example shows how to load `unstructured` output into MySQL.
This allows you to run queries based on metadata that the `unstructured`
library has extracted.
Follow the instructions [here](https://dev.mysql.com/doc/refman/5.7/en/installing.html)
to install MySQL on your system. If you're using homebrew on Mac, you can
install MySQL with `brew install mysql`.


Once you have installed MySQL, you can connect to MySQL with the command `mysql -u root`.
You can create a non-root user and an `unstructured_example` database using the following
commands:

```sql
CREATE USER '<username>'@'localhost' IDENTIFIED BY '<password>';
CREATE DATABASE unstructured_example;
GRANT ALL PRIVILEGES ON unstructured_example.* TO '<username>'@'localhost';
```

## Running the example

1. Run `pip install -r requirements.txt` to install the Python dependencies.
1. Run `jupyter-notebook to start.
1. Run the `load-into-mysql.ipynb` notebook.
