Retry Strategy Configuration
===============================

A common retry strategy configuration is a critical element in enhancing the robustness and resiliency of a system,
especially when dealing with temporary network issues. This configuration typically includes parameters that
define how the system should respond to network-related errors, such as connection timeouts or transient failures.
It specifies the number of retry attempts, the time intervals between retries, and the conditions under which
retries should be initiated. By configuring an effective retry strategy, a system can automatically recover from
network disruptions, increasing its ability to withstand intermittent issues and ensuring a more reliable and
uninterrupted operation. This strategy is vital for maintaining system stability, data integrity, and minimizing
downtime in the face of unpredictable network hiccups.

Configs
---------------------

* ``max_retries``: How many times to retry before giving up.
* ``max_retry_time``: If provided, will end trying after this much time has elapsed.
