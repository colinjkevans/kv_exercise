```
Build a simple, maintainable key-value store by implementing two services that communicate with each other: a key-value store (KV service) and a client that tests the key-value store (test client). This project should ideally take 2 hours to complete and no more than 4 hours.

The KV service should implement a basic JSON Rest API as the primary public interface. The interface must support the following operations:

    Store a value at a given key.
    Attempt to retrieve the value for a given key.
    Delete a key.


The test client should be a service that has at least two operations that exercise the correctness of the KV service interface. All endpoints will return whether or not they succeeded. The endpoints are:

    test_deletion: This should instill confidence in the delete operation.
    test_overwrite: This should instill confidence that the most recently set value for a key is the one that is served.


Additional requirements:

    The services should be executed independently within Docker containers.
    It should be easy to test the KV store and the test client from the command line.
    Please choose one of these programming languages for implementation: golang, python, java, scala.



What is being tested in this exercise:

    Your ability to write readable, maintainable, debuggable code. We will be looking at this as if it were a request to merge into a production project. Think of what you would look for in backend services when evaluating a pull request.
    Your ability to provide readable, concise documentation. Imagine the reviewers had to maintain and QA this project. There should be instructions for how to test the services.
    Your ability to write extensible, modular code. It should be possible to add KV store functionality and quickly change the transport layer protocol.


Your time is valuable. This is what is not being tested in this exercise:

    The number of endpoints you write or attempting to rebuild most of the redis API. You may write however many endpoints you desire for this exercise with no penalty. But the reviewers will only focus on the semantics described above when evaluating the take home.


Please upload the code to a publicly accessible github or bitbucket account.  A readme file should be provided briefly documenting what you are delivering. Like our own code, we expect testing instructions: whether it’s an automated test framework, or simple manual steps.

We understand that you have other responsibilities, so if you think you’ll need more than 5 business days, just let us know when you expect to send a reply.

Please don’t hesitate to contact us with questions for clarification. And good luck!
```

### Assumptions

- Allowed k/v types - values based on json data types, allowed to be string, number, boolean.
                      keys come from URI, so only allow strings
- PUT verb can replace or create. Alternative option would be to only replace and return 404 for non-existent key
- POST will only create a resource. Returns 409 Conflict if the key already exists.
- "quickly change the transport layer protocol"? 
  - HTTP over UDP? Not sure I can do that in 2 hours. 
  - HTTP/3? maybe hypercorn asgi server