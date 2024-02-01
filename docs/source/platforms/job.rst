Jobs Scheduling
===============

Jobs Dashboard
---------------

The job dashboard provides a centralized view for managing and monitoring the execution of data processing tasks within your workflows. Here is how to navigate and view job status:

- The central panel lists all jobs with their associated workflow’s *Name*, *ID*, *Status*, and *Execution Start Time*.

- The 'Status' indicator provides at-a-glance information:

  - A 'New' status indicates a job has been created but has yet to run.

  - A 'Scheduled' status shows that a job is set to run at a future date and time, as indicated in the 'Execution Start Time' column.

  - A ‘Partitioning’ status means that documents are currently being processed.

  - A ‘Finished` status indicates the job has been completed.

  - A ‘Failed’ status indicates the job has encountered some errors.

Run a Job
----------

To run a workflow, you follow these steps.

1. Click on the 'Jobs' tab in the side navigation menu and click the 'Run Job' button to open the job configuration pop-up window.

2. From the *Select a Workflow or create a new one* dropdown menu, you can select a workflow or create a new one.

3. If you select to *create a new workflow*, complete the following fields:

   - Sources: Specify the source connector for the job.
   - Destination: Determine the destination connector where the processed data will be sent.
   - Strategy: Select the processing strategy for the data.
   - Settings: Configure additional job settings.

4. After you click the ‘Run’ button, the system will run the workflow immediately.

Monitor Job’s Activity Logs
----------------------------

The Job Details page is a comprehensive section for monitoring the specific details of jobs executed within a particular workflow. To access this page, click the specific *Workflow* or *ID* on the Job Dashboard.

Here is the information provided by the Job Details page:

- **Job Summary**: At the top of the dashboard, you will see the following document status:

  - *Documents*: Total number of documents included in the workflow.
  - *New*: number of new documents to be processed.
  - *Partitioning*: number of documents being processed.
  - *Finished*: number of documents that have been completed.
  - *Failed*: number of documents that failed to be processed.

- **Job Status and Execution Information**: The page provides a detailed log of the job's execution, including *status*, *expected execution time*, and *Job ID* for reference.

- **Activity Logs**: The activity logs display a timestamped sequence of events during the job's execution. This can include when new documents are found, when documents are processed, and any errors or messages related to the job.