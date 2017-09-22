# Affiche


Sometimes you want to know the coolest films that are going on at the moment, but when you go to the [afisha](https://www.afisha.ru/msk/schedule_cinema/) it is difficult to determine which of them has a higher rating at [kinopoisk](https://www.kinopoisk.ru)


### [Affiche](https://fierce-tor-88650.herokuapp.com/)


Quickstart
----------


Run the following commands to install project locally for developing:

```
    git clone https://github.com/romabiker/25_cinemas_site.git
    cd 25_cinemas_site
    pipenv shell   # activates virtual environment
    pipenv install #automaticaly installs all dependacies from Pipfile
    pipenv graph   # shows all installed dependancies
    export FLASK_APP=autoapp.py
    flask key
    export AFFICHE_SECRET="paste from cli generated flask key"
    export FLASK_DEBUG=1
    flask run       # start the flask developer server for autoreloading on changes
    gunicorn autoapp:app # also you may try production server
```


Managment commands
------------------

```
    flask clean   # Remove *.pyc and *.pyo files recursively starting at current directory.
    flask key     # Generate secret key
```

Deployment
----------

Project is prepared for deployment to Heroku cloud

To deploy:

Register on Heroku

[Download and install Heroku CLI](https://devcenter.heroku.com/articles/getting-started-with-python#set-up)

Run the following commands:

```
    Heroku login
    git clone https://github.com/romabiker/25_cinemas_site.git
    cd 25_cinemas_site
    heroku create # creates application
    pipenv install #automaticaly installs all dependacies from Pipfile
    pipenv shell   # activates virtual environment
    heroku local web  # to check server locally
    git push heroku master  # deploy and after that visit dashboard settings on Heroku to provide AFFICHE_SECRET
    heroku ps:scale web=1 # runs project
    heroku open   # opens in browser
    heroku logs --tail # to see logging

```

## Project Goals

The code is written for educational purposes. Training course for web-developers - [DEVMAN.org](https://devman.org)
