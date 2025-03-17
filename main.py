
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import logging
from celery import Celery
import redis
from celery.exceptions import SoftTimeLimitExceeded
import logging
import os
from fastapi import BackgroundTasks
import asyncio
from core.graph import handler

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    redis_client = redis.Redis(host='localhost', port=6379)
    redis_client.ping()
except Exception as e:
    logging.error(f"Failed to initialize Redis client: {e}")
    raise e

try:
    celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/1')
    
except Exception as e:
    logging.error(f"Failed to initialize Celery app: {e}")
    raise e


@celery_app.task(name="main_scan_task", bind=True, soft_time_limit=10800, time_limit=10820)
def main_scan_task(self, topic):
    try:
        result = handler(topic)
        with open(f"{topic}_content.txt", "wt") as f:
            f.write(result)
        f.close()
    except  SoftTimeLimitExceeded:
        print("Task took longer than expected")
    except Exception as e:
        print("Execption found during process ", str(e))



    



@app.get("/health")
async def health():
    return {"status": "OK"}

@app.post("/ai/{run_scan}")
async def run_scan(query: Request):
    req_info = await query.json()
    print(f"{req_info}")
    logging.info(f"{req_info}")
    log_file_name = f"{req_info['topic']}.log"
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s - %(message)s')
    print("[+] Log file name: {}".format(log_file_name))
    task =  main_scan_task.delay(req_info['topic'])
    print({"Task": "Added", "TaskId": task.id, "Topic": req_info['topic']})
    logging.info({"Task": "Added", "TaskId": task.id, "Topic": req_info['topic']})
    return {"Task": "Added", "TaskId": task.id, "Topic": req_info['topic']}


@app.get("/ai/{task_id}")
async def get_task_status(task_id: Request):
    req_info = await task_id.json()
    task = main_scan_task.AsyncResult(req_info['TaskId'])
    return {"TaskId": task.id, "TaskStatus": task.status}

