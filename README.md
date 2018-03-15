# Project 7: Authenticated brevet time calculator service

## What is in this repository

You have a minimal implementation of password- and token-based authentication modules in "Auth" folder, using which you can create authenticated RESTful API-based services. 

Implemented and maintained by Andrew Werderman. (amwerderman@gmail.com)


## Functionality

Use `docker-compose up` to set up and start the ecosystem. Once started, the database needs to be populated.
So, first visit `http://<host:5002>/` to populate the brevet with controls. 

Next, to expose the API, the user will need to register. To register use the following
POST request in the command line:

`curl -d "username=<username>&password=<password>" localhost:5001/api/register`

Then, once registered, the user will need to generate a token to use the API. To make the 
GET request for the token, the user will use the same username and password they registered with.

`curl -u "<username>:<password>" localhost:5001/api/token`

This last request will return a JSON object with two fields. 'Duration' is the approximate number of
seconds the given token is valid for. 'Token' is the token the user will use to use the API's resources.
To use the token to GET the resources, the user will copy and paste the token into their succeeding
requests like so:

`curl -u "<token>:" localhost:5001/<items>/<format>`
NOTE: If you do not want to get prompted to enter a password (which would be to nothing), include the ':'. 

Here `<items>` refers to 'listAll', 'listOpenOnly', or 'listCloseOnly'. Anything else will return an
error. `<format>` is optional and will default to JSON, but 'json' and 'csv' are the possible inputs.
Finally, if desired, the user can add `?top=<num>` to the end of their http request to limit the number
of responses. `<num>` is expected to be a positive integer. 
