MongoDB
=======

This page contains the information to store processed data to a MongoDB database.

Prerequisites
--------------

- MongoDB Local Install
- Database and Collection

For more information, please refer to `MongoDB documentation <https://docs.mongodb.com/>`__.

Step-by-Step Guide
-------------------

.. image:: imgs/Destination-MongoDB.png
  :alt: Destination Connector MongoDB

1. **Access the Create Destination Page**. Navigate to the "Destinations" section within the platform's side navigation menu and click on "New Destination" to initiate the setup of a new destination for your processed data.

2. **Select Destination Type**. Select **MongoDB** destination connector from the ``Type`` dropdown menu.

3. **Configure Destination Details**

  - ``Name`` (*required*): Assign a descriptive name to the new destination connector.
  - ``URI`` (*required*): Enter the MongoDB connection URI.
  - ``Database`` (*required*): Provide the name of the target MongoDB database.
  - ``Collection``: Specify the name of the target MongoDB collection within the database.

4. **Submit**. Review all the details entered to ensure accuracy. Click 'Submit' to finalize the creation of the Destination Connector. The newly completed MongoDB connector will be listed on the Destinations dashboard.
