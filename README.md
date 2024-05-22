CAR CRASH TYPE CLASSIFIER BY LOCATION
=====================================

This project is a starting Pack for MLOps projects based on the subject "road accident".

Project Organization
------------

    ├── LICENSE
    ├── README.md                   <- The top-level README for developers using this project.
    ├── .github                     <- GitHub configuration folder.
    |   └── workflows               <- Workflows folder.
    |       ├── run_containers.yml  <- GitHub action to startup containers from the docker-compose file.
    |       └── unit_tests.yml      <- Github action to run unit tests.
    ├── app                         <- API folder
    │   ├── Dockerfile              <- Dockerfile for building the Docker image of the API.
    │   ├── Tests                   <- Directory for API unit tests.
    │   │   └── test_api.py         <- Test file for the API ran by unit_tests.yml above on Push in github.
    │   ├── __init__.py             <- File that permits app to be used such as a module.
    │   ├── db_tools.py             <- Functions to access database - for users management by the API.
    │   ├── database.py             <- Relationnal database containing data on users.
    │   ├── main.py                 <- API routes that will run on local host using port 8000
    │   ├── models.py               <- ORM models to interact with database.
    │   ├── requirements.txt        <- Versionning file for the API environment.
    │   ├── router.py               <- Sub API containing routes for users management only.
    │   └── security_center.py      <- Security functions based on Oauth2.
    ├── docker-compose.yml          <- Docker Compose configuration file for deploying the application.
    ├── workflow                    <- Airflow Directory
    │   └── model_maintenance.py    <- File to copy/paste in Airflow's dags directory.
    ├── init_airflow_variables.sh   <- Script to initialize environment variables for Airflow package.
    ├── logs                        <- Directory for training logs.
    ├── models                      <- Directory for trained and serialized models, model predictions, or model summaries.
    ├── setup.py                    <- Configuration file for package installation.
    └── src                         <- Source code for this project.
        ├── __init__.py
        ├── config                  <- Configuration files for the project.
        ├── docs_files              <- Documentation files for the project.
        │   └── workflow.png        <- Image of the Airflow workflow.
        ├── features                <- Scripts to turn raw data into features for modeling.
        │   └── build_features.py   <- Script for building features.
        ├── data                    <- Scripts to load and process data
        │   ├── __init__.py         
        │   ├── check_structure.py  <- Check file and directory existence
        │   ├── import_raw_data.py  <- import Car Accidents raw data from Amazon AWS 
        │   └── make_dataset.py     <- Copy data and upload environement variables
        ├── main.py                 <- Scripts to train models.
        ├── models                  <- Scripts to train models.
        │   ├── __init__.py
        │   ├── predict_model.py    <- Script for making predictions (from a json file of features or manually).
        │   ├── test_features.json  <- json file containing an example of features
        │   └── train_model.py      <- Script to train a model and save it on ./src/models/
        └── visualization           <- Scripts for data visualization and model results visualization.
            ├── __init__.py
            └── visualize.py        <- Script for data visualization.
   

---------

## Steps to follow 

Convention : All python scripts must be run from the root specifying the relative file path.

### 1- Create a virtual environment using Virtualenv.

    `python -m venv my_env`

###   Activate it 

    `./my_env/Scripts/activate`

###   Install the packages from requirements.txt

    `pip install -r .\requirements.txt` ### You will have an error in "setup.py" but this won't interfere with the rest

### 2- Execute import_raw_data.py to import the 4 datasets.

    `python .\src\data\import_raw_data.py` ### It will ask you to create a new folder, accept it.

### 3- Execute make_dataset.py initializing `./data/raw` as input file path and `./data/preprocessed` as output file path.

    `python .\src\data\make_dataset.py`

### 4- Execute train_model.py to instanciate the model in joblib format

    `python .\src\models\train_model.py`

### 5- Finally, execute predict_model.py with respect to one of these rules :
  
  - Provide a json file as follow : 

    
    `python ./src/models/predict_model.py ./src/models/test_features.json`

  test_features.json is an example that you can try 

  - If you do not specify a json file, you will be asked to enter manually each feature. 


------------------------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
