"""
Module of an Airflow workflow that tests model accuracy and retrain it if test result is under a certain threshold.
Threshold value is stored as an environment variable.
"""

from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.email_operator import EmailOperator
from airflow.models import Variable
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.dates import days_ago
from datetime import datetime as dt, timedelta
import requests
import logging
import shutil  # Manage files. See: https://docs.python.org/3/library/shutil.html
from pathlib import Path

# Retrieve environement variables with Airflow get() dedicated function
admin_username = Variable.get("admin_username")
admin_password = Variable.get("admin_password")
api_url = Variable.get("api_url")
current_accuracy = Variable.get("current_accuracy")
accuracy_threshold = Variable.get("accuracy_threshold")

########################################                              
# Define a DAG to play the workflow
########################################
dag = DAG(
    dag_id='car_accidents_prediction_model_retraining',
    description="A DAG to retrain model if accurycy derives under a certain threshlod.",
    default_args={
        'Owner': 'airflow',
        'start_date': days_ago(2),  # or a fixed date such as dt(2024,5,20),
        'retries': 3,
        'retry_delay': timedelta(minutes=5),
        'catchup': False, 
        },
    schedule_interval=timedelta(days=1),
    doc_md="""
    ## SCHEDULE INTERVAL ##########
    Runs daily.

    ## DEFAULT ARGUMENTS ##########
    - **Owner:** `airflow`
    - **Start Date:** `May 20, 2024`
    - **Retries:** `3`
    - **Retry Delay:** `5 minutes`
    - **Catchup:** `False`

    ## AIRFLOW ENVIRONMENT VARIABLES 
    - admin_username: Username for app API access 
    - admin_password: Password for app API access
    - api_url: URL of app API, default to local host: https://127.0.0.1:8000
    - current_accuracy: current model accurac
    - accuracy_threshold: accuracy threshold as an acceptance criteria

    ## DETAILED TASKS ##############
    - TASK 'get_jwt_token' (t1)
      Grasp a token and store it in a Xcom variable.

    - TASK 'recharge_data' (t2)
      Reload data: import raw data and make dataset with the latest available data.

    - TASK 'Check_accuracy' (t3)
      Compute model accuracy on the new dataset (new X_test and y_test) and compare to acceptance threshold.
      If accuracy is under threshold => 'backup' current model and 'retrain' model and save it
      Otherwise => 'nope' do nothing
    
    - TASK 'backup' (t4_1)
      Save the current model in archives with a timestamp.

    - TASK 'nope' (t4_2)
      Do nothing.

    - TASK 'retrain' (t5)
      Retrain the model and store it as the new current model.
    
    - TASK 'validate' (t6)
      Compare new accuracy vs. backup model accuracy and revert models if the new model shows a weaker accuracy.
      
    - TASK 'email_success' (t7_1)
      Send an email if the new model accuracy is better. 
    
    - TASK 'email failure' (t7_2)
      Send an email if the new model accuracy is not better.

    ## WORKFLOW DESCRIPTION ########
    The DAG proceeds in the following order:
        - Get a token using the admin profile in order to connect to the app API,
        - Upload new data and check model accuracy based on those new data, 
        - Backup model (if good accuracy) or do nothing (otherwise),
        - Retrain model (if good accuracy),
        - Validate the new model,
        - Send success email if accuracy has impoved or failure email (otherwise). 

    """,
)

