# FastAPI with MongoDB and Celery

This application uses FastAPI, MongoDB (with Beanie ODM), and Celery for background tasks.

## Setup

1. Make sure you have Python 3.7+ installed.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Make sure MongoDB and Redis are running.

## Running the Application

### Start the FastAPI server

```bash
python main.py
```

### Start the Celery worker

```bash
python start_celery.py
```

Or manually:

```bash
celery -A database.celery_worker.celery_app worker --loglevel=info
```

## Common Issues

### CollectionWasNotInitialized

If you see `CollectionWasNotInitialized` errors in your Celery logs, it means the database collections were not properly initialized before the task attempted to use them. Make sure both the FastAPI app and Celery worker are properly initializing the database.

## Scheduled Tasks

The application has several scheduled tasks:
- `cron_notification`: Sends notifications to users for routine reminders
- `mark_not_done`: Marks missed sessions as not done
- `reset_sessions_status`: Resets session statuses at midnight
- `update_all_users_streaks`: Updates user streaks at midnight

You can adjust the scheduling in `app.py`.

# FastAPI and MongoDB Boilerplate

A simple starter for building RESTful APIs with FastAPI and MongoDB.

![image](./img.jpg)

## Features

+ Python FastAPI backend.
+ MongoDB database.
+ Authentication
+ Deployment

## Using the applicaiton

To use the application, follow the outlined steps:

1. Clone this repository and create a virtual environment in it:

```console
$ python3 -m venv venv
```

2. Install the modules listed in the `requirements.txt` file:

```console
(venv)$ pip3 install -r requirements.txt
```
3. You also need to start your mongodb instance either locally or on Docker as well as create a `.env.dev` file. See the `.env.sample` for configurations. 

    Example for running locally MongoDB at port 27017:
    ```console
    cp .env.sample .env.dev
    ```

4. Start the application:

```console
python3 main.py
```


The starter listens on port 8000 on address [0.0.0.0](0.0.0.0:8080). 

![FastAPI-MongoDB starter](doc.png)


## Testing

To run the tests, run the following command:

```console
(venv)$ pytest
```

You can also write your own tests in the `tests` directory.  
The test follow by the official support [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/), [pytest](https://docs.pytest.org/en/stable/), [anyio](https://anyio.readthedocs.io/en/stable/) for async testing application.

## Deployment

This application can be deployed on any PaaS such as [Heroku](https://heroku.com) or [Okteto](https://okteto) and any other cloud service provider.

## Contributing ?


Fork the repo, make changes and send a PR. We'll review it together!

## License

This project is licensed under the terms of MIT license.
# GT_BE
