# course-creation
ai agent to use deep research for course creation

## How to get started

- Check the notebook which has the content and ai agent workflow

- In order to get  results from api

  - Run
     ```
     docker build -t ai-course .
     ```

     ```
     docker run -it -p 8000:8000 ai-course
     ```


   - Once the server is running you can send the request to celery task which will process your results in background
     ```
     curl -X POST "http://localhost:8000/ai/run_scan" \
     -H "Content-Type: application/json" \
     -d '{
           "topic": "example_topic"
         }'

     ```
     Note: The output of the above api will be a taskid which we can use to check the status like,

     ```
     curl -X GET "http://yourserver.com/ai/task_id" \
     -H "Content-Type: application/json" \
     -d '{
           "TaskId": "your_task_id"
         }'

     ```
  - Once the task is finished the output will be saved to .txt file with name <your course topic>.txt
     