def get_jwt_token(**kwargs):
    ti = kwargs['ti']

    token_url = f"{api_url}/token"
    data = {
        "grant_type": "password",
        "username": admin_username,
        "password": admin_password,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(token_url, data=data, headers=headers)
    if response.status_code == 200:
        # Return the token and add it to Variable:
        token = response.json().get("access_token")
        ti.xcom_push(key='token', value=(token))
        return token
    else:
        logging.error(f"Error obtaining JWT token: {response.status_code}, {response.text}")
        return None

def recharge_data(**kwargs):
    ti = kwargs['ti']

    token = ti.xcom_pull(task_ids='get_jwt_token', key='token')

    raw_url = f"{api_url}/raw"
    dataset_url = f"{api_url}/dataset"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Execute requests to import and process raw data
    resp_raw = requests.post(raw_url, headers=headers)
    resp_dataset = requests.post(dataset_url, headers=headers)

    if resp_raw.status_code == 200:
        logging.info("Raw data have been imported with success.")
    else:
        logging.error(f"Error when importing raw data: {resp_raw.status_code}, {resp_raw.text}")

    if resp_dataset.status_code == 200:
        logging.info("Data have been processed with success and are saved in folder: ./data/preprocessed.")
    else:
        logging.error(f"Error when processing raw data: {resp_dataset.status_code}, {resp_dataset.text}")

def nope():
    pass

def Check_accuracy(**kwargs):
    ti = kwargs['ti']

    token = ti.xcom_pull(task_ids='get_jwt_token', key='token')

    accuracy_url = f"{api_url}/accuracy"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Get accuracy from fresh data with a new X_test set
    resp_accuracy = requests.post(accuracy_url, headers=headers)

    # Update accuracy in environment variable
    ti.xcom_push(key='current_accuracy', value=(float(resp_accuracy)))
    logging.info(f"Checking accuracy difference... Current accuracy: {resp_accuracy}")
    
    accuracy_threshold = float(Variable.get("accuracy_threshold", default_var=85))

    if resp_accuracy >= accuracy_threshold:
        logging.info("Accuracy based on new data is above threshold then we do nothing.")
        return 'nope'
    else: 
        logging.info("Accuracy based on new data is under threshold thne we proceed to backup.")
        return 'backup'
    
def backup(**context):
    ti = context['ti']

    token = ti.xcom_pull(task_ids='get_jwt_token', key='token')

    backup_url = f"{api_url}/backup"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Backup current model
    resp_backup = requests.post(backup_url, headers=headers)
    
    if resp_backup.status_code == 200:
        logging.info("Current model has been saved as a backup with success.")
    else:
        logging.error(f"Error when saving current model: {resp_backup.status_code}, {resp_backup.text}")

def retrain(**context):
    ti = context['ti']

    token = ti.xcom_pull(task_ids='get_jwt_token', key='token')

    # Routes
    train_url = f"{api_url}/train"
    accuracy_url = f"{api_url}/accuracy"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Retrain model
    resp_train = requests.post(train_url, headers=headers)
    
    if resp_train.status_code == 200:
        logging.info("Model has been trained and saved with success.")
    else:
        logging.error(f"Error while training the model. Unable to save it: {resp_train.status_code}, {resp_train.text}")
    
    # Update model accuracy
    resp_accuracy = requests.post(accuracy_url, headers=headers)
    
    if accuracy_url.status_code == 200:
        ti.xcom_push(key='current_accuracy', value=(float(resp_accuracy)))
        logging.info("Accuracy has been updated with success.")
    else:
        logging.error(f"Error while updating accuracy: {accuracy_url.status_code}, {accuracy_url.text}")

def validate(**context):
    ti = context['ti']

    token = ti.xcom_pull(task_ids='get_jwt_token', key='token')

    # Define routes url
    accuracy_url = f"{api_url}/accuracy"
    reverse_backup_url = f"{api_url}/reverse_backup"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Get accuracy of the model
    resp_accuracy = requests.post(accuracy_url, headers=headers)
    
    # Check request success
    if resp_accuracy.status_code == 200:
        logging.info("Accuracy retrieved with success.")
    else:
        logging.error(f"Error while retrieveing accuracy: {resp_accuracy.status_code}, {resp_accuracy.text}")

    # Update accuracy in environment variable
    ti.xcom_push(key='current_accuracy', value=(float(resp_accuracy.values.get("accuracy"))))
    logging.info(f"Checking accuracy difference... Current accuracy: {resp_accuracy}")
    
    accuracy_threshold = float(Variable.get("accuracy_threshold", default_var=85))

    if float(resp_accuracy.values.get("accuracy")) >= accuracy_threshold:
        logging.info("Accuracy of the new model is above the threshold then we keep the new model.")
        
        return 'email_success'
    else: 
        logging.info("Accuracy of the new model is under the threshold then we keep the current model.")
        resp_accuracy = requests.post(accuracy_url, headers=headers)
        logging.info(f"Reversing models... Retrieving current model.")

        # Check request success
        if reverse_backup_url.status_code == 200:
            logging.info("Model reversed with success.")
        else:
            logging.error(f"Error while reversing model: {reverse_backup_url.status_code}, {reverse_backup_url.text}")

        return 'email_failure'
    
###############################################
# TASKS DESCRIPTIUON
###############################################
# Use PythonOperator when a simple outcome
# Use BranchPythonOperator when several outcomes are other tasks

t1 = PythonOperator(
    task_id='get_jwt_token',
    python_callable=get_jwt_token,
    dag=dag,
    doc_md="""
    ### `get_jwt_token`
    - **Type:** PythonOperator
    - **Description:** Get a token by using admin credentials to reach app API.
    """
)

t2 = PythonOperator(
    task_id='recharge_data',
    python_callable=recharge_data,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
    doc_md="""
    ### `recharge_data`
    - **Type:** PythonOperator
    - **Description:** Reload raw data and reprocess it.
    """
)

t3 = BranchPythonOperator(
    task_id='Check_accuracy',
    python_callable=Check_accuracy,
    dag=dag,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    doc_md="""
    ### `Check_accuracy`
    - **Type:** BranchPythonOperator
    - **Description:** Check accuracy of the model based on fresh data.
    """
)

t4_1 = PythonOperator(
    task_id='backup',
    python_callable=backup,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
    doc_md="""
    ### `backup`
    - **Type:** PythonOperator
    - **Description:** Save current model as a backup.
    """
)

t4_2 = PythonOperator(
    task_id='nope',
    python_callable=nope,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
    doc_md="""
    ### `nope`
    - **Type:** PythonOperator
    - **Description:** Do nothing.
    """
)

t5 = PythonOperator(
    task_id='retrain',
    python_callable=retrain,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
    doc_md="""
    ### `retrain`
    - **Type:** PythonOperator
    - **Description:** Retrain model and save it on current directory.
    """
)

t6 = BranchPythonOperator(
    task_id='validate',
    python_callable=validate,
    dag=dag,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    doc_md="""
    ### `validate`
    - **Type:** BranchPythonOperator
    - **Description:** Validate the new model or replace the genuine model. Send warning eamils in any case.
    """
)

t7_1 = EmailOperator(
    task_id='email_success',
    to='immocb@hotmail.com',
    subject='Model retrained with success',
    html_content="""<h3>Model retraining succeeded</h3>
                    <p>Retraining information:</p>
                    <ul>
                        <li>Accuracy of the model in production (reference): {{ Variable.get("accuracy_threshold", default_var=85) }}%</li>
                    </ul>
                    <p>Please see the logs for more details.</p>""",
    dag=dag,
    doc_md = """
    ### `email_success`
    - **Type:** EmailOperator
    - **Description:** Sends a success email with retraining details if validation is successful.
    """
)

t7_2 = EmailOperator(
    task_id='email_failure',
    to='immocb@hotmaiml.com',
    subject='Model retraining failed',
    html_content="""<h3>Model retraining failed</h3>
                    <p>Model retraining failed during validation. Here are some details:</p>
                    <ul>
                        <li>Accuracy of the model in production (reference): {{ Variable.get("accuracy_threshold", default_var=85) }}%</li>
                    </ul>
                    <p>Please check the logs and correct any identified issues.</p>""",
    dag=dag,
    doc_md = """
    ### `email_failure`
    - **Type:** EmailOperator
    - **Description:** Sends a failure email with retraining details if validation fails.
    """
)


#################################################
# WORKFLOW DEPENDENCIES DESCRIPTION
#################################################

t_1 >> t_2 >> t_3 >> [t4_1, t4_2]
t4_1 >> t5 >> t6 >> [t7_1, t7_2]
