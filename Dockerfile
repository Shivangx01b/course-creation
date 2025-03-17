FROM ubuntu:22.04

ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y 
RUN apt-get install  python3 python3-dev cmake make gcc g++ libssl-dev python3-pip -y
RUN apt-get update && apt-get install redis-server -y

WORKDIR /app
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip 
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install celery[redis]
RUN pip install langgraph
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "service redis-server start && uvicorn main:app --reload --host 0.0.0.0 & celery -A main.celery_app worker  -E --autoscale=100,4"]