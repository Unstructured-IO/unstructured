### Install MySQL

Follow the instructions [here](https://dev.mysql.com/doc/refman/5.7/en/installing.html)
to install MySQL on your system. If you're using homebrew on Mac, you can
install MySQL with `brew install mysql`.

### Start MySQL

Start the MySQL service. If you're using homebrew on Mac, run `brew services start mysql`.

Now you can connect to MySQL with the command `mysql -u root`.
You can create a non-root user with the following command:

```sql
CREATE USER '<username>'@'localhost' IDENTIFIED BY '<password>';
```
```sql
CREATE DATABASE unstructured_example;
GRANT ALL PRIVILEGES ON unstructured_example.* TO '<username>'@'localhost';
```
